# db.py
# MongoDB database operations + JSON backup + CSV export
# Single source of truth for all data operations

import json
import os
import csv
import secrets
import string
import tempfile
import threading
import bcrypt
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError, ConnectionFailure, ServerSelectionTimeoutError
from config import (
    MONGO_URI, DB_NAME, INIT_BALANCE, STOCKS,
    ADMIN_LOGIN_ID, ADMIN_PASSWORD,
    CANDLE_TTL_DAYS, AUDIT_LOG_TTL_DAYS,
    MAX_USER_PREDICTIONS, BACKUP_FILE,
    EXPORTS_FOLDER, BACKUP_INTERVAL,
    RATE_LIMIT_ATTEMPTS, RATE_LIMIT_LOCK,
    STOCK_BASE_PRICES
)

# ============================================================
# MongoDB Connection Setup with error handling
# ============================================================

def get_db_connection():
    """Get MongoDB connection with error handling"""
    def get_db_connection():
    """Get MongoDB connection with error handling - Cloud optimized"""
    try:
        mongo_client = MongoClient(
            MONGO_URI,
            maxPoolSize=50,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
            retryWrites=True,
            w='majority'
        )
        # Test connection
        mongo_client.admin.command('ping')
        return mongo_client
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"MongoDB connection failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected connection error: {e}")
        return None

# Initialize connection
client = get_db_connection()

if client is None:
    raise RuntimeError(
        "CRITICAL: Cannot connect to MongoDB!\n"
        "Please ensure MongoDB is running on localhost:27017\n"
        "Run: net start MongoDB (Windows) or mongod (Mac/Linux)"
    )

db = client[DB_NAME]

# ============================================================
# Collections
# ============================================================

users_col         = db["users"]            # User registration data
user_data_col     = db["user_data"]        # User trading data
candles_col       = db["candles"]          # Live OHLC candle data
predictions_col   = db["predictions"]      # AI prediction data
user_preds_col    = db["user_predictions"] # User drawn predictions
audit_log_col     = db["audit_log"]        # Audit logs
market_prices_col = db["market_prices"]    # Global market prices
rate_limit_col    = db["rate_limit"]       # Rate limiting data
orders_col        = db["orders"]           # Separate orders collection

# ============================================================
# Exports folder setup
# ============================================================

os.makedirs(EXPORTS_FOLDER, exist_ok=True)

# ============================================================
# Backup tracking
# ============================================================

_last_backup_time = 0
_backup_lock = threading.Lock()

# ============================================================
# Create Indexes + TTL
# ============================================================

def create_indexes():
    """Create unique indexes and TTL indexes on MongoDB collections"""
    try:
        # Unique indexes
        users_col.create_index(
            [("login_id", ASCENDING)],
            unique=True
        )
        user_data_col.create_index(
            [("login_id", ASCENDING)],
            unique=True
        )

        # Candle index + TTL (auto delete after CANDLE_TTL_DAYS)
        candles_col.create_index(
            [("stock", ASCENDING), ("timestamp", ASCENDING)]
        )
        candles_col.create_index(
            [("created_at", ASCENDING)],
            expireAfterSeconds=CANDLE_TTL_DAYS * 24 * 60 * 60
        )

        # Audit log TTL (auto delete after AUDIT_LOG_TTL_DAYS)
        audit_log_col.create_index(
            [("created_at", ASCENDING)],
            expireAfterSeconds=AUDIT_LOG_TTL_DAYS * 24 * 60 * 60
        )

        # Market prices index
        market_prices_col.create_index(
            [("key", ASCENDING)],
            unique=True
        )

        # Rate limit TTL index
        rate_limit_col.create_index(
            [("locked_until", ASCENDING)],
            expireAfterSeconds=0,
            sparse=True
        )

        # Orders collection index
        orders_col.create_index(
            [("login_id", ASCENDING), ("time", ASCENDING)]
        )

        # User predictions index
        user_preds_col.create_index(
            [("login_id", ASCENDING), ("stock", ASCENDING)]
        )

        print("MongoDB indexes created successfully")
    except Exception as e:
        print(f"Index creation error: {e}")

create_indexes()

# ============================================================
# Password Hashing - bcrypt
# ============================================================

