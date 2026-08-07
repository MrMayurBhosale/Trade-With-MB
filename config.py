# config.py
# All constants and configuration loaded from .env file
# Do NOT hardcode sensitive values here

import os
import pytz
from dotenv import load_dotenv
import bcrypt
# Load environment variables from .env file
load_dotenv()

# ============================================================
# Validate critical environment variables
# ============================================================

def get_env(key, default=None, required=False, cast=str):
    """Get environment variable with validation"""
    value = os.getenv(key, default)
    if required and value is None:
        raise ValueError(f"CRITICAL: Environment variable '{key}' is not set in .env file!")
    try:
        return cast(value) if value is not None else None
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid value for '{key}': {e}")

# ============================================================
# MongoDB Settings
# ============================================================

MONGO_URI = get_env("MONGO_URI", required=True)
DB_NAME = get_env("DB_NAME", required=True)

# ============================================================
# Admin Credentials - From .env only
# ============================================================

ADMIN_LOGIN_ID = "ADMIN"
ADMIN_PASSWORD = get_env("ADMIN_PASSWORD", required=True)

# Hash admin password at startup using bcrypt
_admin_raw = get_env("ADMIN_PASSWORD", required=True)
ADMIN_PASSWORD_HASH = bcrypt.hashpw(
    _admin_raw.encode('utf-8'),
    bcrypt.gensalt()
).decode('utf-8')
del _admin_raw

# ============================================================
# Session Settings
# ============================================================

# Session timeout in seconds (default 10 minutes)
SESSION_TIMEOUT = get_env("SESSION_TIMEOUT", default=600, cast=int)

# ============================================================
# Rate Limiting
# ============================================================

# Max failed login attempts before lock
RATE_LIMIT_ATTEMPTS = get_env("RATE_LIMIT_ATTEMPTS", default=5, cast=int)

# Lock duration in seconds (10 minutes)
RATE_LIMIT_LOCK = get_env("RATE_LIMIT_LOCK", default=600, cast=int)

# ============================================================
# Trading Constants
# ============================================================

# Initial balance for new users
INIT_BALANCE = get_env("INIT_BALANCE", default=100000, cast=int)

# Brokerage rate (0.1%) - Validated range
_brokerage = get_env("BROKERAGE_RATE", default=0.001, cast=float)
if not (0 < _brokerage <= 0.05):
    raise ValueError("BROKERAGE_RATE must be between 0 and 0.05")
BROKERAGE_RATE = _brokerage

# Circuit limit percentage (±10%) - Fixed, not from env
CIRCUIT_LIMIT = 0.10

# Order types
ORDER_TYPE_MARKET = "MARKET"
ORDER_TYPE_LIMIT = "LIMIT"
ORDER_TYPE_SL = "STOP LOSS"

# Max funds user can add at once
MAX_ADD_FUNDS = get_env("MAX_ADD_FUNDS", default=50000, cast=int)

# Max order book entries per user
MAX_ORDER_BOOK = get_env("MAX_ORDER_BOOK", default=500, cast=int)

# ============================================================
# Cache Settings
# ============================================================

# Leaderboard cache duration in seconds (5 minutes)
LEADERBOARD_CACHE_SECONDS = 300

# Candle cache in session state
CANDLE_CACHE_SECONDS = 2

# ============================================================
# Auto Refresh + Sync
# ============================================================

# Auto refresh interval in seconds
AUTO_REFRESH = 2

# Multi-tab sync interval in seconds
SYNC_INTERVAL = 10

# ============================================================
# Storage + Backup
# ============================================================

# Candle TTL in days (auto delete old candles)
CANDLE_TTL_DAYS = get_env("CANDLE_TTL_DAYS", default=7, cast=int)

# Audit log TTL in days
AUDIT_LOG_TTL_DAYS = get_env("AUDIT_LOG_TTL_DAYS", default=30, cast=int)

# Max user predictions per stock
MAX_USER_PREDICTIONS = get_env("MAX_USER_PREDICTIONS", default=10, cast=int)

# Backup interval in seconds (5 minutes)
BACKUP_INTERVAL = get_env("BACKUP_INTERVAL", default=300, cast=int)

# Backup file path
BACKUP_FILE = get_env("BACKUP_FILE", default="backup_data.json")

