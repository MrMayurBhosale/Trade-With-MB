# market.py
# Market Data Generator - Generates fake OHLC candles 24/7
# Continuous candles - previous close = next open
# Natural movement - no random jumps

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
# Generate new candle data for all 25 stocks
# ============================================================

def generate_candles():
    """
    Generate OHLC candle for each stock.
    Previous close = Next open (continuous chart)
    Small natural movements - no random jumps
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

            # Previous close = current open (continuity)
            last_candles = get_candles(stock, limit=1)
            if last_candles:
                open_price = float(last_candles[-1]["close"])
            else:
                open_price = float(prices.get(stock, base_price))

            # Ensure valid price
            if open_price <= 0:
                open_price = base_price

            # Small natural movement (volatility * 0.3)
            change_percent = np.random.normal(0, volatility * 0.3)
            close_price = open_price * (1 + change_percent / 100)

            # Circuit limit check
            upper_circuit = base_price * (1 + CIRCUIT_LIMIT)
            lower_circuit = base_price * (1 - CIRCUIT_LIMIT)
            close_price = max(lower_circuit, min(upper_circuit, close_price))
            close_price = max(close_price, base_price * 0.01)

            # High/Low - small range around open-close
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.001))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.001))

            # Round all
            open_price = round(open_price, 2)
            high_price = round(high_price, 2)
            low_price = round(low_price, 2)
            close_price = round(close_price, 2)

            # OHLC validity
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)

            updated_prices[stock] = close_price

            candle_list.append({
                "stock": stock,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "timestamp": timestamp,
                "created_at": now
            })

        # Bulk save
        save_candles_bulk(candle_list)
        update_global_market_prices(updated_prices)

        return updated_prices

    except Exception as e:
        print(f"Generate candles error: {e}")
        return get_global_market_prices()


# ============================================================
# DB Prediction Engine - SMA + RSI + Trend
# ============================================================

def predict_next_move(stock):
    """
    Predict next price movement.
    Uses SMA-5, SMA-10, RSI, and trend analysis.
    """
    try:
        candles = get_candles(stock, limit=50)

        if not candles or len(candles) < 5:
            return None

        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]

        # SMA
        sma_5 = round(float(np.mean(closes[-5:])), 2)
        sma_10 = round(float(np.mean(closes[-10:])) if len(closes) >= 10 else sma_5, 2)

        # Trend
        recent_avg = np.mean(closes[-10:]) if len(closes) >= 10 else np.mean(closes)
        older_avg = np.mean(closes[-20:-10]) if len(closes) >= 20 else np.mean(closes[:max(1, len(closes) // 2)])

        if older_avg == 0:
            older_avg = closes[0] if closes[0] != 0 else 1.0

        trend = "UP" if recent_avg > older_avg else "DOWN"
        strength = round(abs(recent_avg - older_avg) / older_avg * 100, 2)

        # RSI
        rsi = _calculate_rsi(closes)

        # Predicted price
        if sma_10 != 0:
            predicted_price = closes[-1] * (1 + (sma_5 - sma_10) / sma_10)
        else:
            predicted_price = closes[-1]

        # Circuit limit on prediction
        base_price = STOCKS[stock]["price"]
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

        # Support / Resistance
        support = round(min(lows[-10:]) if len(lows) >= 10 else min(lows), 2)
        resistance = round(max(highs[-10:]) if len(highs) >= 10 else max(highs), 2)

        prediction = {
            "stock": stock,
            "current_price": closes[-1],
            "predicted_price": predicted_price,
            "trend": trend,
            "strength": strength,
            "sma_5": sma_5,
            "sma_10": sma_10,
            "rsi": round(rsi, 2) if rsi is not None else None,
            "rsi_signal": rsi_signal,
            "support": support,
            "resistance": resistance,
            "candles_used": len(candles)
        }

        save_prediction(stock, prediction)
        return prediction

    except Exception as e:
        print(f"Predict next move error: {e}")
        return None


# ============================================================
# RSI Calculator
# ============================================================

def _calculate_rsi(closes, period=14):
    """Calculate RSI (0-100)"""
    try:
        if len(closes) < period + 1:
            return None

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [abs(d) if d < 0 else 0 for d in deltas]

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        if avg_loss == 0:
            return 100.0

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    except Exception as e:
        print(f"RSI calculation error: {e}")
        return None


# ============================================================
# Portfolio Value Calculator
# ============================================================

def calculate_portfolio_value(portfolio, prices):
    """Portfolio Value = Sum(Qty x Current Price)"""
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
