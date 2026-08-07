# app.py
# Main Streamlit application - TRADE with MB
# Paper Trading Platform - 24/7 Live Market
# Database: MongoDB | Backup: JSON | Export: CSV

import bcrypt 
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import random
import time
import secrets
from datetime import datetime, timedelta

from config import (
    STOCKS, STOCK_BASE_PRICES, STOCK_VOLATILITY,
    FAKE_NEWS_POOL, ADMIN_LOGIN_ID, ADMIN_PASSWORD_HASH,
    INIT_BALANCE, BROKERAGE_RATE, SESSION_TIMEOUT,
    CIRCUIT_LIMIT, RATE_LIMIT_ATTEMPTS, LEADERBOARD_CACHE_SECONDS,
    SYNC_INTERVAL, AUTO_REFRESH, MAX_ADD_FUNDS, MAX_ORDER_BOOK,
    ORDER_TYPE_MARKET, ORDER_TYPE_LIMIT, ORDER_TYPE_SL,
    IST, EXPORTS_FOLDER
)
from db import (
    register_user, login_user, forgot_password,
    get_user_data, save_data,
    soft_delete_user, get_all_users, get_all_user_data,
    add_audit_log, get_audit_logs,
    export_users_csv, export_trades_csv, cleanup_export_file,
    get_global_market_prices, update_global_market_prices,
    hash_password, check_password,
    is_duplicate_name, check_rate_limit, record_failed_attempt,
    clear_rate_limit, check_forgot_password_rate_limit,
    record_forgot_password_attempt,
    get_candles, get_predictions, get_user_predictions,
    save_user_prediction, save_order, get_orders,
    get_orders_count, check_db_health,
    sanitize_string, validate_login_id, validate_favourite_number
)
from market import generate_candles, predict_next_move, calculate_portfolio_value

# ============================================================
# Page Configuration
# ============================================================

