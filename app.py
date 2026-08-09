# app.py
# Main Streamlit application - TRADE with MB
# Paper Trading Platform - 24/7 Live Market
# Database: MongoDB | Backup: JSON | Export: CSV
# UI VERSION 2.0 - Premium Dark Trading Terminal

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
# CSS Styling - Premium Dark Trading Terminal UI v2.0
# ============================================================

st.markdown("""
<style>

/* ===================== FONTS ===================== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ===================== ROOT VARIABLES ===================== */
:root {
    --bg-primary:     #080C10;
    --bg-secondary:   #0D1117;
    --bg-card:        #111620;
    --bg-card-hover:  #161D2A;
    --bg-input:       #0D1117;
    --bg-sidebar:     #090D12;

    --border-primary: #1E2733;
    --border-accent:  #00D09C22;
    --border-hover:   #00D09C55;

    --accent-green:   #00D09C;
    --accent-red:     #F85149;
    --accent-yellow:  #F0B429;
    --accent-blue:    #58A6FF;
    --accent-purple:  #BC8CFF;

    --text-primary:   #E6EDF3;
    --text-secondary: #8B949E;
    --text-muted:     #484F58;
    --text-accent:    #00D09C;

    --glow-green:     0 0 20px #00D09C18;
    --glow-red:       0 0 20px #F8514918;
    --shadow-card:    0 4px 24px rgba(0,0,0,0.4);
    --shadow-hover:   0 8px 32px rgba(0,0,0,0.6);

    --radius-sm:  6px;
    --radius-md:  10px;
    --radius-lg:  14px;
    --radius-xl:  18px;

    --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ===================== BASE ===================== */
*, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html, body, .stApp {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    font-size: 14px;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
}

/* ===================== SIDEBAR ===================== */
[data-testid="stSidebar"] {
    background: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border-primary) !important;
    padding: 0 !important;
}

[data-testid="stSidebar"] > div {
    padding: 20px 14px !important;
}

[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: var(--text-secondary) !important;
    border: 1px solid transparent !important;
    border-radius: var(--radius-md) !important;
    padding: 10px 14px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    text-align: left !important;
    transition: var(--transition) !important;
    margin-bottom: 2px !important;
    width: 100% !important;
    letter-spacing: 0.2px;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
    border-color: var(--border-primary) !important;
    transform: translateX(3px);
}

[data-testid="stSidebar"] .stButton > button:active {
    background: var(--bg-card-hover) !important;
    border-color: var(--border-hover) !important;
    color: var(--accent-green) !important;
}

/* ===================== MAIN BUTTONS ===================== */
.stButton > button {
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: var(--radius-md) !important;
    padding: 10px 20px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    font-family: 'Inter', sans-serif !important;
    transition: var(--transition) !important;
    cursor: pointer !important;
    letter-spacing: 0.3px;
}

.stButton > button:hover {
    background: var(--bg-card-hover) !important;
    border-color: var(--border-hover) !important;
    box-shadow: var(--glow-green) !important;
    transform: translateY(-1px);
}

button[kind="primary"],
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #00D09C, #00B887) !important;
    color: #080C10 !important;
    border: none !important;
    font-weight: 700 !important;
    letter-spacing: 0.5px;
    box-shadow: 0 4px 15px rgba(0, 208, 156, 0.25) !important;
}

button[kind="primary"]:hover,
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #00E5AB, #00D09C) !important;
    box-shadow: 0 6px 20px rgba(0, 208, 156, 0.35) !important;
    transform: translateY(-2px);
}

/* BUY Button */
.stButton > button:contains("BUY") {
    background: linear-gradient(135deg, #00D09C, #00B887) !important;
    color: #080C10 !important;
    font-weight: 700 !important;
}

/* SELL Button */
.stButton > button:contains("SELL") {
    background: linear-gradient(135deg, #F85149, #D73A3A) !important;
    color: #fff !important;
    border: none !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 15px rgba(248, 81, 73, 0.25) !important;
}

/* ===================== INPUTS ===================== */
input, textarea {
    background: var(--bg-input) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: var(--radius-md) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    transition: var(--transition) !important;
    padding: 10px 14px !important;
}

input:focus, textarea:focus {
    border-color: var(--accent-green) !important;
    box-shadow: 0 0 0 3px rgba(0, 208, 156, 0.1) !important;
    outline: none !important;
}

[data-baseweb="select"] {
    background: var(--bg-input) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: var(--radius-md) !important;
}

[data-baseweb="select"]:focus-within {
    border-color: var(--accent-green) !important;
    box-shadow: 0 0 0 3px rgba(0, 208, 156, 0.1) !important;
}

/* ===================== METRICS ===================== */
[data-testid="stMetric"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: var(--radius-lg) !important;
    padding: 16px 20px !important;
    transition: var(--transition) !important;
    position: relative;
    overflow: hidden;
}

[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent-green), transparent);
    opacity: 0.6;
}

[data-testid="stMetric"]:hover {
    border-color: var(--border-hover) !important;
    box-shadow: var(--shadow-card) !important;
    transform: translateY(-2px);
}

[data-testid="stMetricLabel"] {
    color: var(--text-secondary) !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.8px !important;
    text-transform: uppercase !important;
}

[data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-size: 22px !important;
    font-weight: 700 !important;
    font-family: 'JetBrains Mono', monospace !important;
    letter-spacing: -0.5px;
}

[data-testid="stMetricDelta"] {
    font-size: 12px !important;
    font-weight: 600 !important;
}

/* ===================== DATAFRAME ===================== */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border-primary) !important;
    border-radius: var(--radius-lg) !important;
    overflow: hidden !important;
}

[data-testid="stDataFrame"] table {
    background: var(--bg-card) !important;
}

[data-testid="stDataFrame"] th {
    background: #0D1117 !important;
    color: var(--text-secondary) !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.8px !important;
    text-transform: uppercase !important;
    padding: 12px 16px !important;
    border-bottom: 1px solid var(--border-primary) !important;
}

[data-testid="stDataFrame"] td {
    color: var(--text-primary) !important;
    font-size: 13px !important;
    padding: 10px 16px !important;
    border-bottom: 1px solid var(--border-primary) !important;
    font-family: 'JetBrains Mono', monospace !important;
}

[data-testid="stDataFrame"] tr:hover td {
    background: var(--bg-card-hover) !important;
}

/* ===================== TABS ===================== */
[data-testid="stTabs"] [role="tablist"] {
    background: var(--bg-card) !important;
    border-radius: var(--radius-lg) !important;
    padding: 4px !important;
    border: 1px solid var(--border-primary) !important;
    gap: 4px !important;
}

[data-testid="stTabs"] [role="tab"] {
    background: transparent !important;
    color: var(--text-secondary) !important;
    border-radius: var(--radius-md) !important;
    padding: 8px 20px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: var(--transition) !important;
    border: none !important;
}

[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background: var(--accent-green) !important;
    color: #080C10 !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 8px rgba(0, 208, 156, 0.3) !important;
}

[data-testid="stTabs"] [role="tab"]:hover:not([aria-selected="true"]) {
    background: var(--bg-card-hover) !important;
    color: var(--text-primary) !important;
}

/* ===================== DIVIDER ===================== */
hr {
    border: none !important;
    border-top: 1px solid var(--border-primary) !important;
    margin: 20px 0 !important;
}

/* ===================== SCROLLBAR ===================== */
::-webkit-scrollbar {
    width: 4px;
    height: 4px;
}

::-webkit-scrollbar-track {
    background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
    background: var(--border-primary);
    border-radius: 2px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--accent-green);
}

/* ===================== CUSTOM COMPONENTS ===================== */

/* Trading Card */
.card {
    background: var(--bg-card);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-lg);
    padding: 16px 18px;
    margin-bottom: 10px;
    transition: var(--transition);
    position: relative;
    overflow: hidden;
}

.card:hover {
    border-color: var(--border-hover);
    box-shadow: var(--shadow-card);
}

/* Metric Card */
.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-lg);
    padding: 18px 20px;
    margin-bottom: 8px;
    transition: var(--transition);
    position: relative;
    overflow: hidden;
}

.metric-card::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent-green), transparent);
    opacity: 0;
    transition: var(--transition);
}

.metric-card:hover::after {
    opacity: 1;
}

.metric-card:hover {
    border-color: var(--border-hover);
    transform: translateY(-2px);
    box-shadow: var(--shadow-card);
}

.metric-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--text-secondary);
    margin-bottom: 6px;
}

.metric-value {
    font-size: 20px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    color: var(--text-primary);
    letter-spacing: -0.5px;
}

.metric-sub {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 4px;
}

/* News Card */
.news {
    background: var(--bg-card);
    border: 1px solid var(--border-primary);
    border-left: 3px solid var(--accent-green);
    padding: 12px 16px;
    margin: 6px 0;
    border-radius: var(--radius-md);
    transition: var(--transition);
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.5;
}

.news:hover {
    background: var(--bg-card-hover);
    color: var(--text-primary);
    border-left-color: var(--accent-green);
    transform: translateX(3px);
}

/* Login Box */
.login-box {
    background: var(--bg-card);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-xl);
    padding: 36px;
    max-width: 460px;
    margin: 40px auto;
    box-shadow: var(--shadow-card);
    position: relative;
    overflow: hidden;
}

.login-box::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent-green), transparent);
}

/* Credentials Box */
.cred-box {
    background: linear-gradient(135deg, #0D1E1A, #111620);
    border: 1px solid var(--accent-green);
    border-radius: var(--radius-lg);
    padding: 22px 24px;
    margin: 16px 0;
    font-family: 'JetBrains Mono', monospace;
    box-shadow: var(--glow-green);
    position: relative;
}

.cred-box::before {
    content: '🔐 SAVE THESE CREDENTIALS';
    display: block;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: var(--accent-green);
    margin-bottom: 12px;
    font-family: 'Inter', sans-serif;
}

/* Profile Box */
.profile-box {
    background: var(--bg-card);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-xl);
    padding: 24px;
    margin-top: 12px;
    transition: var(--transition);
}

/* Banner */
.banner {
    background: linear-gradient(135deg, #1A0A0A, #200D0D);
    border: 1px solid #F8514933;
    color: #F87171;
    padding: 10px 20px;
    text-align: center;
    font-weight: 600;
    border-radius: var(--radius-md);
    margin-bottom: 12px;
    font-size: 13px;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
}

/* Disclaimer */
.disclaimer {
    background: linear-gradient(135deg, #0D0D1A, #111620);
    border: 1px solid #F0B42933;
    color: #F0B429;
    padding: 10px 16px;
    border-radius: var(--radius-md);
    text-align: center;
    font-size: 11px;
    letter-spacing: 0.3px;
    line-height: 1.6;
}

/* Brokerage Info */
.brokerage-info {
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    padding: 10px 14px;
    border-radius: var(--radius-md);
    font-size: 12px;
    color: var(--text-secondary);
    margin: 8px 0;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.2px;
}

/* Profit / Loss */
.profit {
    color: var(--accent-green) !important;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}

.loss {
    color: var(--accent-red) !important;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}

/* Admin Badge */
.admin-badge {
    background: linear-gradient(135deg, #F0B429, #D4A017);
    color: #080C10;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}

/* Owned Stock */
.owned-stock {
    border-left: 3px solid var(--accent-green) !important;
}

/* Market Status */
.market-status {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #0A1F16;
    border: 1px solid #00D09C33;
    color: var(--accent-green);
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
}

.market-status::before {
    content: '';
    width: 7px;
    height: 7px;
    background: var(--accent-green);
    border-radius: 50%;
    animation: pulse 2s infinite;
    box-shadow: 0 0 6px var(--accent-green);
}

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.85); }
}

/* Watchlist Stock Button */
.stock-btn {
    background: var(--bg-card);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    padding: 10px 14px;
    margin-bottom: 4px;
    cursor: pointer;
    transition: var(--transition);
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 13px;
    font-family: 'JetBrains Mono', monospace;
}

.stock-btn:hover {
    background: var(--bg-card-hover);
    border-color: var(--border-hover);
    transform: translateX(2px);
}

/* Section Header */
.section-header {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--text-secondary);
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-primary);
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Top Bar */
.top-bar {
    background: var(--bg-card);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-lg);
    padding: 12px 20px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

/* Order Panel */
.order-panel {
    background: var(--bg-card);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-lg);
    padding: 18px;
    position: sticky;
    top: 10px;
}

/* Price Display */
.price-display {
    font-family: 'JetBrains Mono', monospace;
    font-size: 26px;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -1px;
    line-height: 1.2;
}

.price-change-up {
    color: var(--accent-green);
    font-size: 13px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}

.price-change-down {
    color: var(--accent-red);
    font-size: 13px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}

/* Sidebar Title */
.sidebar-title {
    font-size: 16px;
    font-weight: 800;
    color: var(--text-primary);
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}

.sidebar-subtitle {
    font-size: 11px;
    color: var(--text-muted);
    letter-spacing: 0.3px;
    margin-bottom: 16px;
}

/* User Info in Sidebar */
.user-info-box {
    background: var(--bg-card);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-md);
    padding: 12px 14px;
    margin-bottom: 14px;
}

.user-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
}

.user-id {
    font-size: 11px;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
    margin-top: 2px;
}

/* Nav Separator */
.nav-separator {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: var(--text-muted);
    padding: 12px 4px 6px;
}

/* Page Title */
.page-title {
    font-size: 22px;
    font-weight: 800;
    color: var(--text-primary);
    letter-spacing: -0.5px;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.page-subtitle {
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 20px;
}

/* Chart Container */
.chart-container {
    background: var(--bg-card);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-lg);
    padding: 4px;
    overflow: hidden;
}

/* Tag / Badge */
.tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

.tag-green { background: #0A1F16; color: var(--accent-green); border: 1px solid #00D09C33; }
.tag-red   { background: #1F0A0A; color: var(--accent-red);   border: 1px solid #F8514933; }
.tag-yellow{ background: #1A140A; color: var(--accent-yellow); border: 1px solid #F0B42933; }
.tag-blue  { background: #0A0F1F; color: var(--accent-blue);  border: 1px solid #58A6FF33; }

/* Info Box */
.info-box {
    background: #0A0F1A;
    border: 1px solid #58A6FF22;
    border-left: 3px solid var(--accent-blue);
    border-radius: var(--radius-md);
    padding: 12px 16px;
    font-size: 13px;
    color: var(--text-secondary);
    margin: 8px 0;
}

/* Success Box */
.success-box {
    background: #0A1F16;
    border: 1px solid #00D09C33;
    border-left: 3px solid var(--accent-green);
    border-radius: var(--radius-md);
    padding: 12px 16px;
    font-size: 13px;
    color: var(--accent-green);
    margin: 8px 0;
}

/* Warning Box */
.warning-box {
    background: #1A140A;
    border: 1px solid #F0B42933;
    border-left: 3px solid var(--accent-yellow);
    border-radius: var(--radius-md);
    padding: 12px 16px;
    font-size: 13px;
    color: var(--accent-yellow);
    margin: 8px 0;
}

/* ===================== STREAMLIT OVERRIDES ===================== */

/* Remove default streamlit padding */
.block-container {
    padding: 20px 28px !important;
    max-width: 100% !important;
}

/* Title override */
h1 { 
    font-size: 22px !important; 
    font-weight: 800 !important; 
    color: var(--text-primary) !important;
    letter-spacing: -0.5px !important;
}

h2 { 
    font-size: 18px !important; 
    font-weight: 700 !important;
    color: var(--text-primary) !important;
}

h3 { 
    font-size: 15px !important; 
    font-weight: 600 !important;
    color: var(--text-primary) !important;
}

/* Caption */
.stCaption, [data-testid="stCaptionContainer"] {
    color: var(--text-muted) !important;
    font-size: 11px !important;
}

/* Subheader */
[data-testid="stHeading"] {
    color: var(--text-primary) !important;
}

/* Info / Success / Error / Warning */
[data-testid="stAlert"] {
    border-radius: var(--radius-md) !important;
    border: 1px solid !important;
    font-size: 13px !important;
}

/* Number input */
[data-testid="stNumberInput"] input {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 14px !important;
}

/* Checkbox */
[data-testid="stCheckbox"] label {
    font-size: 13px !important;
    color: var(--text-secondary) !important;
}

/* Select box */
[data-testid="stSelectbox"] label {
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
    color: var(--text-secondary) !important;
}

/* Text input label */
[data-testid="stTextInput"] label {
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
    color: var(--text-secondary) !important;
}

/* Toast */
[data-testid="stToast"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
}

/* Spinner */
[data-testid="stSpinner"] {
    color: var(--accent-green) !important;
}

/* Code block */
[data-testid="stCode"] {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border-primary) !important;
    border-radius: var(--radius-md) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
}

/* ===================== MOBILE RESPONSIVE ===================== */
@media (max-width: 768px) {
    .block-container {
        padding: 12px 14px !important;
    }

    .metric-card { padding: 12px 14px !important; }
    .metric-value { font-size: 16px !important; }

    .card { padding: 12px !important; }
    .news { padding: 10px 12px !important; font-size: 12px !important; }

    .login-box { padding: 24px 18px !important; margin: 20px auto !important; }

    h1 { font-size: 18px !important; }
    h2 { font-size: 16px !important; }
    h3 { font-size: 14px !important; }

    .price-display { font-size: 20px !important; }

    [data-testid="stMetricValue"] { font-size: 16px !important; }
}

@media (max-width: 480px) {
    .block-container { padding: 10px !important; }
    .login-box { padding: 20px 14px !important; }
}

/* ===================== PERFORMANCE ===================== */
* {
    will-change: auto;
    backface-visibility: hidden;
}

.stApp {
    transform: translateZ(0);
}

/* Reduce motion for performance */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# Paper Trading Banner
# ============================================================

st.markdown(
    '<div class="banner">⚠️ PAPER TRADING ONLY — No Real Money Involved</div>',
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

if not st.session_state.market_prices:
    st.session_state.market_prices = get_global_market_prices()

# ============================================================
# Session Timeout
# ============================================================

def check_session_timeout():
    if st.session_state.logged_in:
        elapsed = time.time() - st.session_state.last_activity
        if elapsed > SESSION_TIMEOUT:
            login_id = st.session_state.current_user.get("login_id", "unknown")
            try:
                add_audit_log(login_id, "SESSION_TIMEOUT", "Session expired")
            except Exception:
                pass
            st.session_state.clear()
            init_session_state()
            st.warning("Session expired. Please login again.")
            st.stop()
        st.session_state.last_activity = time.time()

# ============================================================
# CSRF
# ============================================================

def get_csrf_token():
    return st.session_state.csrf_token

def regenerate_csrf_token():
    st.session_state.csrf_token = secrets.token_hex(16)

def validate_csrf(token):
    return token == st.session_state.csrf_token

# ============================================================
# Load / Save Session
# ============================================================

def load_session_data():
    try:
        login_id = st.session_state.current_user.get("login_id")
        if not login_id:
            return
        data = get_user_data(login_id)
        st.session_state.balance        = round(float(data.get("balance", INIT_BALANCE)), 2)
        st.session_state.portfolio      = data.get("portfolio", {})
        st.session_state.pending_orders = data.get("pending_orders", [])
        st.session_state.total_pnl      = round(float(data.get("total_pnl", 0.0)), 2)
        st.session_state.holding_pnl    = data.get("holding_pnl", {})
        st.session_state.last_reset_date = data.get("last_reset_date", datetime.now().strftime("%Y-%m-%d"))
    except Exception as e:
        print(f"Load session error: {e}")

def save_session_data():
    try:
        if not st.session_state.logged_in:
            return
        if st.session_state.is_admin and not st.session_state.admin_viewing_as:
            return
        login_id = st.session_state.current_user.get("login_id")
        if not login_id:
            return
        data = {
            "balance":         round(float(st.session_state.balance), 2),
            "portfolio":       st.session_state.portfolio,
            "pending_orders":  st.session_state.pending_orders,
            "total_pnl":       round(float(st.session_state.total_pnl), 2),
            "holding_pnl":     st.session_state.holding_pnl,
            "last_reset_date": st.session_state.last_reset_date,
            "is_deleted":      0
        }
        save_data(login_id, data)
    except Exception as e:
        print(f"Save session error: {e}")

def sync_data():
    try:
        if time.time() - st.session_state.last_sync > SYNC_INTERVAL:
            if st.session_state.logged_in:
                if not st.session_state.is_admin or st.session_state.admin_viewing_as:
                    load_session_data()
            st.session_state.last_sync = time.time()
    except Exception as e:
        print(f"Sync error: {e}")

# ============================================================
# Market Prices
# ============================================================

def update_prices():
    try:
        current_time = time.time()
        if current_time - st.session_state.last_auto_update < AUTO_REFRESH:
            return
        st.session_state.last_auto_update = current_time
        prices = generate_candles()
        st.session_state.market_prices = prices
    except Exception as e:
        print(f"Update prices error: {e}")
        try:
            st.session_state.market_prices = get_global_market_prices()
        except Exception:
            pass

def check_day_reset():
    try:
        today = datetime.now(IST).strftime("%Y-%m-%d")
        if st.session_state.last_reset_date != today:
            st.session_state.total_pnl      = 0.0
            st.session_state.holding_pnl    = {}
            st.session_state.last_reset_date = today
            save_session_data()
            st.toast("📅 Day P&L reset at midnight IST")
    except Exception as e:
        print(f"Day reset error: {e}")

# ============================================================
# Portfolio Helpers
# ============================================================

def get_holding_qty(stock):
    holding = st.session_state.portfolio.get(stock, {})
    if isinstance(holding, dict):
        return holding.get("qty", 0)
    return int(holding) if holding else 0

def get_holding_avg(stock):
    holding = st.session_state.portfolio.get(stock, {})
    if isinstance(holding, dict):
        return holding.get("avg_price", 0.0)
    return 0.0

def get_portfolio_value():
    try:
        prices = st.session_state.market_prices
        return calculate_portfolio_value(st.session_state.portfolio, prices)
    except Exception:
        return 0.0

# ============================================================
# Place Order
# ============================================================

def place_order(side, o_type, stock, qty, price):
    try:
        if qty <= 0:
            st.error("Quantity must be greater than 0")
            return

        prices     = st.session_state.market_prices
        exec_price = prices.get(stock, STOCK_BASE_PRICES.get(stock, 0))
        base_price = STOCK_BASE_PRICES.get(stock, exec_price)

        upper_circuit = base_price * (1 + CIRCUIT_LIMIT)
        lower_circuit = base_price * (1 - CIRCUIT_LIMIT)

        if exec_price > upper_circuit or exec_price < lower_circuit:
            st.error(
                f"⚡ Circuit limit hit! {stock} frozen at "
                f"±{int(CIRCUIT_LIMIT * 100)}% | "
                f"Range: ₹{lower_circuit:.2f} – ₹{upper_circuit:.2f}"
            )
            return

        brokerage = round((exec_price * qty) * BROKERAGE_RATE, 2)
        status    = "FAILED"

        if o_type == ORDER_TYPE_MARKET:
            if side == "BUY":
                cost = round((exec_price * qty) + brokerage, 2)
                if cost <= st.session_state.balance:
                    st.session_state.balance = round(st.session_state.balance - cost, 2)
                    existing     = st.session_state.portfolio.get(stock, {})
                    existing_qty = existing.get("qty", 0) if isinstance(existing, dict) else int(existing or 0)
                    existing_avg = existing.get("avg_price", exec_price) if isinstance(existing, dict) else exec_price
                    new_qty = existing_qty + qty
                    new_avg = round(
                        ((existing_avg * existing_qty) + (exec_price * qty)) / new_qty, 2
                    ) if new_qty > 0 else exec_price
                    st.session_state.portfolio[stock] = {"qty": new_qty, "avg_price": new_avg}
                    status = "EXECUTED"
                    st.success(f"✅ Bought {qty} {stock} @ ₹{exec_price:.2f} | Brokerage: ₹{brokerage:.2f}")
                else:
                    st.error(f"❌ Insufficient Balance. Required: ₹{cost:,.2f} | Available: ₹{st.session_state.balance:,.2f}")
                    status = "FAILED"

            elif side == "SELL":
                holding   = st.session_state.portfolio.get(stock, {})
                owned_qty = holding.get("qty", 0) if isinstance(holding, dict) else int(holding or 0)
                if owned_qty == 0:
                    st.error(f"❌ You don't own {stock}")
                    status = "REJECTED"
                elif owned_qty < qty:
                    st.error(f"❌ Only {owned_qty} shares available.")
                    status = "REJECTED"
                else:
                    avg_price = holding.get("avg_price", exec_price) if isinstance(holding, dict) else exec_price
                    pnl = round((exec_price - avg_price) * qty - brokerage, 2)
                    st.session_state.total_pnl = round(st.session_state.total_pnl + pnl, 2)
                    st.session_state.holding_pnl[stock] = round(st.session_state.holding_pnl.get(stock, 0.0) + pnl, 2)
                    st.session_state.balance = round(st.session_state.balance + (exec_price * qty) - brokerage, 2)
                    new_qty = owned_qty - qty
                    if new_qty > 0:
                        st.session_state.portfolio[stock] = {"qty": new_qty, "avg_price": avg_price}
                    else:
                        st.session_state.portfolio.pop(stock, None)
                    status   = "EXECUTED"
                    pnl_text = f"Profit: ₹{pnl:.2f}" if pnl >= 0 else f"Loss: ₹{abs(pnl):.2f}"
                    st.success(f"✅ Sold {qty} {stock} @ ₹{exec_price:.2f} | {pnl_text} | Brokerage: ₹{brokerage:.2f}")

            order    = {
                "Time":      datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
                "Type":      f"MARKET {side}",
                "Stock":     stock,
                "Qty":       qty,
                "Price":     round(exec_price, 2),
                "Brokerage": brokerage,
                "Status":    status
            }
            login_id = st.session_state.current_user.get("login_id")
            if login_id:
                save_order(login_id, order)
            if status == "EXECUTED":
                save_session_data()
                load_session_data()

        elif o_type in [ORDER_TYPE_LIMIT, ORDER_TYPE_SL]:
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
            st.info(f"📋 {order_type_str} order placed for {qty} {stock} @ ₹{price:.2f}")

        st.rerun()

    except Exception as e:
        st.error(f"Order failed: {str(e)}")
        print(f"Place order error: {e}")

# ============================================================
# Check Pending Orders
# ============================================================

def check_pending_orders():
    try:
        if not st.session_state.pending_orders:
            return
        prices            = st.session_state.market_prices
        indices_to_remove = []

        for idx, order in enumerate(st.session_state.pending_orders):
            curr_price = prices.get(order['stock'], STOCK_BASE_PRICES.get(order['stock'], 0))
            executed   = False
            order_type = order.get('type', '')

            if   'LIMIT BUY'  in order_type and curr_price <= order['price']: executed = True
            elif 'LIMIT SELL' in order_type and curr_price >= order['price']: executed = True
            elif 'SL SELL'    in order_type and curr_price <= order['price']: executed = True
            elif 'SL BUY'     in order_type and curr_price >= order['price']: executed = True

            if executed:
                brokerage = round((order['price'] * order['qty']) * BROKERAGE_RATE, 2)
                exec_ok   = False

                if 'BUY' in order_type:
                    cost = round((order['price'] * order['qty']) + brokerage, 2)
                    if cost <= st.session_state.balance:
                        st.session_state.balance = round(st.session_state.balance - cost, 2)
                        existing     = st.session_state.portfolio.get(order['stock'], {})
                        existing_qty = existing.get("qty", 0) if isinstance(existing, dict) else int(existing or 0)
                        existing_avg = existing.get("avg_price", order['price']) if isinstance(existing, dict) else order['price']
                        new_qty = existing_qty + order['qty']
                        new_avg = round(((existing_avg * existing_qty) + (order['price'] * order['qty'])) / new_qty, 2) if new_qty > 0 else order['price']
                        st.session_state.portfolio[order['stock']] = {"qty": new_qty, "avg_price": new_avg}
                        exec_ok = True
                else:
                    holding   = st.session_state.portfolio.get(order['stock'], {})
                    owned_qty = holding.get("qty", 0) if isinstance(holding, dict) else int(holding or 0)
                    if owned_qty >= order['qty']:
                        avg_price = holding.get("avg_price", order['price']) if isinstance(holding, dict) else order['price']
                        pnl = round((order['price'] - avg_price) * order['qty'] - brokerage, 2)
                        st.session_state.total_pnl = round(st.session_state.total_pnl + pnl, 2)
                        st.session_state.balance   = round(st.session_state.balance + (order['price'] * order['qty']) - brokerage, 2)
                        new_qty = owned_qty - order['qty']
                        if new_qty > 0:
                            st.session_state.portfolio[order['stock']] = {"qty": new_qty, "avg_price": avg_price}
                        else:
                            st.session_state.portfolio.pop(order['stock'], None)
                        exec_ok = True

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
    if not st.session_state.is_admin or st.session_state.admin_viewing_as:
        col1, col2 = st.columns([8, 1])
        with col2:
            if st.button("← Back", key=f"back_{st.session_state.page}"):
                st.session_state.page = "Dashboard"
                st.rerun()

def top_bar():
    col1, col2, col3, col4 = st.columns([5, 2, 1, 1])
    with col1:
        name = st.session_state.current_user.get('full_name', 'User')
        if st.session_state.admin_viewing_as:
            name += " <span class='admin-badge'>ADMIN VIEW</span>"
        st.markdown(
            f'<div style="font-size:13px;color:#8B949E;">Welcome back, '
            f'<span style="color:#E6EDF3;font-weight:600;">{name}</span></div>',
            unsafe_allow_html=True
        )
    with col2:
        if st.session_state.admin_viewing_as:
            if st.button("👑 Back to Admin", key="back_admin_top"):
                st.session_state.is_admin         = True
                st.session_state.admin_viewing_as = None
                st.session_state.current_user     = {
                    "login_id":  ADMIN_LOGIN_ID,
                    "full_name": "Admin",
                    "bio":       "System Administrator"
                }
                st.rerun()
    with col3:
        if st.button("⟳ Refresh", key="top_refresh"):
            update_prices()
            st.rerun()
    with col4:
        if st.button("Logout", key="top_logout"):
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
# Auth Page - Premium Trading Terminal Login
# ============================================================

def auth_page():
    # Header
    st.markdown("""
    <div style="text-align:center; padding: 40px 0 20px;">
        <div style="font-size:40px; margin-bottom:10px;">📈</div>
        <div style="font-size:26px; font-weight:800; color:#E6EDF3; letter-spacing:-0.5px;">
            TRADE with MB
        </div>
        <div style="font-size:13px; color:#8B949E; margin-top:6px; letter-spacing:0.5px;">
            Paper Trading Terminal — Educational Use Only
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="disclaimer">'
        '📌 This is a PAPER TRADING platform for educational purposes only. '
        'No real money involved.'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🔑 Login", "📝 Register", "🔓 Forgot Password"])

    # Login Tab
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        login_id_input = st.text_input(
            "Login ID",
            key="login_id_input",
            placeholder="Your 4-character Login ID"
        )
        password_input = st.text_input(
            "Password",
            type="password",
            key="login_pass",
            placeholder="Enter your password"
        )
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Login →", type="primary", use_container_width=True):
            if not login_id_input or not password_input:
                st.error("Please enter both Login ID and Password")
            else:
                login_id_clean = login_id_input.strip().upper()
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
                    allowed, remaining = check_rate_limit(login_id_clean)
                    if not allowed:
                        st.error(f"Account locked. Try again in {remaining} seconds.")
                    else:
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
                            st.success(f"Welcome back, {user['full_name']}!")
                            st.rerun()
                        else:
                            attempts, locked = record_failed_attempt(login_id_clean)
                            if locked:
                                st.error("Too many failed attempts! Account locked for 10 minutes.")
                            else:
                                remaining_attempts = RATE_LIMIT_ATTEMPTS - attempts
                                st.error(f"Invalid credentials. {remaining_attempts} attempts remaining.")

    # Register Tab
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        full_name  = st.text_input("Full Name",        key="reg_name", placeholder="Your full name")
        bio        = st.text_input("Bio",              key="reg_bio",  placeholder="Tell us about yourself")
        fav_number = st.text_input(
            "Favourite Number",
            key="reg_fav",
            type="password",
            placeholder="A number for password recovery (e.g. 42)"
        )
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Create Account →", use_container_width=True):
            if not full_name or not fav_number:
                st.error("Full Name and Favourite Number are required")
            elif not validate_favourite_number(fav_number):
                st.error("Favourite Number must be numeric (e.g. 42)")
            elif is_duplicate_name(full_name):
                st.error("An account with this name already exists")
            else:
                with st.spinner("Creating account..."):
                    login_id, raw_password, error = register_user(full_name, bio, fav_number)
                if login_id:
                    st.session_state.show_credentials = True
                    st.session_state.new_login_id     = login_id
                    st.session_state.new_password     = raw_password
                    st.success("Account created! Save your credentials below.")
                else:
                    st.error(f"Registration failed: {error}")

        if st.session_state.show_credentials and st.session_state.new_login_id:
            st.markdown(f"""
            <div class="cred-box">
                <p><b>Login ID:</b> {st.session_state.new_login_id}</p>
                <p><b>Password:</b> {st.session_state.new_password}</p>
                <p style="color:#F85149; font-size:12px; margin-top:10px;">
                    ⚠️ Save these now — you cannot recover them later!
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
                    saved_id   = st.session_state.new_login_id
                    saved_pass = st.session_state.new_password
                    st.session_state.show_credentials = False
                    st.session_state.new_login_id     = ""
                    st.session_state.new_password     = ""
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

    # Forgot Password Tab
    with tab3:
        st.markdown("<br>", unsafe_allow_html=True)
        forgot_lid = st.text_input("Login ID",        key="forgot_id",  placeholder="Your Login ID")
        forgot_fav = st.text_input("Favourite Number",key="forgot_fav", type="password", placeholder="Your favourite number")
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Reset Password →", use_container_width=True):
            if not forgot_lid or not forgot_fav:
                st.error("Both fields are required")
            elif not validate_favourite_number(forgot_fav):
                st.error("Favourite Number must be numeric")
            else:
                forgot_lid_clean = forgot_lid.strip().upper()
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
                            <p><b>Login ID:</b> {forgot_lid_clean}</p>
                            <p><b>New Password:</b> {new_pass}</p>
                            <p style="color:#F85149; font-size:12px; margin-top:10px;">⚠️ Save this now!</p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.code(f"Login ID: {forgot_lid_clean}\nNew Password: {new_pass}", language="text")
                    else:
                        record_forgot_password_attempt(forgot_lid_clean)
                        st.error(error or "Invalid Login ID or Wrong Favourite Number")

# ============================================================
# Auth Gate
# ============================================================

if not st.session_state.logged_in:
    auth_page()
    st.stop()

check_session_timeout()
sync_data()

# ============================================================
# FRAGMENT 1: Watchlist
# ============================================================

@st.fragment(run_every=5)
def watchlist_fragment():
    update_prices()
    check_pending_orders()
    prices = st.session_state.market_prices

    st.markdown('<div class="section-header">📋 Watchlist</div>', unsafe_allow_html=True)

    search_watch = st.text_input("", key="watchlist_search", placeholder="🔍 Search stock...")

    for stock in STOCKS.keys():
        if search_watch and search_watch.upper() not in stock:
            continue

        price  = prices.get(stock, STOCK_BASE_PRICES[stock])
        base   = STOCK_BASE_PRICES[stock]
        change = ((price - base) / base) * 100
        owned  = get_holding_qty(stock)

        color     = "#00D09C" if change >= 0 else "#F85149"
        arrow     = "▲" if change >= 0 else "▼"
        own_badge = '<span class="tag tag-green" style="float:right;">OWNED</span>' if owned > 0 else ""

        is_selected = stock == st.session_state.selected_stock
        border_style = f"border-color: #00D09C55; background: #0A1F16;" if is_selected else ""

        if st.button(
            f"{arrow} {stock}  ₹{price:.2f}  ({change:+.2f}%)",
            key=f"watch_{stock}",
            use_container_width=True,
            help=f"Holdings: {owned} shares" if owned > 0 else stock
        ):
            st.session_state.selected_stock = stock
            st.rerun()

# ============================================================
# FRAGMENT 2: Chart
# ============================================================

@st.fragment(run_every=8)
def chart_fragment():
    selected = st.session_state.selected_stock
    prices   = st.session_state.market_prices
    price    = prices.get(selected, STOCK_BASE_PRICES[selected])
    base     = STOCK_BASE_PRICES[selected]
    change   = ((price - base) / base) * 100
    color    = "#00D09C" if change >= 0 else "#F85149"

    # Stock header
    st.markdown(f"""
    <div style="display:flex; align-items:center; justify-content:space-between; 
                margin-bottom:12px; padding:14px 18px;
                background:#111620; border:1px solid #1E2733; 
                border-radius:10px;">
        <div>
            <div style="font-size:16px; font-weight:700; color:#E6EDF3;">
                {selected}
            </div>
            <div style="font-size:11px; color:#8B949E; margin-top:2px;">
                NSE · Paper Trading
            </div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:24px; font-weight:700; 
                        font-family:'JetBrains Mono',monospace; 
                        color:#E6EDF3; letter-spacing:-1px;">
                ₹{price:.2f}
            </div>
            <div style="font-size:13px; font-weight:600; color:{color};">
                {'▲' if change >= 0 else '▼'} {abs(change):.2f}%
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    candles = get_candles(selected, limit=80)

    if not candles or len(candles) < 3:
        st.markdown(
            '<div class="info-box">⏳ Generating live data... Please wait 30 seconds.</div>',
            unsafe_allow_html=True
        )
        return

    dates  = [c["timestamp"] for c in candles]
    opens  = [c["open"]  for c in candles]
    highs  = [c["high"]  for c in candles]
    lows   = [c["low"]   for c in candles]
    closes = [c["close"] for c in candles]

    # Volume (simulated)
    volumes = [abs(closes[i] - opens[i]) * 1000 + 500 for i in range(len(closes))]

    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=dates,
        open=opens, high=highs, low=lows, close=closes,
        name=selected,
        increasing=dict(
            line=dict(color="#00D09C", width=1.5),
            fillcolor="#00D09C"
        ),
        decreasing=dict(
            line=dict(color="#F85149", width=1.5),
            fillcolor="#F85149"
        ),
        whiskerwidth=0.3
    ))

    # Volume bars at bottom
    vol_colors = ["#00D09C44" if closes[i] >= opens[i] else "#F8514944" for i in range(len(closes))]
    fig.add_trace(go.Bar(
        x=dates,
        y=volumes,
        name="Volume",
        marker_color=vol_colors,
        yaxis="y2",
        showlegend=False,
        hovertemplate="Vol: %{y:.0f}<extra></extra>"
    ))

    # SMA lines
    if len(closes) >= 10:
        sma5  = [sum(closes[max(0,i-4):i+1]) / min(5,  i+1) for i in range(len(closes))]
        sma10 = [sum(closes[max(0,i-9):i+1]) / min(10, i+1) for i in range(len(closes))]
        fig.add_trace(go.Scatter(
            x=dates, y=sma5,
            name="SMA 5",
            line=dict(color="#F0B429", width=1.2, dash="dot"),
            opacity=0.8,
            hovertemplate="SMA5: ₹%{y:.2f}<extra></extra>"
        ))
        fig.add_trace(go.Scatter(
            x=dates, y=sma10,
            name="SMA 10",
            line=dict(color="#58A6FF", width=1.2, dash="dot"),
            opacity=0.8,
            hovertemplate="SMA10: ₹%{y:.2f}<extra></extra>"
        ))

    fig.update_layout(
        template="plotly_dark",
        height=420,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="#111620",
        plot_bgcolor="#111620",
        xaxis_rangeslider_visible=False,
        uirevision="chart_stable",
        transition={"duration": 0},
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.01,
            xanchor="left",   x=0,
            font=dict(size=10, color="#8B949E"),
            bgcolor="rgba(0,0,0,0)"
        ),
        xaxis=dict(
            range=[
                dates[-30] if len(dates) > 30 else dates[0],
                dates[-1]
            ],
            gridcolor="#1E2733",
            showgrid=True,
            zeroline=False,
            tickfont=dict(size=10, color="#484F58"),
            showspikes=True,
            spikecolor="#00D09C44",
            spikethickness=1,
        ),
        yaxis=dict(
            gridcolor="#1E2733",
            showgrid=True,
            zeroline=False,
            tickfont=dict(size=10, color="#484F58"),
            tickprefix="₹",
            side="right",
            showspikes=True,
            spikecolor="#00D09C44",
            spikethickness=1,
            domain=[0.25, 1.0]
        ),
        yaxis2=dict(
            domain=[0.0, 0.22],
            showgrid=False,
            showticklabels=False,
            zeroline=False
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#0D1117",
            bordercolor="#1E2733",
            font=dict(size=12, color="#E6EDF3", family="JetBrains Mono")
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="live_chart",
        config={
            "scrollZoom":      True,
            "displayModeBar":  True,
            "modeBarButtonsToRemove": [
                "select2d", "lasso2d", "autoScale2d",
                "hoverClosestCartesian", "hoverCompareCartesian",
                "toImage"
            ],
            "displaylogo": False
        }
    )
    st.markdown(
        '<div style="font-size:11px;color:#484F58;text-align:right;margin-top:-8px;">'
        '🔄 Updates every 8s · SMA5 · SMA10 · Volume</div>',
        unsafe_allow_html=True
    )