def hash_password(password):
    """Hash password using bcrypt"""
    try:
        return bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
    except Exception as e:
        print(f"Hash password error: {e}")
        return None

def check_password(password, hashed):
    """Verify password against bcrypt hash"""
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed.encode('utf-8')
        )
    except Exception:
        return False

def hash_favourite_number(fav_num):
    """Hash favourite number using bcrypt"""
    try:
        return bcrypt.hashpw(
            str(fav_num).encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
    except Exception as e:
        print(f"Hash favourite number error: {e}")
        return None

def check_favourite_number(fav_num, hashed):
    """Verify favourite number against bcrypt hash"""
    try:
        return bcrypt.checkpw(
            str(fav_num).encode('utf-8'),
            hashed.encode('utf-8')
        )
    except Exception:
        return False

def hash_admin_password(password):
    """Hash admin password using bcrypt"""
    try:
        return bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
    except Exception as e:
        print(f"Hash admin password error: {e}")
        return None

def check_admin_password(password, hashed):
    """Verify admin password against bcrypt hash"""
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed.encode('utf-8')
        )
    except Exception:
        return False

# ============================================================
# Input Sanitization
# ============================================================

def sanitize_string(value, max_length=100):
    """Sanitize string input to prevent injection"""
    if not isinstance(value, str):
        value = str(value)
    # Remove null bytes and control characters
    value = value.replace('\x00', '')
    # Limit length
    value = value[:max_length]
    # Strip whitespace
    value = value.strip()
    return value

def validate_login_id(login_id):
    """Validate login ID format - 4 uppercase alphanumeric"""
    if not login_id:
        return False
    login_id = login_id.upper().strip()
    if len(login_id) != 4:
        return False
    return all(c in string.ascii_uppercase + string.digits for c in login_id)

def validate_favourite_number(fav_num):
    """Validate favourite number - must be numeric"""
    try:
        int(str(fav_num).strip())
        return True
    except (ValueError, TypeError):
        return False

# ============================================================
# Auto Generate Login ID + Password using secrets
# ============================================================

def generate_login_id(max_attempts=100):
    """Generate unique 4 character login ID using cryptographically secure random"""
    chars = string.ascii_uppercase + string.digits
    for attempt in range(max_attempts):
        login_id = ''.join(secrets.choice(chars) for _ in range(4))
        try:
            if not users_col.find_one({"login_id": login_id}):
                return login_id
        except Exception as e:
            print(f"Login ID generation DB error: {e}")
            return None
    print("ERROR: Could not generate unique login ID after max attempts")
    return None

def generate_password():
    """Generate unique 6 character password with letters, digits and special chars"""
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(chars) for _ in range(6))

# ============================================================
# User Registration
# ============================================================

def register_user(full_name, bio, favourite_number):
    """Register new user with auto-generated login ID and password"""
    try:
        # Sanitize inputs
        full_name = sanitize_string(full_name, max_length=50)
        bio = sanitize_string(bio, max_length=200)

        # Validate favourite number
        if not validate_favourite_number(favourite_number):
            return None, None, "Favourite number must be numeric"

        # Generate credentials
        login_id = generate_login_id()
        if not login_id:
            return None, None, "Could not generate login ID. Try again."

        raw_password = generate_password()

        # Hash sensitive data
        hashed_password = hash_password(raw_password)
        hashed_fav = hash_favourite_number(favourite_number)

        if not hashed_password or not hashed_fav:
            return None, None, "Hashing failed. Try again."

        now = datetime.now()

        user_doc = {
            "login_id": login_id,
            "full_name": full_name,
            "bio": bio,
            "favourite_number": hashed_fav,
            "password": hashed_password,
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "created_at_dt": now,
            "is_deleted": 0
        }

        users_col.insert_one(user_doc)

        # Create default trading data
        default_data = {
            "login_id": login_id,
            "balance": float(INIT_BALANCE),
            "portfolio": {},
            "pending_orders": [],
            "total_pnl": 0.0,
            "holding_pnl": {},
            "last_reset_date": now.strftime("%Y-%m-%d"),
            "is_deleted": 0
        }
        user_data_col.insert_one(default_data)

        # Audit log
        add_audit_log(login_id, "REGISTER", "New account created")

        # Trigger backup
        trigger_backup()

        return login_id, raw_password, None

    except DuplicateKeyError:
        return None, None, "Login ID already exists. Try again."
    except Exception as e:
        print(f"Registration error: {e}")
        return None, None, "Registration failed. Try again."