st.set_page_config(
    page_title="TRADE with MB",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS Styling - Dark theme unchanged
# ============================================================

st.markdown("""
<style>
.stApp, [data-testid="stSidebar"] {
    background: #0D1117!important;
    color: #C9D1D9!important;
}
.card {
    background: #161B22;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #30363D;
    margin-bottom: 8px;
}
.news {
    background: #161B22;
    padding: 10px;
    border-left: 3px solid #00D09C;
    margin: 5px 0;
    border-radius: 5px;
}
.profile-box {
    background: #161B22;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #30363D;
    margin-top: 10px;
}
.login-box {
    background: #161B22;
    padding: 30px;
    border-radius: 15px;
    border: 1px solid #30363D;
    max-width: 450px;
    margin: auto;
}
.cred-box {
    background: #1a2332;
    padding: 20px;
    border-radius: 10px;
    border: 2px solid #00D09C;
    margin: 15px 0;
    font-family: monospace;
}
input, textarea, [data-baseweb="select"] {
    background-color: #161B22!important;
    color: #C9D1D9!important;
    border: 1px solid #30363D!important;
}
button[kind="primary"] {
    background-color: #00D09C!important;
    color: #0D1117!important;
}
[data-testid="stMetric"] {
    background: #161B22;
    padding: 10px;
    border-radius: 10px;
    border: 1px solid #30363D;
}
.profit { color: #00D09C; }
.loss   { color: #F85149; }
.admin-badge {
    background: #FFD700;
    color: #000;
    padding: 3px 8px;
    border-radius: 5px;
    font-weight: bold;
}
.banner {
    background: #FF4500;
    color: white;
    padding: 10px;
    text-align: center;
    font-weight: bold;
    border-radius: 5px;
    margin-bottom: 10px;
    font-size: 16px;
}
.disclaimer {
    background: #1a1a2e;
    color: #FFD700;
    padding: 10px;
    border-radius: 5px;
    text-align: center;
    border: 1px solid #FFD700;
    margin: 10px 0;
    font-size: 12px;
}
.owned-stock {
    border-left: 3px solid #00D09C!important;
}
.brokerage-info {
    background: #1a2332;
    padding: 8px;
    border-radius: 5px;
    font-size: 12px;
    color: #8B949E;
    margin: 5px 0;
}
@media (max-width: 768px) {
    .card, .news, .profile-box { padding: 10px!important; }
    [data-testid="stMetric"] { font-size: 14px!important; }
    button { font-size: 14px!important; padding: 8px!important; }
    h3 { font-size: 18px!important; }
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# Paper Trading Banner - Always visible
# ============================================================

st.markdown(
    '<div class="banner">⚠️ PAPER TRADING ONLY - No Real Money Involved ⚠️</div>',
    unsafe_allow_html=True
)

# ============================================================
# MongoDB Health Check
# ============================================================

if not check_db_health():
    st.error("❌ MongoDB is not connected! Please start MongoDB and refresh.")
    st.info("Run: net start MongoDB (Windows) or mongod (Mac/Linux)")
    st.stop()

# ============================================================
# Session State Initialization
# ============================================================

def init_session_state():
    """Initialize all session state variables with defaults"""
    defaults = {
        "logged_in":            False,
        "is_admin":             False,
        "admin_viewing_as":     None,
        "current_user":         {},
        "page":                 "Dashboard",
        "news":                 random.sample(FAKE_NEWS_POOL, 5),
        "selected_stock":       "RELIANCE",
        "last_auto_update":     0,
        "last_activity":        time.time(),
        "csrf_token":           secrets.token_hex(16),
        "last_sync":            0,
        "leaderboard_cache":    None,
        "leaderboard_cache_time": 0,
        "show_credentials":     False,
        "new_login_id":         "",
        "new_password":         "",
        "market_prices":        {},
        "balance":              float(INIT_BALANCE),
        "portfolio":            {},
        "pending_orders":       [],
        "total_pnl":            0.0,
        "holding_pnl":          {},
        "last_reset_date":      datetime.now().strftime("%Y-%m-%d"),
        "candle_cache":         {},
        "candle_cache_time":    {},
        "news_update_time":     0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ============================================================
# Initialize market prices if empty
# ============================================================

if not st.session_state.market_prices:
    st.session_state.market_prices = get_global_market_prices()

# ============================================================
# Session Timeout Check - 10 min inactivity
# ============================================================

def check_session_timeout():
    """Check if session has timed out due to inactivity"""
    if st.session_state.logged_in:
        elapsed = time.time() - st.session_state.last_activity
        if elapsed > SESSION_TIMEOUT:
            login_id = st.session_state.current_user.get("login_id", "unknown")
            try:
                add_audit_log(login_id, "SESSION_TIMEOUT", "Session expired due to inactivity")
            except Exception:
                pass
            st.session_state.clear()
            init_session_state()
            st.warning("Session expired due to inactivity. Please login again.")
            st.stop()
        st.session_state.last_activity = time.time()

# ============================================================
# CSRF Token
# ============================================================

def get_csrf_token():
    """Get current CSRF token"""
    return st.session_state.csrf_token

def regenerate_csrf_token():
    """Regenerate CSRF token after login"""
    st.session_state.csrf_token = secrets.token_hex(16)

def validate_csrf(token):
    """Validate CSRF token"""
    return token == st.session_state.csrf_token

# ============================================================
# Load session data from MongoDB
# ============================================================

def load_session_data():
    """Load user trading data from MongoDB into session state"""
    try:
        login_id = st.session_state.current_user.get("login_id")
        if not login_id:
            return

        data = get_user_data(login_id)

        st.session_state.balance      = round(float(data.get("balance", INIT_BALANCE)), 2)
        st.session_state.portfolio    = data.get("portfolio", {})
        st.session_state.pending_orders = data.get("pending_orders", [])
        st.session_state.total_pnl    = round(float(data.get("total_pnl", 0.0)), 2)
        st.session_state.holding_pnl  = data.get("holding_pnl", {})
        st.session_state.last_reset_date = data.get(
            "last_reset_date",
            datetime.now().strftime("%Y-%m-%d")
        )
    except Exception as e:
        print(f"Load session data error: {e}")

# ============================================================
# Save session data to MongoDB
# ============================================================

def save_session_data():
    """Save current session trading data to MongoDB"""
    try:
        if not st.session_state.logged_in:
            return
        if st.session_state.is_admin and not st.session_state.admin_viewing_as:
            return

        login_id = st.session_state.current_user.get("login_id")
        if not login_id:
            return

        data = {
            "balance":          round(float(st.session_state.balance), 2),
            "portfolio":        st.session_state.portfolio,
            "pending_orders":   st.session_state.pending_orders,
            "total_pnl":        round(float(st.session_state.total_pnl), 2),
            "holding_pnl":      st.session_state.holding_pnl,
            "last_reset_date":  st.session_state.last_reset_date,
            "is_deleted":       0
        }
        save_data(login_id, data)
    except Exception as e:
        print(f"Save session data error: {e}")

# ============================================================
# Multi-Tab Sync - 10 seconds
# ============================================================

def sync_data():
    """Sync data from MongoDB every SYNC_INTERVAL seconds"""
    try:
        if time.time() - st.session_state.last_sync > SYNC_INTERVAL:
            if st.session_state.logged_in:
                if not st.session_state.is_admin or st.session_state.admin_viewing_as:
                    load_session_data()
            st.session_state.last_sync = time.time()
    except Exception as e:
        print(f"Sync data error: {e}")

# ============================================================
# Update Market Prices - 24/7
# ============================================================

def update_prices():
    """
    Update market prices from database.
    Market runs 24/7 - Always generates new candles.
    Rate limited to AUTO_REFRESH seconds.
    """
    try:
        current_time = time.time()
        if current_time - st.session_state.last_auto_update < AUTO_REFRESH:
            return

        st.session_state.last_auto_update = current_time

        # Generate new candles and get updated prices - 24/7
        prices = generate_candles()
        st.session_state.market_prices = prices

    except Exception as e:
        print(f"Update prices error: {e}")
        # Fallback to DB prices
        try:
            st.session_state.market_prices = get_global_market_prices()
        except Exception:
            pass

# ============================================================
# Day Reset - Midnight IST
# ============================================================

def check_day_reset():
    """Reset daily P&L at midnight IST"""
    try:
        today = datetime.now(IST).strftime("%Y-%m-%d")
        if st.session_state.last_reset_date != today:
            st.session_state.total_pnl   = 0.0
            st.session_state.holding_pnl = {}
            st.session_state.last_reset_date = today
            save_session_data()
            st.toast("Day P&L reset at midnight IST")
    except Exception as e:
        print(f"Day reset error: {e}")

# ============================================================
# Portfolio Helpers
# ============================================================

def get_holding_qty(stock):
    """Get quantity of a stock from portfolio"""
    holding = st.session_state.portfolio.get(stock, {})
    if isinstance(holding, dict):
        return holding.get("qty", 0)
    return int(holding) if holding else 0

def get_holding_avg(stock):
    """Get average buy price of a stock from portfolio"""
    holding = st.session_state.portfolio.get(stock, {})
    if isinstance(holding, dict):
        return holding.get("avg_price", 0.0)
    return 0.0

def get_portfolio_value():
    """Calculate total portfolio value - Qty x Current Price"""
    try:
        prices = st.session_state.market_prices
        return calculate_portfolio_value(st.session_state.portfolio, prices)
    except Exception:
        return 0.0

# ============================================================
# Place Order
# ============================================================

def place_order(side, o_type, stock, qty, price):
    """
    Place buy/sell order with all validations:
    - Qty > 0 check
    - Circuit limit check
    - Balance check
    - Portfolio check
    - Avg buy price calculation
    - P&L calculation
    - Brokerage deduction
    - Order book save
    """
    try:
        # Validate qty
        if qty <= 0:
            st.error("Quantity must be greater than 0")
            return

        prices    = st.session_state.market_prices
        exec_price = prices.get(stock, STOCK_BASE_PRICES.get(stock, 0))
        base_price = STOCK_BASE_PRICES.get(stock, exec_price)

        # Circuit limit check
        upper_circuit = base_price * (1 + CIRCUIT_LIMIT)
        lower_circuit = base_price * (1 - CIRCUIT_LIMIT)

        if exec_price > upper_circuit or exec_price < lower_circuit:
            st.error(
                f"Circuit limit hit! {stock} is frozen at "
                f"±{int(CIRCUIT_LIMIT * 100)}% | "
                f"Range: ₹{lower_circuit:.2f} - ₹{upper_circuit:.2f}"
            )
            return

        brokerage = round((exec_price * qty) * BROKERAGE_RATE, 2)
        status    = "FAILED"

        if o_type == ORDER_TYPE_MARKET:
            if side == "BUY":
                cost = round((exec_price * qty) + brokerage, 2)

                if cost <= st.session_state.balance:
                    # Deduct balance
                    st.session_state.balance = round(
                        st.session_state.balance - cost, 2
                    )

                    # Avg buy price calculation
                    existing = st.session_state.portfolio.get(stock, {})
                    existing_qty = existing.get("qty", 0) if isinstance(existing, dict) else int(existing or 0)
                    existing_avg = existing.get("avg_price", exec_price) if isinstance(existing, dict) else exec_price

                    new_qty = existing_qty + qty
                    new_avg = round(
                        ((existing_avg * existing_qty) + (exec_price * qty)) / new_qty, 2
                    ) if new_qty > 0 else exec_price

                    st.session_state.portfolio[stock] = {
                        "qty":       new_qty,
                        "avg_price": new_avg
                    }
                    status = "EXECUTED"
                    st.success(
                        f"✅ Bought {qty} {stock} @ ₹{exec_price:.2f} | "
                        f"Brokerage: ₹{brokerage:.2f}"
                    )
                else:
                    st.error(
                        f"❌ Insufficient Balance. "
                        f"Required: ₹{cost:,.2f} | "
                        f"Available: ₹{st.session_state.balance:,.2f}"
                    )
                    status = "FAILED"

            elif side == "SELL":
                holding   = st.session_state.portfolio.get(stock, {})
                owned_qty = holding.get("qty", 0) if isinstance(holding, dict) else int(holding or 0)

                if owned_qty == 0:
                    st.error(f"❌ You don't own {stock}")
                    status = "REJECTED"
                elif owned_qty < qty:
                    st.error(
                        f"❌ Only {owned_qty} shares available. "
                        f"Cannot sell {qty} shares."
                    )
                    status = "REJECTED"
                else:
                    avg_price = holding.get("avg_price", exec_price) if isinstance(holding, dict) else exec_price

                    # P&L calculation
                    pnl = round((exec_price - avg_price) * qty - brokerage, 2)
                    st.session_state.total_pnl = round(
                        st.session_state.total_pnl + pnl, 2
                    )
                    st.session_state.holding_pnl[stock] = round(
                        st.session_state.holding_pnl.get(stock, 0.0) + pnl, 2
                    )

                    # Update balance
                    st.session_state.balance = round(
                        st.session_state.balance + (exec_price * qty) - brokerage, 2
                    )

                    # Update portfolio
                    new_qty = owned_qty - qty
                    if new_qty > 0:
                        st.session_state.portfolio[stock] = {
                            "qty":       new_qty,
                            "avg_price": avg_price
                        }
                    else:
                        # Remove stock from portfolio
                        st.session_state.portfolio.pop(stock, None)
                        # Clean up holding_pnl for fully sold stock
                        # Keep for history, just note it's closed

                    status   = "EXECUTED"
                    pnl_text = f"Profit: ₹{pnl:.2f}" if pnl >= 0 else f"Loss: ₹{abs(pnl):.2f}"
                    st.success(
                        f"✅ Sold {qty} {stock} @ ₹{exec_price:.2f} | "
                        f"{pnl_text} | Brokerage: ₹{brokerage:.2f}"
                    )

            # Save order to DB only if executed or rejected
            order = {
                "Time":      datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
                "Type":      f"MARKET {side}",
                "Stock":     stock,
                "Qty":       qty,
                "Price":     round(exec_price, 2),
                "Brokerage": brokerage,
                "Status":    status
            }

            # Save to orders collection
            login_id = st.session_state.current_user.get("login_id")
            if login_id:
                save_order(login_id, order)

            # Save session only on EXECUTED
            if status == "EXECUTED":
                save_session_data()
                load_session_data()

        elif o_type in [ORDER_TYPE_LIMIT, ORDER_TYPE_SL]:
            # Check for duplicate pending orders
            existing_pending = [
                o for o in st.session_state.pending_orders
                if o.get("stock") == stock
                and o.get("type") == f"{o_type} {side}"
                and o.get("price") == price
                and o.get("qty") == qty
            ]

            if existing_pending:
                st.warning(f"⚠️ Similar pending order already exists for {stock}")
                return

            order_type_str = f"LIMIT {side}" if o_type == ORDER_TYPE_LIMIT else f"SL {side}"
            st.session_state.pending_orders.append({
                "type":      order_type_str,
                "stock":     stock,
                "qty":       qty,
                "price":     price,
                "placed_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
            })
            save_session_data()
            st.info(
                f"📋 {order_type_str} order placed for "
                f"{qty} {stock} @ ₹{price:.2f}"
            )

        st.rerun()

    except Exception as e:
        st.error(f"Order failed: {str(e)}")
        print(f"Place order error: {e}")

# ============================================================
# Check and Execute Pending Orders
# ============================================================

def check_pending_orders():
    """
    Check pending limit/stop loss orders and execute if conditions met.
    Stop Loss SELL: Execute when price drops to/below trigger price (loss cut).
    Stop Loss BUY: Execute when price rises to/above trigger price.
    Limit BUY: Execute when price drops to/below limit price.
    Limit SELL: Execute when price rises to/above limit price.
    """
    try:
        if not st.session_state.pending_orders:
            return

        prices         = st.session_state.market_prices
        executed_orders = []
        indices_to_remove = []

        for idx, order in enumerate(st.session_state.pending_orders):
            curr_price = prices.get(
                order['stock'],
                STOCK_BASE_PRICES.get(order['stock'], 0)
            )
            executed = False
            order_type = order.get('type', '')

            # Correct trigger logic
            if 'LIMIT BUY' in order_type and curr_price <= order['price']:
                executed = True
            elif 'LIMIT SELL' in order_type and curr_price >= order['price']:
                executed = True
            elif 'SL SELL' in order_type and curr_price <= order['price']:
                # Stop loss sell - triggered when price falls to stop level
                executed = True
            elif 'SL BUY' in order_type and curr_price >= order['price']:
                # Stop loss buy - triggered when price rises to stop level
                executed = True

            if executed:
                brokerage = round((order['price'] * order['qty']) * BROKERAGE_RATE, 2)
                exec_ok   = False

                if 'BUY' in order_type:
                    cost = round((order['price'] * order['qty']) + brokerage, 2)
                    if cost <= st.session_state.balance:
                        st.session_state.balance = round(
                            st.session_state.balance - cost, 2
                        )
                        existing = st.session_state.portfolio.get(order['stock'], {})
                        existing_qty = existing.get("qty", 0) if isinstance(existing, dict) else int(existing or 0)
                        existing_avg = existing.get("avg_price", order['price']) if isinstance(existing, dict) else order['price']

                        new_qty = existing_qty + order['qty']
                        new_avg = round(
                            ((existing_avg * existing_qty) + (order['price'] * order['qty'])) / new_qty, 2
                        ) if new_qty > 0 else order['price']

                        st.session_state.portfolio[order['stock']] = {
                            "qty":       new_qty,
                            "avg_price": new_avg
                        }
                        exec_ok = True

                else:  # SELL
                    holding   = st.session_state.portfolio.get(order['stock'], {})
                    owned_qty = holding.get("qty", 0) if isinstance(holding, dict) else int(holding or 0)

                    if owned_qty >= order['qty']:
                        avg_price = holding.get("avg_price", order['price']) if isinstance(holding, dict) else order['price']
                        pnl = round((order['price'] - avg_price) * order['qty'] - brokerage, 2)

                        st.session_state.total_pnl = round(
                            st.session_state.total_pnl + pnl, 2
                        )
                        st.session_state.balance = round(
                            st.session_state.balance + (order['price'] * order['qty']) - brokerage, 2
                        )

                        new_qty = owned_qty - order['qty']
                        if new_qty > 0:
                            st.session_state.portfolio[order['stock']] = {
                                "qty":       new_qty,
                                "avg_price": avg_price
                            }
                        else:
                            st.session_state.portfolio.pop(order['stock'], None)
                        exec_ok = True

                # Save executed order
                if exec_ok:
                    login_id = st.session_state.current_user.get("login_id")
                    if login_id:
                        save_order(login_id, {
                            "Time":      datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
                            "Type":      order_type,
                            "Stock":     order['stock'],
                            "Qty":       order['qty'],
                            "Price":     order['price'],
                            "Brokerage": brokerage,
                            "Status":    "EXECUTED"
                        })
                    indices_to_remove.append(idx)

        # Remove executed orders by index (reverse to maintain correct indices)
        for idx in sorted(indices_to_remove, reverse=True):
            st.session_state.pending_orders.pop(idx)

        if indices_to_remove:
            save_session_data()

    except Exception as e:
        print(f"Pending order check error: {e}")

# ============================================================
# Navigation Helpers
# ============================================================

def back_button():
    """Back button - only shown for non-admin users"""
    if not st.session_state.is_admin or st.session_state.admin_viewing_as:
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button("⬅️ Back"):
                st.session_state.page = "Dashboard"
                st.rerun()

def top_bar():
    """Top navigation bar with user info, refresh, and logout"""
    col1, col2, col3, col4 = st.columns([5, 2, 1, 1])

    with col1:
        name = st.session_state.current_user.get('full_name', 'User')
        if st.session_state.admin_viewing_as:
            name += " <span class='admin-badge'>VIEWING AS ADMIN</span>"
        st.markdown(f"Welcome, **{name}**", unsafe_allow_html=True)

    with col2:
        if st.session_state.admin_viewing_as:
            if st.button("👑 Back to Admin"):
                st.session_state.is_admin      = True
                st.session_state.admin_viewing_as = None
                st.session_state.current_user  = {
                    "login_id":  ADMIN_LOGIN_ID,
                    "full_name": "Admin",
                    "bio":       "System Administrator"
                }
                st.rerun()

    with col3:
        if st.button("🔄 Refresh"):
            update_prices()
            st.rerun()

    with col4:
        if st.button("Logout", type="secondary"):
            login_id = st.session_state.current_user.get("login_id", "unknown")
            try:
                save_session_data()
                add_audit_log(login_id, "LOGOUT", "User logged out")
            except Exception:
                pass
            st.session_state.clear()
            init_session_state()
            st.rerun()

# ============================================================
# Authentication Page
# ============================================================

def auth_page():
    """Authentication page - Login + Register + Forgot Password"""
    st.title("📈 TRADE with MB")
    st.caption("Paper Trading Platform - Login or Create Account")

    st.markdown(
        '<div class="disclaimer">'
        '📌 This is a PAPER TRADING platform for educational purposes only. '
        'No real money is involved.'
        '</div>',
        unsafe_allow_html=True
    )

    tab1, tab2, tab3 = st.tabs(["Login", "Register", "Forgot Password"])

    # --------------------------------------------------------
    # Login Tab
    # --------------------------------------------------------
    with tab1:
        login_id_input = st.text_input(
            "Login ID",
            key="login_id_input",
            placeholder="Enter your 4-character Login ID"
        )
        password_input = st.text_input(
            "Password",
            type="password",
            key="login_pass",
            placeholder="Enter your password"
        )

        if st.button("Login", type="primary", use_container_width=True):
            # Validate inputs
            if not login_id_input or not password_input:
                st.error("Please enter both Login ID and Password")
            else:
                login_id_clean = login_id_input.strip().upper()

                # Admin login check
                if login_id_clean == ADMIN_LOGIN_ID and bcrypt.checkpw(
                    password_input.encode('utf-8'),
                    ADMIN_PASSWORD_HASH.encode('utf-8')
                ):
                    st.session_state.logged_in    = True
                    st.session_state.is_admin     = True
                    st.session_state.current_user = {
                        "login_id":  ADMIN_LOGIN_ID,
                        "full_name": "Admin",
                        "bio":       "System Administrator"
                    }
                    st.session_state.last_activity = time.time()
                    regenerate_csrf_token()
                    st.rerun()

                else:
                    # Rate limit check
                    allowed, remaining = check_rate_limit(login_id_clean)
                    if not allowed:
                        st.error(
                            f"Account locked. Try again in {remaining} seconds."
                        )
                    else:
                        # User login
                        user = login_user(login_id_clean, password_input)
                        if user:
                            clear_rate_limit(login_id_clean)
                            st.session_state.logged_in    = True
                            st.session_state.is_admin     = False
                            st.session_state.current_user = {
                                "login_id":  user["login_id"],
                                "full_name": user["full_name"],
                                "bio":       user.get("bio", "")
                            }
                            st.session_state.last_activity = time.time()
                            regenerate_csrf_token()
                            load_session_data()
                            st.success(f"Welcome {user['full_name']}!")
                            st.rerun()
                        else:
                            attempts, locked = record_failed_attempt(login_id_clean)
                            if locked:
                                st.error(
                                    "Too many failed attempts! "
                                    "Account locked for 10 minutes."
                                )
                            else:
                                remaining_attempts = RATE_LIMIT_ATTEMPTS - attempts
                                st.error(
                                    f"Invalid Login ID or Wrong Password. "
                                    f"{remaining_attempts} attempts remaining."
                                )

    # --------------------------------------------------------
    # Register Tab
    # --------------------------------------------------------
    with tab2:
        full_name  = st.text_input("Full Name", key="reg_name", placeholder="Enter your full name")
        bio        = st.text_input("Bio", key="reg_bio", placeholder="Tell us about yourself")
        fav_number = st.text_input(
            "Favourite Number",
            key="reg_fav",
            type="password",
            placeholder="A number you will remember (used for password recovery)"
        )

        if st.button("Create Account", use_container_width=True):
            if not full_name or not fav_number:
                st.error("Full Name and Favourite Number are required")
            elif not validate_favourite_number(fav_number):
                st.error("Favourite Number must be numeric (e.g. 42)")
            elif is_duplicate_name(full_name):
                st.error("An account with this name already exists")
            else:
                with st.spinner("Creating account..."):
                    login_id, raw_password, error = register_user(
                        full_name, bio, fav_number
                    )

                if login_id:
                    st.session_state.show_credentials = True
                    st.session_state.new_login_id     = login_id
                    st.session_state.new_password     = raw_password
                    st.success("Registration Successful! Save your credentials below.")
                else:
                    st.error(f"Registration failed: {error}")

        # Show credentials box
        if st.session_state.show_credentials and st.session_state.new_login_id:
            st.markdown(f"""
            <div class="cred-box">
                <h4 style="color:#00D09C;">🔐 Your Login Credentials</h4>
                <p><b>Login ID:</b> {st.session_state.new_login_id}</p>
                <p><b>Password:</b> {st.session_state.new_password}</p>
                <p style="color:#F85149;">
                    ⚠️ Save these now! You cannot recover them later.
                </p>
            </div>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                st.code(
                    f"Login ID: {st.session_state.new_login_id}\n"
                    f"Password: {st.session_state.new_password}",
                    language="text"
                )
            with col2:
                if st.button("✅ I've Saved My Credentials"):
                    saved_id  = st.session_state.new_login_id
                    saved_pass = st.session_state.new_password
                    st.session_state.show_credentials = False
                    st.session_state.new_login_id     = ""
                    st.session_state.new_password     = ""

                    # Auto login after registration
                    user = login_user(saved_id, saved_pass)
                    if user:
                        st.session_state.logged_in    = True
                        st.session_state.is_admin     = False
                        st.session_state.current_user = {
                            "login_id":  user["login_id"],
                            "full_name": user["full_name"],
                            "bio":       user.get("bio", "")
                        }
                        st.session_state.last_activity = time.time()
                        regenerate_csrf_token()
                        load_session_data()
                        st.rerun()

    # --------------------------------------------------------
    # Forgot Password Tab
    # --------------------------------------------------------
    with tab3:
        forgot_lid = st.text_input(
            "Login ID",
            key="forgot_id",
            placeholder="Enter your Login ID"
        )
        forgot_fav = st.text_input(
            "Favourite Number",
            key="forgot_fav",
            type="password",
            placeholder="Enter your favourite number"
        )

        if st.button("Reset Password", use_container_width=True):
            if not forgot_lid or not forgot_fav:
                st.error("Both Login ID and Favourite Number are required")
            elif not validate_favourite_number(forgot_fav):
                st.error("Favourite Number must be numeric")
            else:
                forgot_lid_clean = forgot_lid.strip().upper()

                # Rate limit check for forgot password
                allowed, remaining = check_forgot_password_rate_limit(forgot_lid_clean)
                if not allowed:
                    st.error(f"Too many attempts. Try again in {remaining} seconds.")
                else:
                    with st.spinner("Resetting password..."):
                        new_pass, error = forgot_password(forgot_lid_clean, forgot_fav)

                    if new_pass:
                        st.success("Password reset successful!")
                        st.markdown(f"""
                        <div class="cred-box">
                            <h4 style="color:#00D09C;">🔐 New Password</h4>
                            <p><b>Login ID:</b> {forgot_lid_clean}</p>
                            <p><b>New Password:</b> {new_pass}</p>
                            <p style="color:#F85149;">⚠️ Save this now!</p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.code(
                            f"Login ID: {forgot_lid_clean}\nNew Password: {new_pass}",
                            language="text"
                        )
                    else:
                        record_forgot_password_attempt(forgot_lid_clean)
                        st.error(error or "Invalid Login ID or Wrong Favourite Number")

# ============================================================
# Auth Gate
# ============================================================

if not st.session_state.logged_in:
    auth_page()
    st.stop()

# Check session timeout - only if logged in
check_session_timeout()

# Sync data from DB
sync_data()

# ============================================================
# Dashboard Page
# ============================================================

# ============================================================
# FRAGMENT 1: Watchlist - Auto refresh every 5 sec
# ============================================================

@st.fragment(run_every=5)
def watchlist_fragment():
    """Watchlist - prices update every 5 sec"""
    update_prices()
    check_pending_orders()

    prices = st.session_state.market_prices

    st.subheader("📋 Watchlist")

    search_watch = st.text_input(
        "🔍 Search",
        key="watchlist_search",
        placeholder="Search stock..."
    )

    for stock in STOCKS.keys():
        if search_watch and search_watch.upper() not in stock:
            continue

        price = prices.get(stock, STOCK_BASE_PRICES[stock])
        base = STOCK_BASE_PRICES[stock]
        change = ((price - base) / base) * 100
        icon = "🟢" if change >= 0 else "🔴"
        owned = get_holding_qty(stock)
        own_icon = "💼" if owned > 0 else ""

        if st.button(
            f"{icon} {stock} {own_icon} | ₹{price:.2f} ({change:+.2f}%)",
            key=f"watch_{stock}",
            use_container_width=True
        ):
            st.session_state.selected_stock = stock
            st.rerun()


# ============================================================
# FRAGMENT 2: Chart - Auto refresh every 5 sec
# ============================================================

@st.fragment(run_every=8)
def chart_fragment():
    """Chart section - stable, no jumping"""
    selected = st.session_state.selected_stock

    st.subheader(f"📈 {selected} Live Chart")

    candles = get_candles(selected, limit=80)

    if not candles or len(candles) < 3:
        st.info("⏳ Live data generate hotey... 30 sec wait kara.")
        return

    dates = [c["timestamp"] for c in candles]
    opens = [c["open"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]

    fig = go.Figure(data=[go.Candlestick(
        x=dates,
        open=opens,
        high=highs,
        low=lows,
        close=closes,
        increasing_line_color="#00D09C",
        decreasing_line_color="#F85149"
    )])

    fig.update_layout(
        template="plotly_dark",
        height=400,
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis_rangeslider_visible=False,
        uirevision="chart_stable",
        transition={"duration": 0},
        xaxis=dict(
            range=[
                dates[-30] if len(dates) > 30 else dates[0],
                dates[-1]
            ]
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="live_chart",
        config={
            "scrollZoom": True,
            "displayModeBar": False
        }
    )
    st.caption("🔄 Chart updates every 8 seconds")


# ============================================================
# FRAGMENT 3: News - Auto refresh every 60 sec
# ============================================================

@st.fragment(run_every=60)
def news_fragment():
    """News section - Refreshes every 60 sec"""
    st.subheader("📰 Market News")
    
    if time.time() - st.session_state.news_update_time > 60:
        st.session_state.news = random.sample(FAKE_NEWS_POOL, 5)
        st.session_state.news_update_time = time.time()

    for n in st.session_state.news:
        st.markdown(
            f'<div class="news">🔔 {n}</div>',
            unsafe_allow_html=True
        )


# ============================================================
# STATIC SECTIONS - NO Auto Refresh
# ============================================================

def order_section():
    """Order placement - No auto refresh"""
    prices = st.session_state.market_prices
    stock = st.session_state.selected_stock
    price = prices.get(stock, STOCK_BASE_PRICES[stock])
    owned_qty = get_holding_qty(stock)
    avg_price = get_holding_avg(stock)

    st.subheader("📝 Place Order")
    st.metric(stock, f"₹{price:.2f}")

    order_type = st.selectbox(
        "Order Type",
        [ORDER_TYPE_MARKET, ORDER_TYPE_LIMIT, ORDER_TYPE_SL],
        key="order_type_select"
    )
    qty = st.number_input("Quantity", min_value=1, max_value=100, value=1, step=1)

    limit_price = price
    if order_type != ORDER_TYPE_MARKET:
        limit_price = st.number_input(
            "Trigger Price",
            min_value=0.01,
            value=float(round(price, 2)),
            step=0.05
        )

    est_brokerage = round(price * qty * BROKERAGE_RATE, 2)
    st.markdown(
        f'<div class="brokerage-info">'
        f'Est. Brokerage: ₹{est_brokerage:.2f} | '
        f'Total Cost: ₹{(price * qty + est_brokerage):,.2f}'
        f'</div>',
        unsafe_allow_html=True
    )

    col_b, col_s = st.columns(2)

    if col_b.button("BUY", use_container_width=True, type="primary"):
        place_order("BUY", order_type, stock, qty, limit_price)

    if owned_qty > 0:
        if col_s.button(
            f"SELL ({owned_qty})",
            use_container_width=True
        ):
            place_order("SELL", order_type, stock, min(qty, owned_qty), limit_price)
        st.caption(
            f"💼 Holding: {owned_qty} | Avg: ₹{avg_price:.2f}"
        )
    else:
        col_s.button(
            "SELL",
            disabled=True,
            use_container_width=True,
            help="Buy first to sell"
        )


def holdings_section():
    """Holdings - Static"""
    st.subheader("💼 Holdings")
    prices = st.session_state.market_prices
    holdings_data = []

    portfolio = st.session_state.portfolio
    if portfolio:
        for stk, holding in portfolio.items():
            if isinstance(holding, dict):
                qty = holding.get("qty", 0)
                avg = holding.get("avg_price", 0)
            else:
                qty = int(holding) if holding else 0
                avg = 0

            if qty > 0:
                ltp = prices.get(stk, STOCK_BASE_PRICES.get(stk, 0))
                value = round(qty * ltp, 2)
                pnl = round((ltp - avg) * qty, 2)
                pnl_pct = round(((ltp - avg) / avg * 100), 2) if avg > 0 else 0

                holdings_data.append({
                    "Stock": stk,
                    "Qty": qty,
                    "Avg": f"₹{avg:.2f}",
                    "LTP": f"₹{ltp:.2f}",
                    "Value": f"₹{value:,.2f}",
                    "P&L": f"₹{pnl:,.2f} ({pnl_pct:+.1f}%)"
                })

    if holdings_data:
        st.dataframe(
            pd.DataFrame(holdings_data),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No holdings yet. Buy a stock first!")


def orderbook_section():
    """Order book - Static"""
    st.subheader("📜 Order Book")
    login_id = st.session_state.current_user.get("login_id", "")
    orders = get_orders(login_id, limit=50)

    if orders:
        orders_display = []
        for o in orders[::-1]:
            orders_display.append({
                "Time": o.get("Time", ""),
                "Type": o.get("Type", ""),
                "Stock": o.get("Stock", ""),
                "Qty": o.get("Qty", 0),
                "Price": f"₹{float(o.get('Price', 0)):.2f}",
                "Status": o.get("Status", "")
            })
        st.dataframe(
            pd.DataFrame(orders_display),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No orders yet. Place a trade!")


def pending_orders_section():
    """Pending orders - Static"""
    st.subheader("⏳ Pending Orders")
    st.caption("P&L from pending orders excluded from Total P&L")

    pending = st.session_state.pending_orders
    if pending:
        pending_display = []
        for o in pending:
            pending_display.append({
                "Type": o.get("type", ""),
                "Stock": o.get("stock", ""),
                "Qty": o.get("qty", 0),
                "Price": f"₹{float(o.get('price', 0)):.2f}",
                "Placed": o.get("placed_at", "")
            })
        st.dataframe(
            pd.DataFrame(pending_display),
            use_container_width=True,
            hide_index=True
        )

        if st.button("🗑️ Cancel All Pending"):
            st.session_state.pending_orders = []
            save_session_data()
            st.success("All pending orders cancelled")
            st.rerun()
    else:
        st.info("No pending orders")


# ============================================================
# MAIN DASHBOARD - Uses Fragments
# ============================================================

def dashboard_page():
    """Main dashboard - Fragment based, no full page refresh"""
    
    st.title("📈 TRADE with MB - Pro Paper Trading")
    top_bar()
    check_day_reset()

    # Metrics section
    prices = st.session_state.market_prices
    portfolio_value = get_portfolio_value()
    net_worth = round(st.session_state.balance + portfolio_value, 2)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.markdown(
        f'<div class="card"><b>Balance</b><br>₹{st.session_state.balance:,.2f}</div>',
        unsafe_allow_html=True
    )
    col2.markdown(
        f'<div class="card"><b>Portfolio Value</b><br>₹{portfolio_value:,.2f}</div>',
        unsafe_allow_html=True
    )
    color = "profit" if st.session_state.total_pnl >= 0 else "loss"
    col3.markdown(
        f'<div class="card"><b>Today P&L</b><br>'
        f'<span class="{color}">₹{st.session_state.total_pnl:,.2f}</span>'
        f'<br><small>Resets daily midnight IST</small></div>',
        unsafe_allow_html=True
    )
    col4.markdown(
        f'<div class="card"><b>Net Worth</b><br>₹{net_worth:,.2f}</div>',
        unsafe_allow_html=True
    )
    total_trades = get_orders_count(
        st.session_state.current_user.get("login_id", "")
    )
    col5.markdown(
        f'<div class="card"><b>Trades</b><br>{total_trades}</div>',
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        '<div style="display:flex;justify-content:center;">'
        '<div class="card" style="width:300px;text-align:center;">'
        '<b>Market Status</b> 🟢 OPEN 24/7'
        '</div></div>',
        unsafe_allow_html=True
    )
    st.divider()

    # Three column layout with fragments
    col_watch, col_chart, col_order = st.columns([1, 2, 1])

    # WATCHLIST - Fragment (auto refresh 5s)
    with col_watch:
        watchlist_fragment()

    # CHART + NEWS - Fragments
    with col_chart:
        chart_fragment()
        news_fragment()

    # ORDER PANEL - No auto refresh
    with col_order:
        order_section()

    st.divider()

    # Bottom section - Static
    col1, col2, col3 = st.columns(3)
    with col1:
        holdings_section()
    with col2:
        orderbook_section()
    with col3:
        pending_orders_section()
# ============================================================
# Trade History Page
# ============================================================

def history_page():
    """Trade history with search and filter"""
    back_button()
    top_bar()
    st.title("📜 Trade History")

    login_id = st.session_state.current_user.get("login_id", "")
    orders   = get_orders(login_id, limit=MAX_ORDER_BOOK)

    if orders:
        # Search and Filter
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            search_stock = st.text_input(
                "🔍 Search Stock",
                placeholder="Stock name..."
            )
        with col2:
            filter_type = st.selectbox(
                "Filter Type",
                ["All", "BUY", "SELL"]
            )
        with col3:
            filter_status = st.selectbox(
                "Filter Status",
                ["All", "EXECUTED", "FAILED", "REJECTED"]
            )
        with col4:
            filter_date = st.date_input(
                "Filter Date",
                value=None,
                help="Filter by trade date"
            )

        # Apply filters
        filtered = orders[::-1]

        if search_stock:
            filtered = [
                o for o in filtered
                if search_stock.upper() in o.get("Stock", "").upper()
            ]
        if filter_type != "All":
            filtered = [
                o for o in filtered
                if filter_type in o.get("Type", "")
            ]
        if filter_status != "All":
            filtered = [
                o for o in filtered
                if o.get("Status") == filter_status
            ]
        if filter_date:
            date_str = filter_date.strftime("%Y-%m-%d")
            filtered = [
                o for o in filtered
                if o.get("Time", "").startswith(date_str)
            ]

        st.dataframe(
            pd.DataFrame(filtered) if filtered else pd.DataFrame(
                columns=["Time", "Type", "Stock", "Qty", "Price", "Brokerage", "Status"]
            ),
            use_container_width=True,
            hide_index=True
        )

        col_exp, col_clear = st.columns(2)

        # CSV Export with cleanup
        with col_exp:
            if st.button("📥 Export to CSV"):
                with st.spinner("Generating CSV..."):
                    filepath = export_trades_csv(login_id)
                if filepath:
                    with open(filepath, 'r', encoding='utf-8-sig') as f:
                        csv_data = f.read()
                    st.download_button(
                        "⬇️ Download CSV",
                        csv_data,
                        file_name=f"trades_{login_id}.csv",
                        mime="text/csv"
                    )
                    # Cleanup file after read
                    cleanup_export_file(filepath)
                else:
                    st.warning("No trades to export")

        with col_clear:
            if st.button("🗑️ Clear History"):
                st.warning(
                    "This will clear your trade history display. "
                    "Data remains in database."
                )
    else:
        st.info("No trades yet")

# ============================================================
# Funds Page
# ============================================================

def funds_page():
    """Funds management"""
    back_button()
    top_bar()
    st.title("💰 Funds")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Available Balance", f"₹{st.session_state.balance:,.2f}")
    with col2:
        portfolio_value = get_portfolio_value()
        st.metric("Portfolio Value", f"₹{portfolio_value:,.2f}")

    st.metric(
        "Net Worth",
        f"₹{round(st.session_state.balance + portfolio_value, 2):,.2f}"
    )

    st.divider()
    st.subheader("Add Funds")
    st.caption(f"Maximum you can add at once: ₹{MAX_ADD_FUNDS:,}")

    add_amount = st.number_input(
        "Enter Amount",
        min_value=10000,
        max_value=MAX_ADD_FUNDS,
        value=10000,
        step=1000
    )

    if st.button("Add Amount", type="primary", use_container_width=True):
        st.session_state.balance = round(
            st.session_state.balance + add_amount, 2
        )
        save_session_data()
        st.success(f"₹{add_amount:,.2f} added to your account!")
        st.rerun()

# ============================================================
# Settings Page
# ============================================================

def settings_page():
    """Settings - reset account, delete account"""
    back_button()
    top_bar()
    st.title("⚙️ Settings")

    st.success("Theme: Dark Mode - Locked 🔒")
    st.divider()

    if not st.session_state.is_admin:
        # Reset Account
        st.subheader("🔄 Reset Account")
        st.caption(
            "This will reset balance, portfolio, P&L, pending orders. "
            "Trade history and profile remain."
        )

        confirm_reset = st.checkbox("I confirm I want to reset my account")
        if st.button("Reset Account", type="secondary", disabled=not confirm_reset):
            st.session_state.balance        = float(INIT_BALANCE)
            st.session_state.portfolio      = {}
            st.session_state.total_pnl      = 0.0
            st.session_state.holding_pnl    = {}
            st.session_state.pending_orders = []
            save_session_data()
            add_audit_log(
                st.session_state.current_user.get("login_id", ""),
                "RESET",
                "Account reset by user"
            )
            st.success("Account reset successfully!")
            st.rerun()

        st.divider()

        # Delete Account
        st.subheader("🗑️ Delete Account")
        st.error(
            "⚠️ This will PERMANENTLY delete your account. "
            "You cannot login again."
        )

        confirm_text = st.text_input(
            "Type DELETE to confirm",
            placeholder="DELETE"
        )

        if st.button(
            "Delete Account",
            type="primary",
            disabled=(confirm_text != "DELETE")
        ):
            login_id = st.session_state.current_user.get("login_id", "")
            with st.spinner("Deleting account..."):
                soft_delete_user(login_id)
            st.session_state.clear()
            init_session_state()
            st.success("Account deleted successfully.")
            st.rerun()

# ============================================================
# Profile Page
# ============================================================

def profile_page():
    """User profile page with bio edit"""
    back_button()
    top_bar()
    st.title("👤 My Profile")

    user = st.session_state.current_user

    st.markdown('<div class="profile-box">', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Login ID", value=user.get("login_id", ""), disabled=True)
        st.text_input("Name", value=user.get("full_name", ""), disabled=True)
    with col2:
        st.text_input(
            "Member Since",
            value=user.get("created_at", "N/A"),
            disabled=True
        )

    # Editable bio
    new_bio = st.text_area(
        "Bio",
        value=user.get("bio", ""),
        placeholder="Tell us about yourself...",
        max_chars=200
    )

    if st.button("Update Bio", type="primary"):
        from db import users_col, sanitize_string
        login_id = user.get("login_id", "")
        new_bio_clean = sanitize_string(new_bio, max_length=200)

        try:
            users_col.update_one(
                {"login_id": login_id},
                {"$set": {"bio": new_bio_clean}}
            )
            st.session_state.current_user["bio"] = new_bio_clean
            add_audit_log(login_id, "PROFILE_UPDATE", "Bio updated")
            st.success("Bio updated successfully!")
        except Exception as e:
            st.error(f"Update failed: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # Account stats
    st.subheader("📊 Account Stats")
    login_id     = user.get("login_id", "")
    total_trades = get_orders_count(login_id)
    orders       = get_orders(login_id, limit=500)
    executed     = [o for o in orders if o.get("Status") == "EXECUTED"]
    wins         = [
        o for o in executed
        if "SELL" in o.get("Type", "") and o.get("Status") == "EXECUTED"
    ]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Trades", total_trades)
    col2.metric("Executed", len(executed))
    col3.metric("Current Balance", f"₹{st.session_state.balance:,.2f}")

# ============================================================
# Leaderboard Page
# ============================================================

def leaderboard_page():
    """Leaderboard with 5 minute cache"""
    back_button()
    top_bar()
    st.title("🏆 Leaderboard")

    current_time = time.time()
    current_login_id = st.session_state.current_user.get("login_id", "")

    # Refresh cache every 5 min
    if (
        st.session_state.leaderboard_cache is None
        or current_time - st.session_state.leaderboard_cache_time > LEADERBOARD_CACHE_SECONDS
    ):
        with st.spinner("Loading leaderboard..."):
            users    = get_all_users()
            all_data = get_all_user_data()
            prices   = get_global_market_prices()

            leaderboard = []
            for user in users:
                lid      = user["login_id"]
                data     = all_data.get(lid, {})
                balance  = float(data.get("balance", INIT_BALANCE))
                portfolio = data.get("portfolio", {})

                portfolio_value = calculate_portfolio_value(portfolio, prices)
                net_worth       = round(balance + portfolio_value, 2)
                pnl             = float(data.get("total_pnl", 0))

                leaderboard.append({
                    "login_id":  lid,
                    "Name":      user["full_name"],
                    "Net Worth": net_worth,
                    "P&L":       pnl,
                    "Trades":    get_orders_count(lid),
                    "Joined":    user.get("created_at", "N/A")
                })

            # Sort by net worth (numeric)
            leaderboard.sort(key=lambda x: x["Net Worth"], reverse=True)

            # Format after sort + add rank
            formatted = []
            for i, entry in enumerate(leaderboard):
                is_me = "⭐" if entry["login_id"] == current_login_id else ""
                formatted.append({
                    "Rank":      i + 1,
                    "Name":      f"{entry['Name']} {is_me}",
                    "Net Worth": f"₹{entry['Net Worth']:,.2f}",
                    "P&L":       f"₹{entry['P&L']:,.2f}",
                    "Trades":    entry["Trades"],
                    "Joined":    entry["Joined"]
                })

            st.session_state.leaderboard_cache      = formatted
            st.session_state.leaderboard_cache_time = current_time

    if st.session_state.leaderboard_cache:
        st.dataframe(
            pd.DataFrame(st.session_state.leaderboard_cache),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No users yet")

    st.caption(
        f"⭐ = You | Leaderboard refreshes every 5 minutes | "
        f"Last updated: {datetime.fromtimestamp(st.session_state.leaderboard_cache_time).strftime('%H:%M:%S')}"
    )

# ============================================================
# Admin Panel
# ============================================================

def admin_panel():
    """Admin panel - view all users, login as user, delete user, audit logs"""
    top_bar()
    st.title("👑 Admin Panel")

    users    = get_all_users()
    all_data = get_all_user_data()
    prices   = get_global_market_prices()

    # All users P&L dashboard
    st.subheader("📊 All Users Dashboard")

    admin_data = []
    for user in users:
        lid       = user["login_id"]
        data      = all_data.get(lid, {})
        balance   = float(data.get("balance", INIT_BALANCE))
        portfolio = data.get("portfolio", {})
        portfolio_value = calculate_portfolio_value(portfolio, prices)
        net_worth = round(balance + portfolio_value, 2)

        admin_data.append({
            "Login ID":   lid,
            "Name":       user["full_name"],
            "Balance":    f"₹{balance:,.2f}",
            "Portfolio":  f"₹{portfolio_value:,.2f}",
            "Net Worth":  f"₹{net_worth:,.2f}",
            "Total P&L":  f"₹{float(data.get('total_pnl', 0)):,.2f}",
            "Joined":     user.get("created_at", "N/A")
        })

    st.dataframe(
        pd.DataFrame(admin_data) if admin_data else pd.DataFrame(),
        use_container_width=True,
        hide_index=True
    )

    # Export users CSV
    if st.button("📥 Export Users CSV"):
        with st.spinner("Generating CSV..."):
            filepath = export_users_csv()
        if filepath:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                csv_data = f.read()
            st.download_button(
                "⬇️ Download Users CSV",
                csv_data,
                file_name="users_export.csv",
                mime="text/csv"
            )
            cleanup_export_file(filepath)
        else:
            st.warning("No users to export")

    st.divider()

    # Login as any user - view only
    st.subheader("👁️ View as User")
    if users:
        user_options = {
            f"{u['full_name']} ({u['login_id']})": u['login_id']
            for u in users
        }
        selected_display = st.selectbox(
            "Select User",
            list(user_options.keys()),
            key="admin_view_user"
        )

        # Search in admin user list
        search_admin = st.text_input(
            "🔍 Search User",
            placeholder="Name or Login ID...",
            key="admin_search"
        )

        filtered_users = users
        if search_admin:
            filtered_users = [
                u for u in users
                if search_admin.upper() in u["login_id"].upper()
                or search_admin.lower() in u["full_name"].lower()
            ]
            if filtered_users:
                selected_display = f"{filtered_users[0]['full_name']} ({filtered_users[0]['login_id']})"

        if st.button("View as this User", type="primary"):
            selected_lid = user_options.get(selected_display)
            if selected_lid:
                user = next(
                    (u for u in users if u["login_id"] == selected_lid),
                    None
                )
                if user:
                    st.session_state.is_admin         = False
                    st.session_state.admin_viewing_as = ADMIN_LOGIN_ID
                    st.session_state.current_user     = {
                        "login_id":  user["login_id"],
                        "full_name": user["full_name"],
                        "bio":       user.get("bio", "")
                    }
                    load_session_data()
                    st.success(f"Now viewing as {user['full_name']}")
                    st.rerun()

    st.divider()

    # Delete user with confirmation
    st.subheader("⚠️ Delete User Account")
    st.error("After deletion, user cannot access their account (soft delete)")

    if users:
        delete_options = {
            f"{u['full_name']} ({u['login_id']})": u['login_id']
            for u in users
        }
        delete_display = st.selectbox(
            "Select User to Delete",
            list(delete_options.keys()),
            key="admin_del"
        )
        confirm_delete = st.checkbox(
            "I confirm I want to delete this user",
            key="confirm_del_check"
        )

        if st.button(
            "Delete Account",
            key="del_btn",
            disabled=not confirm_delete
        ):
            delete_lid = delete_options.get(delete_display)
            if delete_lid:
                with st.spinner("Deleting user..."):
                    soft_delete_user(delete_lid)
                st.success(f"User {delete_lid} deleted successfully")
                st.rerun()

    st.divider()

    # Audit Logs
    st.subheader("📋 Audit Logs")
    logs = get_audit_logs(limit=100)
    if logs:
        st.dataframe(
            pd.DataFrame(logs),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No audit logs yet")

# ============================================================
# Analytics Page
# ============================================================

def analytics_page():
    """Analytics with trade statistics and P&L chart"""
    back_button()
    top_bar()
    st.title("📊 Analytics")

    login_id = st.session_state.current_user.get("login_id", "")
    orders   = get_orders(login_id, limit=500)

    total_trades = get_orders_count(login_id)
    st.metric("Total Trades", total_trades)

    if orders:
        executed = [o for o in orders if o.get("Status") == "EXECUTED"]
        buy_exec = [o for o in executed if "BUY"  in o.get("Type", "")]
        sell_exec= [o for o in executed if "SELL" in o.get("Type", "")]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Executed",   len(executed))
        col2.metric("Buy Orders", len(buy_exec))
        col3.metric("Sell Orders",len(sell_exec))

        # Win rate
        total_sell = len(sell_exec)
        col4.metric("Sell Trades", total_sell)

        st.divider()

        # Brokerage paid
        total_brokerage = round(
            sum(float(o.get("Brokerage", 0)) for o in executed), 2
        )
        st.metric("Total Brokerage Paid", f"₹{total_brokerage:,.2f}")

        # P&L trend chart
        st.subheader("📈 P&L Trend")
        pnl_data     = []
        running_pnl  = 0.0

        for o in orders:
            if o.get("Status") == "EXECUTED" and "SELL" in o.get("Type", ""):
                # Estimate PnL from order data
                price     = float(o.get("Price", 0))
                qty       = int(o.get("Qty", 0))
                brokerage = float(o.get("Brokerage", 0))
                running_pnl += round((price * qty) - brokerage, 2)
                pnl_data.append(running_pnl)

        if pnl_data:
            fig = go.Figure(data=[go.Scatter(
                y=pnl_data,
                mode='lines+markers',
                line=dict(
                    color="#00D09C" if pnl_data[-1] >= 0 else "#F85149",
                    width=2
                )
            )])
            fig.update_layout(
                template="plotly_dark",
                height=300,
                margin=dict(l=0, r=0, t=30, b=0),
                yaxis_title="Cumulative P&L (₹)"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sell trades yet for P&L chart")

        # Best and worst trades
        st.subheader("🏆 Trade Summary")
        prices_now = st.session_state.market_prices

        sell_trades = [
            o for o in orders
            if o.get("Status") == "EXECUTED" and "SELL" in o.get("Type", "")
        ]

        if sell_trades:
            trade_pnls = []
            for o in sell_trades:
                price     = float(o.get("Price", 0))
                qty       = int(o.get("Qty", 0))
                brokerage = float(o.get("Brokerage", 0))
                est_pnl   = round((price * qty * 0.01) - brokerage, 2)
                trade_pnls.append({
                    "Stock":  o.get("Stock", ""),
                    "Price":  f"₹{price:.2f}",
                    "Qty":    qty,
                    "Est. Return": f"₹{est_pnl:.2f}"
                })

            st.dataframe(
                pd.DataFrame(trade_pnls),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("No trade data for analytics yet")

# ============================================================
# Options Chain Page
# ============================================================

def options_page():
    """Options chain display"""
    back_button()
    top_bar()
    st.title("📈 Options Chain")

    prices = st.session_state.market_prices
    stock  = st.session_state.selected_stock
    base   = prices.get(stock, STOCK_BASE_PRICES[stock])

    st.subheader(f"{stock} | Spot: ₹{base:.2f}")

    # Generate strikes around current price
    step = max(50, round(base * 0.02 / 50) * 50)
    strikes = [
        round(base - (2 * step) + (i * step), 0)
        for i in range(7)
    ]

    # Filter out negative strikes
    strikes = [s for s in strikes if s > 0]

    # Seed for consistency within session
    seed = int(base * 100) % 10000
    rng  = random.Random(seed)

    data = []
    for s in strikes:
        intrinsic_ce = max(0, base - s)
        intrinsic_pe = max(0, s - base)
        data.append({
            "Strike":  f"₹{s:,.0f}",
            "CE LTP":  round(intrinsic_ce + rng.uniform(10, 80), 2),
            "CE OI":   rng.randint(1000, 50000),
            "PE LTP":  round(intrinsic_pe + rng.uniform(10, 80), 2),
            "PE OI":   rng.randint(1000, 50000),
            "ATM":     "⭐" if abs(s - base) < step else ""
        })

    st.dataframe(
        pd.DataFrame(data),
        use_container_width=True,
        hide_index=True
    )
    st.caption("⚠️ Dummy options data for educational purposes only")

# ============================================================
# News Page
# ============================================================

def news_page():
    """Market news page"""
    back_button()
    top_bar()
    st.title("📰 Market News")

    # Refresh news on page load
    st.session_state.news = random.sample(FAKE_NEWS_POOL, min(10, len(FAKE_NEWS_POOL)))
    st.session_state.news_update_time = time.time()

    for n in st.session_state.news:
        st.markdown(
            f'<div class="news">🔔 {n}</div>',
            unsafe_allow_html=True
        )

    st.caption("⚠️ All news is fake and for simulation purposes only")

# ============================================================
# AI Price Prediction Page
# ============================================================

def predict_page():
    """AI price prediction using DB engine + user prediction tool"""
    back_button()
    top_bar()
    st.title("📉 AI Price Prediction")

    stock      = st.session_state.selected_stock
    prices     = st.session_state.market_prices
    curr_price = prices.get(stock, STOCK_BASE_PRICES[stock])

    st.subheader(f"Selected: {stock} | Current Price: ₹{curr_price:.2f}")

    # Get prediction from DB engine
    with st.spinner("Analyzing market data..."):
        prediction = predict_next_move(stock)

    if prediction:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Predicted Price",
                f"₹{prediction['predicted_price']:.2f}"
            )
        with col2:
            trend_icon = "📈" if prediction['trend'] == "UP" else "📉"
            st.metric("Trend", f"{trend_icon} {prediction['trend']}")
        with col3:
            st.metric("Strength", f"{prediction['strength']:.2f}%")
        with col4:
            rsi_val = prediction.get('rsi')
            st.metric(
                "RSI",
                f"{rsi_val:.1f}" if rsi_val else "N/A",
                delta=prediction.get('rsi_signal', 'NEUTRAL')
            )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                f'<div class="card">'
                f'<b>SMA 5</b><br>₹{prediction["sma_5"]:.2f}'
                f'</div>',
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                f'<div class="card">'
                f'<b>SMA 10</b><br>₹{prediction["sma_10"]:.2f}'
                f'</div>',
                unsafe_allow_html=True
            )
        with col3:
            st.markdown(
                f'<div class="card">'
                f'<b>Support</b> ₹{prediction.get("support", 0):.2f} | '
                f'<b>Resistance</b> ₹{prediction.get("resistance", 0):.2f}'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.info("⏳ Collecting market data... Please wait a moment and refresh.")

    st.divider()

    # 5-day prediction chart
    st.subheader("📅 5-Day Price Forecast")
    days        = 5
    pred_prices = [curr_price]
    pred_dates  = [datetime.now()]
    trend_bias  = random.uniform(-0.3, 0.3)

    for i in range(1, days + 1):
        change    = np.random.normal(trend_bias, 1.2)
        new_price = pred_prices[-1] * (1 + change / 100)

        # Apply circuit limit
        base      = STOCK_BASE_PRICES[stock]
        new_price = max(base * (1 - CIRCUIT_LIMIT), min(base * (1 + CIRCUIT_LIMIT), new_price))

        pred_prices.append(round(new_price, 2))
        pred_dates.append(datetime.now() + timedelta(days=i))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pred_dates,
        y=pred_prices,
        mode='lines+markers',
        name="AI Forecast",
        line=dict(color="#00D09C", width=3)
    ))

    # Add support/resistance lines if available
    if prediction:
        support    = prediction.get("support", 0)
        resistance = prediction.get("resistance", 0)
        if support > 0:
            fig.add_hline(
                y=support,
                line_dash="dash",
                line_color="#F85149",
                annotation_text=f"Support ₹{support:.2f}"
            )
        if resistance > 0:
            fig.add_hline(
                y=resistance,
                line_dash="dash",
                line_color="#00D09C",
                annotation_text=f"Resistance ₹{resistance:.2f}"
            )

    fig.update_layout(
        template="plotly_dark",
        height=400,
        xaxis_title="Date",
        yaxis_title="Price ₹",
        margin=dict(l=0, r=0, t=30, b=0)
    )
    st.plotly_chart(fig, use_container_width=True)

    final_price  = pred_prices[-1]
    change_perc  = ((final_price / curr_price) - 1) * 100

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Predicted Day 5 Price", f"₹{final_price:.2f}")
    with col2:
        if change_perc > 0:
            st.success(f"AI Says: 📈 UP by {change_perc:.2f}%")
        else:
            st.error(f"AI Says: 📉 DOWN by {abs(change_perc):.2f}%")

    st.divider()

    # User prediction tool
    st.subheader("📐 Your Prediction")
    st.caption("Mark your support/resistance levels")

    pred_type  = st.selectbox(
        "Prediction Type",
        ["Support Line", "Resistance Line", "Trend Line", "Target Price"]
    )
    pred_price_val = st.number_input(
        "Price Level",
        min_value=0.01,
        value=float(round(curr_price, 2)),
        step=0.5
    )
    pred_note = st.text_input(
        "Note (optional)",
        placeholder="Why do you think this level is important?"
    )

    if st.button("💾 Save Prediction"):
        login_id = st.session_state.current_user.get("login_id", "")
        pred_data = {
            "type":      pred_type,
            "price":     pred_price_val,
            "note":      pred_note[:200],
            "stock":     stock,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        if save_user_prediction(login_id, stock, pred_data):
            st.success("✅ Prediction saved!")
        else:
            st.error("Failed to save prediction")

    # Show saved predictions on chart
    login_id   = st.session_state.current_user.get("login_id", "")
    user_preds = get_user_predictions(login_id, stock)

    if user_preds:
        st.subheader("📌 Your Saved Predictions")

        # Add predictions to chart
        pred_fig = go.Figure()
        pred_fig.add_trace(go.Scatter(
            x=pred_dates,
            y=pred_prices,
            mode='lines',
            name="AI Forecast",
            line=dict(color="#00D09C", width=2)
        ))

        pred_display = []
        for p in user_preds:
            d = p.get("data", {})
            p_price = d.get("price", 0)
            p_type  = d.get("type", "")
            color   = "#F85149" if "Support" in p_type else "#FFD700"

            # Add horizontal line for each prediction
            pred_fig.add_hline(
                y=p_price,
                line_dash="dot",
                line_color=color,
                annotation_text=f"{p_type}: ₹{p_price:.2f}"
            )

            pred_display.append({
                "Type":  p_type,
                "Price": f"₹{p_price:.2f}",
                "Note":  d.get("note", ""),
                "Time":  d.get("timestamp", "")
            })

        pred_fig.update_layout(
            template="plotly_dark",
            height=350,
            margin=dict(l=0, r=0, t=30, b=0)
        )
        st.plotly_chart(pred_fig, use_container_width=True)

        st.dataframe(
            pd.DataFrame(pred_display),
            use_container_width=True,
            hide_index=True
        )

    st.caption(
        "⚠️ Disclaimer: This is a DUMMY AI for practice only. "
        "Do not use for real trading decisions."
    )

# ============================================================
# Sidebar Navigation
# ============================================================

with st.sidebar:
    st.title("📊 TRADE with MB")
    st.caption(
        f"👤 {st.session_state.current_user.get('full_name', 'User')}"
    )
    st.caption(
        f"🆔 {st.session_state.current_user.get('login_id', '')}"
    )

    # Market status - always open 24/7
    st.markdown(
        '<div style="color:#00D09C;font-weight:bold;">🟢 Market OPEN 24/7</div>',
        unsafe_allow_html=True
    )

    if st.button("👤 Profile", use_container_width=True):
        st.session_state.page = "Profile"
        st.rerun()

    st.markdown("---")

    if not st.session_state.is_admin:
        nav_items = [
            ("🏠 Dashboard",    "Dashboard"),
            ("📊 Analytics",    "Analytics"),
            ("📈 Options Chain","Options"),
            ("💰 Funds",        "Funds"),
            ("📜 History",      "History"),
            ("📰 News",         "News"),
            ("📉 Price Predict","Predict"),
            ("🏆 Leaderboard",  "Leaderboard"),
        ]
        for label, page in nav_items:
            if st.button(label, use_container_width=True):
                st.session_state.page = page
                st.rerun()

    if st.session_state.is_admin:
        if st.button("👑 Admin Panel", use_container_width=True):
            st.session_state.page = "Admin"
            st.rerun()

    if st.button("⚙️ Settings", use_container_width=True):
        st.session_state.page = "Settings"
        st.rerun()

    st.markdown("---")
    st.markdown(
        '<div class="disclaimer">'
        '📌 PAPER TRADING ONLY<br>'
        'No Real Money Involved<br>'
        'Educational Purpose Only'
        '</div>',
        unsafe_allow_html=True
    )

# ============================================================
# Page Router
# ============================================================

pages = {
    "Dashboard":  dashboard_page,
    "Analytics":  analytics_page,
    "Options":    options_page,
    "Funds":      funds_page,
    "History":    history_page,
    "News":       news_page,
    "Predict":    predict_page,
    "Profile":    profile_page,
    "Admin":      admin_panel,
    "Settings":   settings_page,
    "Leaderboard":leaderboard_page
}

# Run selected page
current_page = st.session_state.get("page", "Dashboard")
if current_page in pages:
    pages[current_page]()
else:
    st.session_state.page = "Dashboard"
    dashboard_page()