# ============================================================
# FRAGMENT 3: News
# ============================================================

@st.fragment(run_every=60)
def news_fragment():
    st.markdown('<div class="section-header">📰 Market News</div>', unsafe_allow_html=True)

    if time.time() - st.session_state.news_update_time > 60:
        st.session_state.news = random.sample(FAKE_NEWS_POOL, 5)
        st.session_state.news_update_time = time.time()

    for n in st.session_state.news:
        st.markdown(f'<div class="news">🔔 {n}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div style="font-size:10px;color:#484F58;margin-top:6px;">'
        '⚠️ Simulated news — not real market data</div>',
        unsafe_allow_html=True
    )

# ============================================================
# Order Section
# ============================================================

def order_section():
    prices    = st.session_state.market_prices
    stock     = st.session_state.selected_stock
    price     = prices.get(stock, STOCK_BASE_PRICES[stock])
    owned_qty = get_holding_qty(stock)
    avg_price = get_holding_avg(stock)
    base      = STOCK_BASE_PRICES[stock]
    change    = ((price - base) / base) * 100
    pnl_color = "#00D09C" if change >= 0 else "#F85149"

    st.markdown('<div class="section-header">📝 Place Order</div>', unsafe_allow_html=True)

    # Current holding info
    if owned_qty > 0:
        holding_pnl = (price - avg_price) * owned_qty
        hp_color    = "#00D09C" if holding_pnl >= 0 else "#F85149"
        st.markdown(f"""
        <div style="background:#0A1F16; border:1px solid #00D09C33;
                    border-radius:8px; padding:10px 14px; margin-bottom:10px;">
            <div style="font-size:10px;font-weight:600;letter-spacing:0.8px;
                        text-transform:uppercase;color:#00D09C;margin-bottom:6px;">
                Current Position
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-size:13px;color:#E6EDF3;font-weight:600;">
                        {owned_qty} shares
                    </div>
                    <div style="font-size:11px;color:#8B949E;margin-top:2px;">
                        Avg: ₹{avg_price:.2f}
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:13px;font-weight:600;color:{hp_color};">
                        {'▲' if holding_pnl >= 0 else '▼'} ₹{abs(holding_pnl):.2f}
                    </div>
                    <div style="font-size:11px;color:#8B949E;margin-top:2px;">
                        Unrealized P&L
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

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
    total_cost    = round(price * qty + est_brokerage, 2)

    st.markdown(f"""
    <div class="brokerage-info">
        <div style="display:flex;justify-content:space-between;">
            <span>Brokerage</span>
            <span>₹{est_brokerage:.2f}</span>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:4px;
                    color:#E6EDF3;font-weight:600;">
            <span>Total Cost</span>
            <span>₹{total_cost:,.2f}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_b, col_s = st.columns(2)

    with col_b:
        if st.button("▲ BUY", use_container_width=True, type="primary", key="buy_btn"):
            place_order("BUY", order_type, stock, qty, limit_price)

    with col_s:
        if owned_qty > 0:
            if st.button(f"▼ SELL ({owned_qty})", use_container_width=True, key="sell_btn"):
                place_order("SELL", order_type, stock, min(qty, owned_qty), limit_price)
        else:
            st.button("▼ SELL", disabled=True, use_container_width=True, key="sell_btn_dis", help="Buy first")

    # Balance display
    st.markdown(f"""
    <div style="margin-top:12px; padding:10px 14px;
                background:#0D1117; border:1px solid #1E2733;
                border-radius:8px;">
        <div style="font-size:10px;color:#8B949E;letter-spacing:0.8px;
                    text-transform:uppercase;margin-bottom:4px;">
            Available Balance
        </div>
        <div style="font-size:18px;font-weight:700;
                    font-family:'JetBrains Mono',monospace;color:#E6EDF3;">
            ₹{st.session_state.balance:,.2f}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# Holdings Section
# ============================================================

def holdings_section():
    st.markdown('<div class="section-header">💼 Holdings</div>', unsafe_allow_html=True)
    prices       = st.session_state.market_prices
    holdings_data = []

    for stk, holding in st.session_state.portfolio.items():
        qty = holding.get("qty", 0) if isinstance(holding, dict) else int(holding or 0)
        avg = holding.get("avg_price", 0) if isinstance(holding, dict) else 0
        if qty > 0:
            ltp     = prices.get(stk, STOCK_BASE_PRICES.get(stk, 0))
            value   = round(qty * ltp, 2)
            pnl     = round((ltp - avg) * qty, 2)
            pnl_pct = round(((ltp - avg) / avg * 100), 2) if avg > 0 else 0
            holdings_data.append({
                "Stock": stk,
                "Qty":   qty,
                "Avg":   f"₹{avg:.2f}",
                "LTP":   f"₹{ltp:.2f}",
                "Value": f"₹{value:,.2f}",
                "P&L":   f"₹{pnl:,.2f} ({pnl_pct:+.1f}%)"
            })

    if holdings_data:
        st.dataframe(pd.DataFrame(holdings_data), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="info-box">No holdings yet. Buy a stock to start!</div>', unsafe_allow_html=True)

# ============================================================
# Order Book Section
# ============================================================

def orderbook_section():
    st.markdown('<div class="section-header">📜 Order Book</div>', unsafe_allow_html=True)
    login_id = st.session_state.current_user.get("login_id", "")
    orders   = get_orders(login_id, limit=50)

    if orders:
        orders_display = []
        for o in orders[::-1]:
            orders_display.append({
                "Time":   o.get("Time", ""),
                "Type":   o.get("Type", ""),
                "Stock":  o.get("Stock", ""),
                "Qty":    o.get("Qty", 0),
                "Price":  f"₹{float(o.get('Price', 0)):.2f}",
                "Status": o.get("Status", "")
            })
        st.dataframe(pd.DataFrame(orders_display), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="info-box">No orders yet. Place your first trade!</div>', unsafe_allow_html=True)

# ============================================================
# Pending Orders Section
# ============================================================

def pending_orders_section():
    st.markdown('<div class="section-header">⏳ Pending Orders</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:11px;color:#484F58;margin-bottom:8px;">'
        'Pending P&L excluded from Today\'s Total</div>',
        unsafe_allow_html=True
    )

    pending = st.session_state.pending_orders
    if pending:
        pending_display = []
        for o in pending:
            pending_display.append({
                "Type":   o.get("type", ""),
                "Stock":  o.get("stock", ""),
                "Qty":    o.get("qty", 0),
                "Price":  f"₹{float(o.get('price', 0)):.2f}",
                "Placed": o.get("placed_at", "")
            })
        st.dataframe(pd.DataFrame(pending_display), use_container_width=True, hide_index=True)
        if st.button("🗑️ Cancel All Pending", key="cancel_pending"):
            st.session_state.pending_orders = []
            save_session_data()
            st.success("All pending orders cancelled")
            st.rerun()
    else:
        st.markdown('<div class="info-box">No pending orders</div>', unsafe_allow_html=True)

# ============================================================
# DASHBOARD
# ============================================================

def dashboard_page():
    check_day_reset()

    # Page header
    st.markdown("""
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px;">
        <div>
            <div class="page-title">📈 TRADE with MB</div>
            <div class="page-subtitle">Live Paper Trading Terminal</div>
        </div>
        <div class="market-status">MARKET OPEN 24/7</div>
    </div>
    """, unsafe_allow_html=True)

    top_bar()

    # Metrics Row
    prices          = st.session_state.market_prices
    portfolio_value = get_portfolio_value()
    net_worth       = round(st.session_state.balance + portfolio_value, 2)
    pnl             = st.session_state.total_pnl
    pnl_color       = "#00D09C" if pnl >= 0 else "#F85149"
    total_trades    = get_orders_count(st.session_state.current_user.get("login_id", ""))

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">💰 Balance</div>
            <div class="metric-value">₹{st.session_state.balance:,.0f}</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">📊 Portfolio</div>
            <div class="metric-value">₹{portfolio_value:,.0f}</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">📈 Today P&L</div>
            <div class="metric-value" style="color:{pnl_color};">
                {'▲' if pnl >= 0 else '▼'} ₹{abs(pnl):,.0f}
            </div>
            <div class="metric-sub">Resets midnight IST</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">🏦 Net Worth</div>
            <div class="metric-value">₹{net_worth:,.0f}</div>
        </div>""", unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">🔢 Total Trades</div>
            <div class="metric-value">{total_trades}</div>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # Main Trading Layout
    col_watch, col_chart, col_order = st.columns([1, 2.2, 1])

    with col_watch:
        watchlist_fragment()

    with col_chart:
        chart_fragment()
        st.markdown("<br>", unsafe_allow_html=True)
        news_fragment()

    with col_order:
        order_section()

    st.divider()

    # Bottom Panels
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
    back_button()
    top_bar()

    st.markdown('<div class="page-title">📜 Trade History</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">All your executed and pending trades</div>', unsafe_allow_html=True)

    login_id = st.session_state.current_user.get("login_id", "")
    orders   = get_orders(login_id, limit=MAX_ORDER_BOOK)

    if orders:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            search_stock = st.text_input("Search Stock", placeholder="Stock name...")
        with col2:
            filter_type  = st.selectbox("Type",   ["All", "BUY", "SELL"])
        with col3:
            filter_status= st.selectbox("Status", ["All", "EXECUTED", "FAILED", "REJECTED"])
        with col4:
            filter_date  = st.date_input("Date", value=None)

        filtered = orders[::-1]
        if search_stock:
            filtered = [o for o in filtered if search_stock.upper() in o.get("Stock", "").upper()]
        if filter_type != "All":
            filtered = [o for o in filtered if filter_type in o.get("Type", "")]
        if filter_status != "All":
            filtered = [o for o in filtered if o.get("Status") == filter_status]
        if filter_date:
            date_str = filter_date.strftime("%Y-%m-%d")
            filtered = [o for o in filtered if o.get("Time", "").startswith(date_str)]

        st.dataframe(
            pd.DataFrame(filtered) if filtered else pd.DataFrame(
                columns=["Time", "Type", "Stock", "Qty", "Price", "Brokerage", "Status"]
            ),
            use_container_width=True,
            hide_index=True
        )

        col_exp, col_clear = st.columns(2)
        with col_exp:
            if st.button("📥 Export to CSV"):
                with st.spinner("Generating CSV..."):
                    filepath = export_trades_csv(login_id)
                if filepath:
                    with open(filepath, 'r', encoding='utf-8-sig') as f:
                        csv_data = f.read()
                    st.download_button("⬇️ Download CSV", csv_data,
                                       file_name=f"trades_{login_id}.csv", mime="text/csv")
                    cleanup_export_file(filepath)
                else:
                    st.warning("No trades to export")
        with col_clear:
            if st.button("🗑️ Clear History"):
                st.warning("This will clear display. Data remains in database.")
    else:
        st.markdown('<div class="info-box">No trades yet. Go to Dashboard to place your first trade!</div>', unsafe_allow_html=True)

# ============================================================
# Funds Page
# ============================================================

def funds_page():
    back_button()
    top_bar()

    st.markdown('<div class="page-title">💰 Funds</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Manage your paper trading balance</div>', unsafe_allow_html=True)

    portfolio_value = get_portfolio_value()
    net_worth       = round(st.session_state.balance + portfolio_value, 2)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">💵 Available Balance</div>
            <div class="metric-value">₹{st.session_state.balance:,.2f}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">📊 Portfolio Value</div>
            <div class="metric-value">₹{portfolio_value:,.2f}</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">🏦 Net Worth</div>
            <div class="metric-value">₹{net_worth:,.2f}</div>
        </div>""", unsafe_allow_html=True)

    st.divider()

    st.markdown('<div class="section-header">➕ Add Funds</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:12px;color:#8B949E;margin-bottom:12px;">'
        f'Maximum per transaction: ₹{MAX_ADD_FUNDS:,}</div>',
        unsafe_allow_html=True
    )

    add_amount = st.number_input("Amount", min_value=10000, max_value=MAX_ADD_FUNDS, value=10000, step=1000)

    if st.button("Add Funds →", type="primary", use_container_width=True):
        st.session_state.balance = round(st.session_state.balance + add_amount, 2)
        save_session_data()
        st.success(f"✅ ₹{add_amount:,.2f} added successfully!")
        st.rerun()

# ============================================================
# Settings Page
# ============================================================

def settings_page():
    back_button()
    top_bar()

    st.markdown('<div class="page-title">⚙️ Settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Account preferences and management</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="success-box">
        🌙 Dark Mode — Active & Locked
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    if not st.session_state.is_admin:
        st.markdown('<div class="section-header">🔄 Reset Account</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="warning-box">
            This resets balance, portfolio, P&L, and pending orders.
            Trade history and profile are kept.
        </div>
        """, unsafe_allow_html=True)

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
                "RESET", "Account reset by user"
            )
            st.success("Account reset successfully!")
            st.rerun()

        st.divider()

        st.markdown('<div class="section-header">🗑️ Delete Account</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#1F0A0A; border:1px solid #F8514933;
                    border-left:3px solid #F85149; border-radius:8px;
                    padding:12px 16px; font-size:13px; color:#F87171;">
            ⚠️ This will PERMANENTLY delete your account.
            You cannot login again after this action.
        </div>
        """, unsafe_allow_html=True)

        confirm_text = st.text_input("Type DELETE to confirm", placeholder="DELETE")
        if st.button("Delete Account", type="primary", disabled=(confirm_text != "DELETE")):
            login_id = st.session_state.current_user.get("login_id", "")
            with st.spinner("Deleting account..."):
                soft_delete_user(login_id)
            st.session_state.clear()
            init_session_state()
            st.success("Account deleted.")
            st.rerun()

# ============================================================
# Profile Page
# ============================================================

def profile_page():
    back_button()
    top_bar()

    st.markdown('<div class="page-title">👤 My Profile</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Your account details and trading stats</div>', unsafe_allow_html=True)

    user = st.session_state.current_user

    st.markdown('<div class="profile-box">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Login ID",    value=user.get("login_id",   ""), disabled=True)
        st.text_input("Name",        value=user.get("full_name",  ""), disabled=True)
    with col2:
        st.text_input("Member Since",value=user.get("created_at", "N/A"), disabled=True)

    new_bio = st.text_area("Bio", value=user.get("bio", ""),
                           placeholder="Tell us about yourself...", max_chars=200)

    if st.button("Update Bio →", type="primary"):
        from db import users_col, sanitize_string
        login_id    = user.get("login_id", "")
        new_bio_clean = sanitize_string(new_bio, max_length=200)
        try:
            users_col.update_one(
                {"login_id": login_id},
                {"$set": {"bio": new_bio_clean}}
            )
            st.session_state.current_user["bio"] = new_bio_clean
            add_audit_log(login_id, "PROFILE_UPDATE", "Bio updated")
            st.success("Bio updated!")
        except Exception as e:
            st.error(f"Update failed: {e}")

    st.markdown('</div>', unsafe_allow_html=True)
    st.divider()

    st.markdown('<div class="section-header">📊 Account Stats</div>', unsafe_allow_html=True)
    login_id     = user.get("login_id", "")
    total_trades = get_orders_count(login_id)
    orders       = get_orders(login_id, limit=500)
    executed     = [o for o in orders if o.get("Status") == "EXECUTED"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Trades</div>
            <div class="metric-value">{total_trades}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Executed</div>
            <div class="metric-value">{len(executed)}</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Balance</div>
            <div class="metric-value">₹{st.session_state.balance:,.0f}</div>
        </div>""", unsafe_allow_html=True)