# ============================================================
# Duplicate Prevention
# ============================================================

def is_duplicate_name(full_name):
    """Check if user with same full name already exists"""
    try:
        full_name = sanitize_string(full_name)
        return users_col.find_one({
            "full_name": {"$regex": f"^{full_name}$", "$options": "i"},
            "is_deleted": 0
        }) is not None
    except Exception as e:
        print(f"Duplicate check error: {e}")
        return False

# ============================================================
# Login
# ============================================================

def login_user(login_id, password):
    """Login using Login ID and password"""
    try:
        # Sanitize + uppercase
        login_id = sanitize_string(login_id).upper()

        user = users_col.find_one({
            "login_id": login_id,
            "is_deleted": 0
        })

        if user and check_password(password, user["password"]):
            add_audit_log(login_id, "LOGIN", "User logged in")
            return user

        return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

# ============================================================
# Rate Limiting
# ============================================================

def check_rate_limit(login_id):
    """Check if login ID is rate limited - returns (allowed, remaining_seconds)"""
    try:
        login_id = sanitize_string(login_id).upper()
        doc = rate_limit_col.find_one({"login_id": login_id})

        if doc and doc.get("locked_until"):
            locked_until = doc["locked_until"]
            if isinstance(locked_until, str):
                locked_until = datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S")

            if datetime.now() < locked_until:
                remaining = int((locked_until - datetime.now()).total_seconds())
                return False, remaining
            else:
                # Lock expired - clear it
                rate_limit_col.delete_one({"login_id": login_id})

        return True, 0
    except Exception:
        return True, 0

def record_failed_attempt(login_id):
    """Record failed login attempt - returns (attempts, is_locked)"""
    try:
        login_id = sanitize_string(login_id).upper()
        doc = rate_limit_col.find_one({"login_id": login_id})

        if doc:
            attempts = doc.get("attempts", 0) + 1
            if attempts >= RATE_LIMIT_ATTEMPTS:
                locked_until = datetime.now() + timedelta(seconds=RATE_LIMIT_LOCK)
                rate_limit_col.update_one(
                    {"login_id": login_id},
                    {"$set": {
                        "attempts": attempts,
                        "locked_until": locked_until
                    }}
                )
                return attempts, True
            else:
                rate_limit_col.update_one(
                    {"login_id": login_id},
                    {"$set": {"attempts": attempts}}
                )
                return attempts, False
        else:
            rate_limit_col.insert_one({
                "login_id": login_id,
                "attempts": 1,
                "locked_until": None
            })
            return 1, False
    except Exception as e:
        print(f"Record failed attempt error: {e}")
        return 0, False

def clear_rate_limit(login_id):
    """Clear rate limit after successful login"""
    try:
        login_id = sanitize_string(login_id).upper()
        rate_limit_col.delete_one({"login_id": login_id})
    except Exception as e:
        print(f"Clear rate limit error: {e}")

def check_forgot_password_rate_limit(login_id):
    """Rate limit for forgot password attempts"""
    try:
        login_id = sanitize_string(login_id).upper()
        key = f"forgot_{login_id}"
        doc = rate_limit_col.find_one({"login_id": key})

        if doc and doc.get("locked_until"):
            locked_until = doc["locked_until"]
            if isinstance(locked_until, str):
                locked_until = datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S")
            if datetime.now() < locked_until:
                remaining = int((locked_until - datetime.now()).total_seconds())
                return False, remaining
            else:
                rate_limit_col.delete_one({"login_id": key})

        return True, 0
    except Exception:
        return True, 0

