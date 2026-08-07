# market.py
# Market Data Generator - Generates fake OHLC candles 24/7
# All 25 stocks get candle data saved to MongoDB candles collection
# Market runs 24/7 - No market hours restriction

import random
import numpy as np
from datetime import datetime
from config import (
    STOCKS,
    STOCK_BASE_PRICES,
    STOCK_VOLATILITY,
    CIRCUIT_LIMIT
)
from db import (
    get_global_market_prices,
    update_global_market_prices,
    save_candles_bulk,
    get_candles,
    save_prediction
)

# ============================================================
# Generate new candle data for all 25 stocks - Bulk write
# ============================================================

def generate_candles():
    """
    Generate OHLC candle for each stock and save to MongoDB.
    Uses bulk write for performance.
    Per-stock volatility from config.
    Circuit limit applied per stock.
    Returns updated prices dict.
    """
    try:
        prices = get_global_market_prices()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        now = datetime.now()

        candle_list = []
        updated_prices = {}

        for stock, stock_data in STOCKS.items():
            base_price = stock_data["price"]
            volatility = stock_data["volatility"]

            current_price = prices.get(stock, base_price)

            # Ensure current price is valid - never zero or negative
            if current_price <= 0:
                current_price = base_price

            # Per-stock volatility based random price movement
            change_percent = np.random.normal(0, volatility)

            # Calculate new close price
            close_price = current_price * (1 + change_percent / 100)

            # Circuit limit check - ±10% from base price
            upper_circuit = base_price * (1 + CIRCUIT_LIMIT)
            lower_circuit = base_price * (1 - CIRCUIT_LIMIT)

            # Clamp price within circuit limits
            close_price = max(lower_circuit, min(upper_circuit, close_price))

            # Ensure price never goes to zero or negative
            close_price = max(close_price, base_price * 0.01)

            # Generate OHLC - High must be >= Open,Close; Low must be <= Open,Close
            open_price = current_price
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.002))
            low_price  = min(open_price, close_price) * (1 - random.uniform(0, 0.002))

            # Round all prices to 2 decimal places
            open_price  = round(open_price, 2)
            high_price  = round(high_price, 2)
            low_price   = round(low_price, 2)
            close_price = round(close_price, 2)

            # Ensure OHLC validity
            high_price = max(high_price, open_price, close_price)
            low_price  = min(low_price, open_price, close_price)

            # Update price for this stock
            updated_prices[stock] = close_price

            # Build candle document
            candle_list.append({
                "stock":      stock,
                "open":       open_price,
                "high":       high_price,
                "low":        low_price,
                "close":      close_price,
                "timestamp":  timestamp,
                "created_at": now
            })

        # Bulk save all candles at once - much faster than 25 separate inserts
        save_candles_bulk(candle_list)

        # Update global market prices in database
        update_global_market_prices(updated_prices)

        return updated_prices

    except Exception as e:
        print(f"Generate candles error: {e}")
        # Return last known prices on error
        return get_global_market_prices()

# ============================================================
# DB Prediction Engine - SMA + RSI + Trend
# ============================================================

def predict_next_move(stock):
    """
    Predict next price movement based on historical candle data.
    Uses SMA-5, SMA-10, RSI, and trend analysis.
    Saves prediction to MongoDB predictions collection.
    Returns prediction dict or None if not enough data.
    """
    try:
        candles = get_candles(stock, limit=50)

        if not candles or len(candles) < 5:
            return None

        closes = [c["close"] for c in candles]
        highs  = [c["high"]  for c in candles]
        lows   = [c["low"]   for c in candles]

        # SMA calculations
        sma_5  = round(float(np.mean(closes[-5:])), 2)
        sma_10 = round(float(np.mean(closes[-10:])) if len(closes) >= 10 else sma_5, 2)

        # Trend detection
        recent_avg = np.mean(closes[-10:]) if len(closes) >= 10 else np.mean(closes)
        older_avg  = np.mean(closes[-20:-10]) if len(closes) >= 20 else np.mean(closes[:max(1, len(closes)//2)])

        # Safe division for older_avg
        if older_avg == 0:
            older_avg = closes[0] if closes[0] != 0 else 1.0

        trend    = "UP" if recent_avg > older_avg else "DOWN"
        strength = round(abs(recent_avg - older_avg) / older_avg * 100, 2)

        # RSI calculation (14 period)
        rsi = _calculate_rsi(closes)

        # Predicted price using SMA crossover
        if sma_10 != 0:
            predicted_price = closes[-1] * (1 + (sma_5 - sma_10) / sma_10)
        else:
            predicted_price = closes[-1]

        # Apply circuit limit to prediction
        base_price    = STOCKS[stock]["price"]
        upper_circuit = base_price * (1 + CIRCUIT_LIMIT)
        lower_circuit = base_price * (1 - CIRCUIT_LIMIT)
        predicted_price = max(lower_circuit, min(upper_circuit, predicted_price))
        predicted_price = round(predicted_price, 2)

        # RSI signal
        if rsi is not None:
            if rsi > 70:
                rsi_signal = "OVERBOUGHT"
            elif rsi < 30:
                rsi_signal = "OVERSOLD"
            else:
                rsi_signal = "NEUTRAL"
        else:
            rsi_signal = "NEUTRAL"

        # Support and resistance levels
        support    = round(min(lows[-10:])  if len(lows)  >= 10 else min(lows), 2)
        resistance = round(max(highs[-10:]) if len(highs) >= 10 else max(highs), 2)

        prediction = {
            "stock":           stock,
            "current_price":   closes[-1],
            "predicted_price": predicted_price,
            "trend":           trend,
            "strength":        strength,
            "sma_5":           sma_5,
            "sma_10":          sma_10,
            "rsi":             round(rsi, 2) if rsi is not None else None,
            "rsi_signal":      rsi_signal,
            "support":         support,
            "resistance":      resistance,
            "candles_used":    len(candles)
        }

        # Save prediction to MongoDB (upsert per stock)
        save_prediction(stock, prediction)

        return prediction

    except Exception as e:
        print(f"Predict next move error: {e}")
        return None

# ============================================================
# RSI Calculator
# ============================================================

def _calculate_rsi(closes, period=14):
    """
    Calculate RSI (Relative Strength Index) for given close prices.
    Returns RSI value (0-100) or None if not enough data.
    """
    try:
        if len(closes) < period + 1:
            return None

        # Calculate price changes
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]

        # Separate gains and losses
        gains  = [d if d > 0 else 0 for d in deltas]
        losses = [abs(d) if d < 0 else 0 for d in deltas]

        # Initial average gain/loss
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        if avg_loss == 0:
            return 100.0

        # Smoothed RSI
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs  = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    except Exception as e:
        print(f"RSI calculation error: {e}")
        return None

# ============================================================
# Portfolio Value Calculator - Helper
# ============================================================

def calculate_portfolio_value(portfolio, prices):
    """
    Calculate total portfolio value.
    Portfolio Value = Sum of (Qty × Current Price) for all stocks.
    """
    try:
        total = 0.0
        for stock, holding in portfolio.items():
            qty = holding.get("qty", 0) if isinstance(holding, dict) else holding
            price = prices.get(stock, STOCK_BASE_PRICES.get(stock, 0))
            total += qty * price
        return round(total, 2)
    except Exception as e:
        print(f"Portfolio value error: {e}")
        return 0.0