# ============================================================
# Leaderboard Page
# ============================================================

def leaderboard_page():
    back_button()
    top_bar()

    st.markdown('<div class="page-title">🏆 Leaderboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Top traders by net worth</div>', unsafe_allow_html=True)

    current_time     = time.time()
    current_login_id = st.session_state.current_user.get("login_id", "")

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
                lid       = user["login_id"]
                data      = all_data.get(lid, {})
                balance   = float(data.get("balance", INIT_BALANCE))
                portfolio = data.get("portfolio", {})
                pv        = calculate_portfolio_value(portfolio, prices)
                net_worth = round(balance + pv, 2)
                pnl       = float(data.get("total_pnl", 0))
                leaderboard.append({
                    "login_id":  lid,
                    "Name":      user["full_name"],
                    "Net Worth": net_worth,
                    "P&L":       pnl,
                    "Trades":    get_orders_count(lid),
                    "Joined":    user.get("created_at", "N/A")
                })

            leaderboard.sort(key=lambda x: x["Net Worth"], reverse=True)
            formatted = []
            for i, entry in enumerate(leaderboard):
                is_me = "⭐" if entry["login_id"] == current_login_id else ""
                medal = ["🥇","🥈","🥉"][i] if i < 3 else f"#{i+1}"
                formatted.append({
                    "Rank":      medal,
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
            use_container_width=True, hide_index=True
        )
    else:
        st.markdown('<div class="info-box">No users yet</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div style="font-size:11px;color:#484F58;margin-top:8px;">'
        f'⭐ = You · Refreshes every 5 min · '
        f'Last: {datetime.fromtimestamp(st.session_state.leaderboard_cache_time).strftime("%H:%M:%S")}'
        f'</div>',
        unsafe_allow_html=True
    )

# ============================================================
# Admin Panel
# ============================================================

def admin_panel():
    top_bar()

    st.markdown('<div class="page-title">👑 Admin Panel</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">User management and system overview</div>', unsafe_allow_html=True)

    users    = get_all_users()
    all_data = get_all_user_data()
    prices   = get_global_market_prices()

    st.markdown('<div class="section-header">📊 All Users Dashboard</div>', unsafe_allow_html=True)
    admin_data = []
    for user in users:
        lid       = user["login_id"]
        data      = all_data.get(lid, {})
        balance   = float(data.get("balance", INIT_BALANCE))
        portfolio = data.get("portfolio", {})
        pv        = calculate_portfolio_value(portfolio, prices)
        net_worth = round(balance + pv, 2)
        admin_data.append({
            "Login ID":  lid,
            "Name":      user["full_name"],
            "Balance":   f"₹{balance:,.2f}",
            "Portfolio": f"₹{pv:,.2f}",
            "Net Worth": f"₹{net_worth:,.2f}",
            "Total P&L": f"₹{float(data.get('total_pnl', 0)):,.2f}",
            "Joined":    user.get("created_at", "N/A")
        })

    st.dataframe(
        pd.DataFrame(admin_data) if admin_data else pd.DataFrame(),
        use_container_width=True, hide_index=True
    )

    if st.button("📥 Export Users CSV"):
        with st.spinner("Generating..."):
            filepath = export_users_csv()
        if filepath:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                csv_data = f.read()
            st.download_button("⬇️ Download", csv_data,
                               file_name="users_export.csv", mime="text/csv")
            cleanup_export_file(filepath)
        else:
            st.warning("No users to export")

    st.divider()

    st.markdown('<div class="section-header">👁️ View as User</div>', unsafe_allow_html=True)
    if users:
        user_options    = {f"{u['full_name']} ({u['login_id']})": u['login_id'] for u in users}
        selected_display = st.selectbox("Select User", list(user_options.keys()), key="admin_view_user")
        search_admin    = st.text_input("Search User", placeholder="Name or Login ID...", key="admin_search")

        filtered_users = users
        if search_admin:
            filtered_users = [
                u for u in users
                if search_admin.upper() in u["login_id"].upper()
                or search_admin.lower() in u["full_name"].lower()
            ]
            if filtered_users:
                selected_display = f"{filtered_users[0]['full_name']} ({filtered_users[0]['login_id']})"

        if st.button("View as User →", type="primary"):
            selected_lid = user_options.get(selected_display)
            if selected_lid:
                user = next((u for u in users if u["login_id"] == selected_lid), None)
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

    st.markdown('<div class="section-header">⚠️ Delete User</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#1F0A0A; border:1px solid #F8514933;
                border-left:3px solid #F85149; border-radius:8px;
                padding:10px 14px; font-size:12px; color:#F87171; margin-bottom:12px;">
        Soft delete — user loses access but data is retained
    </div>
    """, unsafe_allow_html=True)

    if users:
        delete_options  = {f"{u['full_name']} ({u['login_id']})": u['login_id'] for u in users}
        delete_display  = st.selectbox("Select User to Delete", list(delete_options.keys()), key="admin_del")
        confirm_delete  = st.checkbox("I confirm deletion", key="confirm_del_check")
        if st.button("Delete User", key="del_btn", disabled=not confirm_delete):
            delete_lid = delete_options.get(delete_display)
            if delete_lid:
                with st.spinner("Deleting..."):
                    soft_delete_user(delete_lid)
                st.success(f"User {delete_lid} deleted")
                st.rerun()

    st.divider()

    st.markdown('<div class="section-header">📋 Audit Logs</div>', unsafe_allow_html=True)
    logs = get_audit_logs(limit=100)
    if logs:
        st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="info-box">No audit logs yet</div>', unsafe_allow_html=True)

# ============================================================
# Analytics Page
# ============================================================

def analytics_page():
    back_button()
    top_bar()

    st.markdown('<div class="page-title">📊 Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Your trading performance overview</div>', unsafe_allow_html=True)

    login_id     = st.session_state.current_user.get("login_id", "")
    orders       = get_orders(login_id, limit=500)
    total_trades = get_orders_count(login_id)

    col1, col2, col3, col4 = st.columns(4)
    executed  = [o for o in orders if o.get("Status") == "EXECUTED"] if orders else []
    buy_exec  = [o for o in executed if "BUY"  in o.get("Type", "")]
    sell_exec = [o for o in executed if "SELL" in o.get("Type", "")]
    total_brokerage = round(sum(float(o.get("Brokerage", 0)) for o in executed), 2)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Trades</div>
            <div class="metric-value">{total_trades}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Buy Orders</div>
            <div class="metric-value" style="color:#00D09C;">{len(buy_exec)}</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Sell Orders</div>
            <div class="metric-value" style="color:#F85149;">{len(sell_exec)}</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Brokerage Paid</div>
            <div class="metric-value">₹{total_brokerage:,.2f}</div>
        </div>""", unsafe_allow_html=True)

    if orders:
        st.divider()
        st.markdown('<div class="section-header">📈 P&L Trend</div>', unsafe_allow_html=True)
        pnl_data    = []
        running_pnl = 0.0

        for o in orders:
            if o.get("Status") == "EXECUTED" and "SELL" in o.get("Type", ""):
                price     = float(o.get("Price", 0))
                qty       = int(o.get("Qty", 0))
                brokerage = float(o.get("Brokerage", 0))
                running_pnl += round((price * qty) - brokerage, 2)
                pnl_data.append(running_pnl)

        if pnl_data:
            line_color = "#00D09C" if pnl_data[-1] >= 0 else "#F85149"
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                y=pnl_data,
                mode='lines+markers',
                line=dict(color=line_color, width=2),
                marker=dict(size=4, color=line_color),
                fill='tozeroy',
                fillcolor=f"{line_color}15",
                hovertemplate="P&L: ₹%{y:,.2f}<extra></extra>"
            ))
            fig.update_layout(
                template="plotly_dark",
                height=300,
                paper_bgcolor="#111620",
                plot_bgcolor="#111620",
                margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(
                    gridcolor="#1E2733",
                    tickprefix="₹",
                    tickfont=dict(size=10, color="#8B949E")
                ),
                xaxis=dict(
                    gridcolor="#1E2733",
                    tickfont=dict(size=10, color="#8B949E")
                ),
                hoverlabel=dict(
                    bgcolor="#0D1117",
                    bordercolor="#1E2733",
                    font=dict(size=12, color="#E6EDF3", family="JetBrains Mono")
                )
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown('<div class="info-box">No sell trades yet for P&L chart</div>', unsafe_allow_html=True)

        st.divider()
        st.markdown('<div class="section-header">🏆 Trade Summary</div>', unsafe_allow_html=True)
        sell_trades = [o for o in orders if o.get("Status") == "EXECUTED" and "SELL" in o.get("Type","")]
        if sell_trades:
            trade_pnls = []
            for o in sell_trades:
                price     = float(o.get("Price", 0))
                qty       = int(o.get("Qty", 0))
                brokerage = float(o.get("Brokerage", 0))
                est_pnl   = round((price * qty * 0.01) - brokerage, 2)
                trade_pnls.append({
                    "Stock":       o.get("Stock",""),
                    "Price":       f"₹{price:.2f}",
                    "Qty":         qty,
                    "Est. Return": f"₹{est_pnl:.2f}"
                })
            st.dataframe(pd.DataFrame(trade_pnls), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="info-box">No trade data yet. Start trading!</div>', unsafe_allow_html=True)

# ============================================================
# Options Page
# ============================================================

def options_page():
    back_button()
    top_bar()

    st.markdown('<div class="page-title">📈 Options Chain</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Simulated options data — not real market</div>', unsafe_allow_html=True)

    prices = st.session_state.market_prices
    stock  = st.session_state.selected_stock
    base   = prices.get(stock, STOCK_BASE_PRICES[stock])

    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:16px; 
                background:#111620; border:1px solid #1E2733;
                border-radius:10px; padding:14px 18px; margin-bottom:16px;">
        <div style="font-size:16px;font-weight:700;color:#E6EDF3;">{stock}</div>
        <div style="font-size:13px;color:#8B949E;">Spot Price</div>
        <div style="font-size:18px;font-weight:700;
                    font-family:'JetBrains Mono',monospace;color:#E6EDF3;">
            ₹{base:.2f}
        </div>
        <span class="tag tag-yellow">DUMMY DATA</span>
    </div>
    """, unsafe_allow_html=True)

    step    = max(50, round(base * 0.02 / 50) * 50)
    strikes = [round(base - (2*step) + (i*step), 0) for i in range(7)]
    strikes = [s for s in strikes if s > 0]
    seed    = int(base * 100) % 10000
    rng     = random.Random(seed)

    data = []
    for s in strikes:
        intrinsic_ce = max(0, base - s)
        intrinsic_pe = max(0, s - base)
        atm          = abs(s - base) < step
        data.append({
            "CE OI":   rng.randint(1000, 50000),
            "CE LTP":  round(intrinsic_ce + rng.uniform(10, 80), 2),
            "Strike":  f"₹{s:,.0f}" + (" ⭐" if atm else ""),
            "PE LTP":  round(intrinsic_pe + rng.uniform(10, 80), 2),
            "PE OI":   rng.randint(1000, 50000),
        })

    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    st.markdown(
        '<div style="font-size:11px;color:#484F58;margin-top:6px;">'
        '⚠️ Simulated options data for educational purposes only</div>',
        unsafe_allow_html=True
    )

# ============================================================
# News Page
# ============================================================

def news_page():
    back_button()
    top_bar()

    st.markdown('<div class="page-title">📰 Market News</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Simulated market headlines</div>', unsafe_allow_html=True)

    st.session_state.news = random.sample(FAKE_NEWS_POOL, min(10, len(FAKE_NEWS_POOL)))
    st.session_state.news_update_time = time.time()

    for n in st.session_state.news:
        st.markdown(f'<div class="news">🔔 {n}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div style="font-size:11px;color:#484F58;margin-top:12px;">'
        '⚠️ All news is simulated — not real market data</div>',
        unsafe_allow_html=True
    )

# ============================================================
# Predict Page
# ============================================================

def predict_page():
    back_button()
    top_bar()

    st.markdown('<div class="page-title">📉 AI Price Prediction</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Simulated analysis — not real financial advice</div>', unsafe_allow_html=True)

    stock      = st.session_state.selected_stock
    prices     = st.session_state.market_prices
    curr_price = prices.get(stock, STOCK_BASE_PRICES[stock])

    st.markdown(f"""
    <div style="background:#111620; border:1px solid #1E2733;
                border-radius:10px; padding:14px 18px; margin-bottom:16px;
                display:flex; align-items:center; gap:16px;">
        <div style="font-size:16px;font-weight:700;color:#E6EDF3;">{stock}</div>
        <div style="font-size:13px;color:#8B949E;">Current Price</div>
        <div style="font-size:18px;font-weight:700;
                    font-family:'JetBrains Mono',monospace;color:#E6EDF3;">
            ₹{curr_price:.2f}
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Analyzing market data..."):
        prediction = predict_next_move(stock)

    if prediction:
        col1, col2, col3, col4 = st.columns(4)
        trend_color = "#00D09C" if prediction['trend'] == "UP" else "#F85149"
        trend_arrow = "▲" if prediction['trend'] == "UP" else "▼"

        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Predicted Price</div>
                <div class="metric-value">₹{prediction['predicted_price']:.2f}</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Trend</div>
                <div class="metric-value" style="color:{trend_color};">
                    {trend_arrow} {prediction['trend']}
                </div>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Strength</div>
                <div class="metric-value">{prediction['strength']:.2f}%</div>
            </div>""", unsafe_allow_html=True)
        with col4:
            rsi_val = prediction.get('rsi')
            rsi_sig = prediction.get('rsi_signal','NEUTRAL')
            rsi_color = "#F85149" if rsi_sig == "OVERBOUGHT" else "#00D09C" if rsi_sig == "OVERSOLD" else "#8B949E"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">RSI · {rsi_sig}</div>
                <div class="metric-value" style="color:{rsi_color};">
                    {f"{rsi_val:.1f}" if rsi_val else "N/A"}
                </div>
            </div>""", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="card"><div class="metric-label">SMA 5</div><div style="font-family:JetBrains Mono,monospace;font-size:16px;color:#E6EDF3;margin-top:4px;">₹{prediction["sma_5"]:.2f}</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="card"><div class="metric-label">SMA 10</div><div style="font-family:JetBrains Mono,monospace;font-size:16px;color:#E6EDF3;margin-top:4px;">₹{prediction["sma_10"]:.2f}</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="card"><div class="metric-label">Support / Resistance</div><div style="font-family:JetBrains Mono,monospace;font-size:14px;color:#E6EDF3;margin-top:4px;">₹{prediction.get("support",0):.2f} / ₹{prediction.get("resistance",0):.2f}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="info-box">⏳ Collecting market data... Please wait and refresh.</div>', unsafe_allow_html=True)

    st.divider()

    # 5 Day Forecast Chart
    st.markdown('<div class="section-header">📅 5-Day Price Forecast</div>', unsafe_allow_html=True)
    days        = 5
    pred_prices = [curr_price]
    pred_dates  = [datetime.now()]
    trend_bias  = random.uniform(-0.3, 0.3)

    for i in range(1, days + 1):
        change    = np.random.normal(trend_bias, 1.2)
        new_price = pred_prices[-1] * (1 + change / 100)
        base_p    = STOCK_BASE_PRICES[stock]
        new_price = max(base_p*(1-CIRCUIT_LIMIT), min(base_p*(1+CIRCUIT_LIMIT), new_price))
        pred_prices.append(round(new_price, 2))
        pred_dates.append(datetime.now() + timedelta(days=i))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pred_dates, y=pred_prices,
        mode='lines+markers',
        name="AI Forecast",
        line=dict(color="#00D09C", width=2.5),
        marker=dict(size=6, color="#00D09C"),
        fill='tozeroy',
        fillcolor="#00D09C0D",
        hovertemplate="₹%{y:.2f}<extra></extra>"
    ))

    if prediction:
        support    = prediction.get("support", 0)
        resistance = prediction.get("resistance", 0)
        if support > 0:
            fig.add_hline(y=support,    line_dash="dash", line_color="#F85149", opacity=0.6,
                          annotation_text=f"Support ₹{support:.2f}",
                          annotation_font=dict(size=10, color="#F85149"))
        if resistance > 0:
            fig.add_hline(y=resistance, line_dash="dash", line_color="#00D09C", opacity=0.6,
                          annotation_text=f"Resistance ₹{resistance:.2f}",
                          annotation_font=dict(size=10, color="#00D09C"))

    fig.update_layout(
        template="plotly_dark",
        height=380,
        paper_bgcolor="#111620",
        plot_bgcolor="#111620",
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(gridcolor="#1E2733", tickfont=dict(size=10, color="#8B949E")),
        yaxis=dict(gridcolor="#1E2733", tickprefix="₹",
                   tickfont=dict(size=10, color="#8B949E")),
        hoverlabel=dict(bgcolor="#0D1117", bordercolor="#1E2733",
                        font=dict(size=12, color="#E6EDF3", family="JetBrains Mono"))
    )
    st.plotly_chart(fig, use_container_width=True)

    final_price  = pred_prices[-1]
    change_perc  = ((final_price / curr_price) - 1) * 100
    col1, col2   = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Day 5 Predicted Price</div>
            <div class="metric-value">₹{final_price:.2f}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        cp_color = "#00D09C" if change_perc >= 0 else "#F85149"
        cp_arrow = "▲" if change_perc >= 0 else "▼"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">AI Signal</div>
            <div class="metric-value" style="color:{cp_color};">
                {cp_arrow} {abs(change_perc):.2f}%
            </div>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # User Prediction Tool
    st.markdown('<div class="section-header">📐 Your Prediction</div>', unsafe_allow_html=True)
    pred_type      = st.selectbox("Prediction Type",
                                  ["Support Line","Resistance Line","Trend Line","Target Price"])
    pred_price_val = st.number_input("Price Level", min_value=0.01,
                                     value=float(round(curr_price,2)), step=0.5)
    pred_note      = st.text_input("Note (optional)", placeholder="Why is this level important?")

    if st.button("💾 Save Prediction →", type="primary"):
        login_id  = st.session_state.current_user.get("login_id","")
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

    login_id   = st.session_state.current_user.get("login_id","")
    user_preds = get_user_predictions(login_id, stock)

    if user_preds:
        st.markdown('<div class="section-header">📌 Your Saved Predictions</div>', unsafe_allow_html=True)
        pred_fig = go.Figure()
        pred_fig.add_trace(go.Scatter(
            x=pred_dates, y=pred_prices,
            mode='lines', name="AI Forecast",
            line=dict(color="#00D09C", width=2)
        ))

        pred_display = []
        for p in user_preds:
            d       = p.get("data", {})
            p_price = d.get("price", 0)
            p_type  = d.get("type", "")
            color   = "#F85149" if "Support" in p_type else "#F0B429"
            pred_fig.add_hline(
                y=p_price, line_dash="dot",
                line_color=color, opacity=0.7,
                annotation_text=f"{p_type}: ₹{p_price:.2f}",
                annotation_font=dict(size=10, color=color)
            )
            pred_display.append({
                "Type":  p_type,
                "Price": f"₹{p_price:.2f}",
                "Note":  d.get("note",""),
                "Time":  d.get("timestamp","")
            })

        pred_fig.update_layout(
            template="plotly_dark", height=320,
            paper_bgcolor="#111620", plot_bgcolor="#111620",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#1E2733"),
            yaxis=dict(gridcolor="#1E2733", tickprefix="₹")
        )
        st.plotly_chart(pred_fig, use_container_width=True)
        st.dataframe(pd.DataFrame(pred_display), use_container_width=True, hide_index=True)

    st.markdown(
        '<div style="font-size:11px;color:#484F58;margin-top:12px;">'
        '⚠️ Simulated AI — not real financial advice. Do not use for real trading.</div>',
        unsafe_allow_html=True
    )