def record_forgot_password_attempt(login_id):
    """Record failed forgot password attempt"""
    try:
        login_id = sanitize_string(login_id).upper()
        key = f"forgot_{login_id}"
        doc = rate_limit_col.find_one({"login_id": key})

        if doc:
            attempts = doc.get("attempts", 0) + 1
            if attempts >= RATE_LIMIT_ATTEMPTS:
                locked_until = datetime.now() + timedelta(seconds=RATE_LIMIT_LOCK)
                rate_limit_col.update_one(
                    {"login_id": key},
                    {"$set": {"attempts": attempts, "locked_until": locked_until}}
                )
                return attempts, True
            else:
                rate_limit_col.update_one(
                    {"login_id": key},
                    {"$set": {"attempts": attempts}}
                )
                return attempts, False
        else:
            rate_limit_col.insert_one({
                "login_id": key,
                "attempts": 1,
                "locked_until": None
            })
            return 1, False
    except Exception as e:
        print(f"Record forgot password attempt error: {e}")
        return 0, False

# ============================================================
# Forgot Password
# ============================================================

def forgot_password(login_id, favourite_number):
    """Reset password using Login ID and Favourite Number"""
    try:
        login_id = sanitize_string(login_id).upper()

        # Validate favourite number
        if not validate_favourite_number(favourite_number):
            return None, "Favourite number must be numeric"

        user = users_col.find_one({
            "login_id": login_id,
            "is_deleted": 0
        })

        if user and check_favourite_number(favourite_number, user["favourite_number"]):
            new_password = generate_password()
            hashed = hash_password(new_password)

            users_col.update_one(
                {"login_id": login_id},
                {"$set": {"password": hashed}}
            )

            # Clear any rate limits
            clear_rate_limit(login_id)

            add_audit_log(login_id, "PASSWORD_RESET", "Password reset via forgot password")
            trigger_backup()

            return new_password, None

        return None, "Invalid Login ID or Wrong Favourite Number"
    except Exception as e:
        print(f"Forgot password error: {e}")
        return None, "Password reset failed. Try again."

# ============================================================
# Get / Save User Trading Data
# ============================================================

def get_user_data(login_id):
    """Get user trading data from MongoDB"""
    try:
        login_id = sanitize_string(login_id).upper()
        data = user_data_col.find_one({
            "login_id": login_id,
            "is_deleted": 0
        })

        if data:
            data.pop("_id", None)
            return data

        # Return default data
        return _default_user_data(login_id)

    except Exception as e:
        print(f"Get user data error: {e}")
        return _default_user_data(login_id)

def _default_user_data(login_id):
    """Return default user trading data structure"""
    return {
        "login_id": login_id,
        "balance": float(INIT_BALANCE),
        "portfolio": {},
        "pending_orders": [],
        "total_pnl": 0.0,
        "holding_pnl": {},
        "last_reset_date": datetime.now().strftime("%Y-%m-%d"),
        "is_deleted": 0
    }

