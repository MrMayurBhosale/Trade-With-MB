# 📈 TRADE with MB - Paper Trading Platform

> ⚠️ PAPER TRADING ONLY - No Real Money Involved  
> For Educational Purpose Only

---

## 📌 What is This?

TRADE with MB is a Paper Trading Platform that  
simulates the Indian Stock Market.  
No real money is involved - just for practice.

The platform runs a 24/7 live market simulation  
where you can trade 25 Indian stocks.

---

## ✨ Features

### 📊 Trading
- 25 Indian Stocks (RELIANCE, TCS, HDFCBANK, etc.)
- Market Order, Limit Order, Stop Loss Order
- Real-time Portfolio Tracking
- Brokerage Deduction (0.1%)
- Circuit Limit Protection (±10%)
- Holding P&L Tracking
- Day P&L (Resets at Midnight IST)

### 📈 Charts & Analysis
- Live Candlestick Charts (Plotly)
- AI Price Prediction (SMA + RSI)
- Support & Resistance Levels
- 5-Day Price Forecast
- Options Chain (Simulation)

### 👤 User Features
- Auto Login ID Generation (4 characters)
- Auto Password Generation (6 characters)
- Forgot Password via Favourite Number
- User Profile with Bio
- Trade History with CSV Export
- Account Reset Option
- Leaderboard (Ranked by Net Worth)

### 👑 Admin Features
- All Users Dashboard
- View Platform as Any User
- Soft Delete User Account
- Full Audit Logs
- Export Users Data as CSV

### 🔒 Security
- bcrypt Password Hashing
- Session Timeout (10 min inactivity)
- Rate Limiting (Locks after 5 failed attempts)
- CSRF Token Protection
- Input Sanitization on all fields
- Soft Delete (Data preserved in DB)

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| Python 3.10+ | Core Language |
| Streamlit | Frontend UI |
| MongoDB | Primary Database |
| Plotly | Charts & Graphs |
| bcrypt | Password Hashing |
| NumPy | Market Calculations |
| Pandas | Data Display |
| python-dotenv | Environment Config |

---

## 📁 Project Structure
trade-with-mb/
│
├── app.py # Main Streamlit app + All UI pages
├── config.py # Constants + Settings loaded from .env
├── db.py # MongoDB operations + Backup + CSV Export
├── market.py # Market simulator + AI prediction engine
├── requirements.txt # Python dependencies
└── README.md # Project documentation


---

## ⚙️ Setup & Installation

### Step 1 - Clone Repository

git clone https://github.com/MRMAYURBHOSALE/Trade-With-Mb.git
cd Trade-With-Mb

### Step 2 - Create Virtual Environment
python -m venv env

Windows
env\Scripts\activate

Mac/Linux
source env/bin/activate




### Step 3 - Install Dependencies
pip install -r requirements.txt




### Step 4 - Setup Environment Variables
Create a .env file in the root folder and add:
MONGO_URI=mongodb://localhost:27017/
DB_NAME=trade_with_mb
ADMIN_PASSWORD=your_strong_password
SESSION_TIMEOUT=600
RATE_LIMIT_ATTEMPTS=5
RATE_LIMIT_LOCK=600
INIT_BALANCE=100000
BROKERAGE_RATE=0.001
MAX_ADD_FUNDS=50000
MAX_ORDER_BOOK=500
CANDLE_TTL_DAYS=7
AUDIT_LOG_TTL_DAYS=30
MAX_USER_PREDICTIONS=10
BACKUP_INTERVAL=300
BACKUP_FILE=backup_data.json
EXPORTS_FOLDER=exports




### Step 5 - Start MongoDB
Windows
net start MongoDB

Mac/Linux
mongod




### Step 6 - Run the App
streamlit run app.py




---

## 🎮 How to Use

### New User
Go to Register tab
Enter Name + Favourite Number
Save your Login ID and Password
You will be logged in automatically
Start trading on the Dashboard
text


### Trading
Select a stock from the Watchlist
Choose Order Type (Market / Limit / Stop Loss)
Enter Quantity
Click BUY or SELL
text


### Admin Login
Login ID : ADMIN
Password : 




---

## 📊 25 Stocks Available
RELIANCE TCS HDFCBANK INFY
TATAMOTORS ICICIBANK SBIN BHARTIARTL
ITC KOTAKBANK LT HINDUNILVR
AXISBANK BAJFINANCE MARUTI SUNPHARMA
TITAN ULTRACEMCO WIPRO ADANIENT
TATASTEEL POWERGRID NTPC COALINDIA
ONGC




---

## ⚠️ Important Disclaimers
✅ This platform is for educational purposes only
✅ No real money is involved at any point
✅ All stock prices are fake and simulated
✅ All news shown is completely fake
✅ AI prediction is a dummy simulation
✅ No connection to any real stock exchange
✅ Not financial advice of any kind




---

## 🔒 Security Overview
✅ All passwords hashed with bcrypt
✅ All sensitive data stored in .env file
✅ Session expires after 10 min inactivity
✅ Account locks after 5 failed login attempts
✅ CSRF protection enabled
✅ Input sanitization on all user inputs
✅ Soft delete keeps data safe in database
✅ Full audit logs for all user actions




## 📜 License

This project is for personal and educational 
use only. Not for commercial use.

---

*Built for learning purposes only* 📚