# ============================================================
# Sidebar Navigation
# ============================================================

with st.sidebar:
    # Brand
    st.markdown("""
    <div style="padding: 8px 4px 16px;">
        <div class="sidebar-title">📈 TRADE with MB</div>
        <div class="sidebar-subtitle">Paper Trading Terminal</div>
    </div>
    """, unsafe_allow_html=True)

    # User Info
    st.markdown(f"""
    <div class="user-info-box">
        <div class="user-name">
            {st.session_state.current_user.get('full_name','User')}
            {'&nbsp;<span class="admin-badge">ADMIN</span>' if st.session_state.is_admin else ''}
        </div>
        <div class="user-id">
            ID: {st.session_state.current_user.get('login_id','')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Market Status
    st.markdown(
        '<div style="margin-bottom:16px;">'
        '<span class="market-status">MARKET OPEN 24/7</span>'
        '</div>',
        unsafe_allow_html=True
    )

    # Profile Button
    if st.button("👤 My Profile", use_container_width=True, key="nav_profile"):
        st.session_state.page = "Profile"
        st.rerun()

    st.markdown('<div class="nav-separator">Navigation</div>', unsafe_allow_html=True)

    if not st.session_state.is_admin:
        nav_items = [
            ("🏠  Dashboard",     "Dashboard"),
            ("📊  Analytics",     "Analytics"),
            ("📈  Options Chain", "Options"),
            ("💰  Funds",         "Funds"),
            ("📜  Trade History", "History"),
            ("📰  Market News",   "News"),
            ("📉  AI Prediction", "Predict"),
            ("🏆  Leaderboard",   "Leaderboard"),
        ]
        for label, page in nav_items:
            if st.button(label, use_container_width=True, key=f"nav_{page}"):
                st.session_state.page = page
                st.rerun()

    if st.session_state.is_admin:
        if st.button("👑  Admin Panel", use_container_width=True, key="nav_admin"):
            st.session_state.page = "Admin"
            st.rerun()

    st.markdown('<div class="nav-separator">Account</div>', unsafe_allow_html=True)

    if st.button("⚙️  Settings", use_container_width=True, key="nav_settings"):
        st.session_state.page = "Settings"
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Bottom disclaimer
    st.markdown(
        '<div class="disclaimer">'
        '📌 PAPER TRADING ONLY<br>'
        'No Real Money · Educational Only'
        '</div>',
        unsafe_allow_html=True
    )

# ============================================================
# Page Router
# ============================================================

pages = {
    "Dashboard":   dashboard_page,
    "Analytics":   analytics_page,
    "Options":     options_page,
    "Funds":       funds_page,
    "History":     history_page,
    "News":        news_page,
    "Predict":     predict_page,
    "Profile":     profile_page,
    "Admin":       admin_panel,
    "Settings":    settings_page,
    "Leaderboard": leaderboard_page
}

current_page = st.session_state.get("page", "Dashboard")
if current_page in pages:
    pages[current_page]()
else:
    st.session_state.page = "Dashboard"
    dashboard_page()