def save_data(login_id, data):
    """Single save function - saves to MongoDB + triggers JSON backup"""
    try:
        login_id = sanitize_string(login_id).upper()

        # Remove _id if present to avoid MongoDB error
        data.pop("_id", None)

        # Safety check - never overwrite is_deleted = 1
        existing = user_data_col.find_one({"login_id": login_id})
        if existing and existing.get("is_deleted") == 1:
            print(f"WARNING: Attempted to save data for deleted user {login_id}")
            return False

        # Ensure balance is rounded
        if "balance" in data:
            data["balance"] = round(float(data["balance"]), 2)

        # Ensure total_pnl is rounded
        if "total_pnl" in data:
            data["total_pnl"] = round(float(data["total_pnl"]), 2)

        data["login_id"] = login_id
        data["is_deleted"] = 0
        data["last_saved"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        user_data_col.update_one(
            {"login_id": login_id},
            {"$set": data},
            upsert=True
        )

        # Trigger backup (rate limited)
        trigger_backup()

        return True

    except Exception as e:
        print(f"Save data error: {e}")
        return False

# ============================================================
# Orders - Separate Collection
# ============================================================

def save_order(login_id, order):
    """Save order to separate orders collection"""
    try:
        login_id = sanitize_string(login_id).upper()
        order["login_id"] = login_id
        order["created_at"] = datetime.now()
        orders_col.insert_one(order)
        return True
    except Exception as e:
        print(f"Save order error: {e}")
        return False

def get_orders(login_id, limit=500):
    """Get orders for a user from orders collection"""
    try:
        login_id = sanitize_string(login_id).upper()
        order_list = list(
            orders_col.find({"login_id": login_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        for o in order_list:
            o.pop("_id", None)
            o.pop("login_id", None)
            o.pop("created_at", None)
        return order_list[::-1]
    except Exception as e:
        print(f"Get orders error: {e}")
        return []

def get_orders_count(login_id):
    """Get total order count for a user"""
    try:
        login_id = sanitize_string(login_id).upper()
        return orders_col.count_documents({"login_id": login_id})
    except Exception:
        return 0

# ============================================================
# Soft Delete
# ============================================================

def soft_delete_user(login_id):
    """Soft delete user - sets is_deleted = 1"""
    try:
        login_id = sanitize_string(login_id).upper()
        users_col.update_one(
            {"login_id": login_id},
            {"$set": {"is_deleted": 1}}
        )
        user_data_col.update_one(
            {"login_id": login_id},
            {"$set": {"is_deleted": 1}}
        )
        add_audit_log(login_id, "DELETE", "Account soft deleted")
        trigger_backup()
        return True
    except Exception as e:
        print(f"Soft delete error: {e}")
        return False

# ============================================================
# Get All Users
# ============================================================

def get_all_users():
    """Get all active non-deleted users"""
    try:
        users = list(users_col.find(
            {"is_deleted": 0},
            {"password": 0, "favourite_number": 0, "_id": 0}
        ))
        return users
    except Exception as e:
        print(f"Get all users error: {e}")
        return []

def get_all_user_data(projection=None):
    """Get all active user trading data with optional projection"""
    try:
        if projection is None:
            # Default: exclude heavy fields for leaderboard
            projection = {
                "_id": 0,
                "login_id": 1,
                "balance": 1,
                "portfolio": 1,
                "total_pnl": 1,
                "is_deleted": 1
            }

        data = list(user_data_col.find(
            {"is_deleted": 0},
            projection
        ))

        result = {}
        for d in data:
            d.pop("_id", None)
            result[d["login_id"]] = d

        return result
    except Exception as e:
        print(f"Get all user data error: {e}")
        return {}

# ============================================================
# Audit Log
# ============================================================

def add_audit_log(login_id, action, details=""):
    """Add entry to audit log"""
    try:
        # Limit details to 500 chars
        details = str(details)[:500]

        log = {
            "login_id": login_id,
            "action": action,
            "details": details,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "created_at": datetime.now()
        }
        audit_log_col.insert_one(log)
    except Exception as e:
        print(f"Audit log error: {e}")

def get_audit_logs(limit=100):
    """Get audit logs sorted by latest first"""
    try:
        logs = list(
            audit_log_col.find({}, {"_id": 0, "created_at": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )
        return logs
    except Exception:
        return []

# ============================================================
# JSON Backup - Rate limited + Atomic write
# ============================================================

def trigger_backup():
    """Trigger backup if enough time has passed"""
    global _last_backup_time
    import time
    current_time = time.time()

    if current_time - _last_backup_time >= BACKUP_INTERVAL:
        _last_backup_time = current_time
        # Run backup in background thread
        thread = threading.Thread(target=backup_to_json, daemon=True)
        thread.start()

def backup_to_json():
    """Backup MongoDB data to JSON file using atomic write"""
    with _backup_lock:
        try:
            # Exclude sensitive fields from backup
            all_users = list(users_col.find(
                {},
                {"_id": 0, "password": 0, "favourite_number": 0}
            ))
            all_data = list(user_data_col.find(
                {},
                {"_id": 0}
            ))

            backup = {
                "users": all_users,
                "user_data": all_data,
                "backup_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Atomic write - temp file then rename
            temp_fd, temp_path = tempfile.mkstemp(suffix='.json', dir='.')
            try:
                with os.fdopen(temp_fd, 'w') as f:
                    json.dump(backup, f, default=str)
                os.replace(temp_path, BACKUP_FILE)
            except Exception as e:
                print(f"Backup write error: {e}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            print(f"JSON backup error: {e}")

# ============================================================
# CSV Export - Proper format + Cleanup
# ============================================================

def export_users_csv():
    """Export all users data to CSV file"""
    try:
        users = get_all_users()
        if not users:
            return None

        filepath = os.path.join(EXPORTS_FOLDER, "users_export.csv")
        keys = ["login_id", "full_name", "bio", "created_at"]

        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(users)

        return filepath
    except Exception as e:
        print(f"CSV export error: {e}")
        return None

def export_trades_csv(login_id):
    """Export user trade history to CSV file"""
    try:
        login_id = sanitize_string(login_id).upper()
        orders = get_orders(login_id, limit=500)

        if not orders:
            return None

        filepath = os.path.join(EXPORTS_FOLDER, f"trades_{login_id}.csv")
        keys = ["Time", "Type", "Stock", "Qty", "Price", "Brokerage", "Status"]

        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(orders)

        return filepath
    except Exception as e:
        print(f"Trade CSV export error: {e}")
        return None

def cleanup_export_file(filepath):
    """Delete export file after download"""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Cleanup error: {e}")

# ============================================================
# Global Market Prices - Same for all users
# ============================================================

def get_global_market_prices():
    """Get single global market prices from database"""
    try:
        doc = market_prices_col.find_one({"key": "global_prices"})
        if doc:
            return doc.get("prices", {})

        # Initialize with default stock prices
        prices = {stock: data["price"] for stock, data in STOCKS.items()}
        market_prices_col.insert_one({
            "key": "global_prices",
            "prices": prices,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return prices

    except Exception as e:
        print(f"Get market prices error: {e}")
        return {stock: data["price"] for stock, data in STOCKS.items()}

def update_global_market_prices(prices):
    """Update global market prices in database"""
    try:
        market_prices_col.update_one(
            {"key": "global_prices"},
            {"$set": {
                "prices": prices,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Update market prices error: {e}")
        return False

# ============================================================
# Candle Data
# ============================================================

def save_candles_bulk(candle_list):
    """Save multiple OHLC candles using bulk write"""
    try:
        if not candle_list:
            return False
        candles_col.insert_many(candle_list)
        return True
    except Exception as e:
        print(f"Bulk candle save error: {e}")
        return False

def get_candles(stock, limit=50):
    """Get latest candles for a stock from MongoDB"""
    try:
        candles = list(
            candles_col.find({"stock": stock}, {"_id": 0, "created_at": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )
        candles.reverse()
        return candles
    except Exception as e:
        print(f"Get candles error: {e}")
        return []

# ============================================================
# Predictions - Upsert per stock
# ============================================================

def save_prediction(stock, predictions_data):
    """Save AI prediction to predictions collection - upsert per stock"""
    try:
        doc = {
            "stock": stock,
            "predictions": predictions_data,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        # Upsert - per stock sirf 1 prediction
        predictions_col.update_one(
            {"stock": stock},
            {"$set": doc},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Save prediction error: {e}")
        return False

def get_predictions(stock):
    """Get latest prediction for a stock"""
    try:
        pred = predictions_col.find_one(
            {"stock": stock},
            {"_id": 0}
        )
        return pred
    except Exception:
        return None

# ============================================================
# User Predictions - Max 10 per stock
# ============================================================

def save_user_prediction(login_id, stock, prediction_data):
    """Save user drawn prediction - max MAX_USER_PREDICTIONS per stock"""
    try:
        login_id = sanitize_string(login_id).upper()

        # Check count
        count = user_preds_col.count_documents({
            "login_id": login_id,
            "stock": stock
        })

        # Remove oldest if limit reached
        if count >= MAX_USER_PREDICTIONS:
            oldest = user_preds_col.find_one(
                {"login_id": login_id, "stock": stock},
                sort=[("created_at", ASCENDING)]
            )
            if oldest:
                user_preds_col.delete_one({"_id": oldest["_id"]})

        doc = {
            "login_id": login_id,
            "stock": stock,
            "data": prediction_data,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        user_preds_col.insert_one(doc)
        return True
    except Exception as e:
        print(f"Save user prediction error: {e}")
        return False

def get_user_predictions(login_id, stock):
    """Get user predictions for a stock"""
    try:
        login_id = sanitize_string(login_id).upper()
        preds = list(
            user_preds_col.find(
                {"login_id": login_id, "stock": stock},
                {"_id": 0}
            )
            .sort("created_at", -1)
            .limit(MAX_USER_PREDICTIONS)
        )
        return preds
    except Exception:
        return []

# ============================================================
# MongoDB Health Check
# ============================================================

def check_db_health():
    """Check if MongoDB is connected and healthy"""
    try:
        client.admin.command('ping')
        return True
    except Exception:
        return False