# Exports folder
EXPORTS_FOLDER = get_env("EXPORTS_FOLDER", default="exports")

# ============================================================
# Timezone - IST
# ============================================================

IST = pytz.timezone("Asia/Kolkata")

# ============================================================
# 25 Stocks with base prices and volatility
# ============================================================

STOCKS = {
    "RELIANCE":   {"price": 2450.00, "volatility": 0.3},
    "TCS":        {"price": 3800.00, "volatility": 0.25},
    "HDFCBANK":   {"price": 1650.00, "volatility": 0.3},
    "INFY":       {"price": 1480.00, "volatility": 0.28},
    "TATAMOTORS": {"price": 950.00,  "volatility": 0.5},
    "ICICIBANK":  {"price": 1120.00, "volatility": 0.32},
    "SBIN":       {"price": 780.00,  "volatility": 0.35},
    "BHARTIARTL": {"price": 1250.00, "volatility": 0.28},
    "ITC":        {"price": 465.00,  "volatility": 0.2},
    "KOTAKBANK":  {"price": 1780.00, "volatility": 0.3},
    "LT":         {"price": 3450.00, "volatility": 0.28},
    "HINDUNILVR": {"price": 2520.00, "volatility": 0.2},
    "AXISBANK":   {"price": 1085.00, "volatility": 0.33},
    "BAJFINANCE": {"price": 6800.00, "volatility": 0.45},
    "MARUTI":     {"price": 12500.00,"volatility": 0.3},
    "SUNPHARMA":  {"price": 1350.00, "volatility": 0.32},
    "TITAN":      {"price": 3200.00, "volatility": 0.35},
    "ULTRACEMCO": {"price": 9800.00, "volatility": 0.25},
    "WIPRO":      {"price": 480.00,  "volatility": 0.28},
    "ADANIENT":   {"price": 2900.00, "volatility": 0.55},
    "TATASTEEL":  {"price": 145.00,  "volatility": 0.6},
    "POWERGRID":  {"price": 305.00,  "volatility": 0.2},
    "NTPC":       {"price": 370.00,  "volatility": 0.22},
    "COALINDIA":  {"price": 430.00,  "volatility": 0.25},
    "ONGC":       {"price": 265.00,  "volatility": 0.3},
}

# Helper - Get just prices dict (backward compat)
STOCK_BASE_PRICES = {k: v["price"] for k, v in STOCKS.items()}

# Helper - Get volatility dict
STOCK_VOLATILITY = {k: v["volatility"] for k, v in STOCKS.items()}

# ============================================================
# Fake News Pool
# ============================================================

FAKE_NEWS_POOL = [
    "RELIANCE announces new 5G plant, stock sees rally",
    "IT sector falls, TCS and INFY down by 2%",
    "RBI keeps repo rate unchanged, Bank stocks volatile",
    "TATAMOTORS gets big export order, investors cheer",
    "Profit booking in market, NIFTY drops 200 points",
    "ADANIENT announces new green energy project",
    "HDFCBANK Q2 results tomorrow, expectations are high",
    "Crude oil prices rise, ONGC gains",
    "FMCG sector stable, HINDUNILVR and ITC trade flat",
    "FIIs buy worth 5000Cr today in Indian markets",
    "Auto sector slowdown, MARUTI and TATAMOTORS fall",
    "Pharma stocks surge, SUNPHARMA up by 3%",
    "Govt announces big budget for infrastructure",
    "Crypto crashes, investors move to stock market",
    "Market expects rally before Diwali season",
    "TATASTEEL rallies on China demand news",
    "NIFTY touches 25000 mark for first time",
    "LT wins 12000Cr defense contract",
    "Insurance stocks up after IRDAI new rules",
    "Realty sector boom, real estate stocks gain",
    "USDINR weakens, IT exporters benefit",
    "SEBI tightens norms for F&O trading",
    "COALINDIA announces record production",
    "WIPRO signs mega deal with US client",
    "BAJFINANCE reports strong quarterly earnings",
    "TITAN launches new luxury brand, stock jumps",
    "POWERGRID gets new transmission project",
    "NTPC capacity expansion plan announced",
    "AXISBANK merger rumors boost stock price",
    "KOTAKBANK digital banking push impresses analysts"
]