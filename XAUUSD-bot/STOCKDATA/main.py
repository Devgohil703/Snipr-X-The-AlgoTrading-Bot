import MetaTrader5 as mt5
import pandas as pd
import time
import json

# ================= CONFIG =================
CONFIG = {
    "symbol": "XAUUSD",
    "timeframe": mt5.TIMEFRAME_M5,
    "lot": 0.1,
    "sl_points": 300,
    "tp_points": 300,
    "magic": 123456,
    "deviation": 20
}

# ================= MT5 CONNECT =================
def connect_mt5():
    if not mt5.initialize():
        raise RuntimeError("❌ MT5 initialize failed")
    print("✅ MT5 Connected")

def disconnect_mt5():
    mt5.shutdown()
    print("🔌 MT5 Disconnected")

# ================= DATA FETCH =================
def get_data(symbol, timeframe, n=200):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df

# ================= INDICATORS =================
def ema_strategy(df):
    df["ema9"] = df["close"].ewm(span=9, adjust=False).mean()
    df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # bullish crossover
    if prev["ema9"] < prev["ema21"] and last["ema9"] > last["ema21"]:
        return "buy"
    # bearish crossover
    elif prev["ema9"] > prev["ema21"] and last["ema9"] < last["ema21"]:
        return "sell"
    return None

def macd_strategy(df):
    df["ema12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = df["ema12"] - df["ema26"]
    df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # bullish MACD crossover
    if prev["macd"] < prev["signal"] and last["macd"] > last["signal"]:
        return "buy"
    # bearish MACD crossover
    elif prev["macd"] > prev["signal"] and last["macd"] < last["signal"]:
        return "sell"
    return None

# ================= ORDER SENDER =================
def send_order(order_type):
    symbol = CONFIG["symbol"]
    lot = CONFIG["lot"]

    tick = mt5.symbol_info_tick(symbol)
    if order_type == "buy":
        price = tick.ask
        sl = price - CONFIG["sl_points"] * mt5.symbol_info(symbol).point
        tp = price + CONFIG["tp_points"] * mt5.symbol_info(symbol).point
        order_type_mt5 = mt5.ORDER_TYPE_BUY
    else:
        price = tick.bid
        sl = price + CONFIG["sl_points"] * mt5.symbol_info(symbol).point
        tp = price - CONFIG["tp_points"] * mt5.symbol_info(symbol).point
        order_type_mt5 = mt5.ORDER_TYPE_SELL

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type_mt5,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": CONFIG["deviation"],
        "magic": CONFIG["magic"],
        "comment": "EMA+MACD bot"
    }

    result = mt5.order_send(request)
    print(f"📌 Order Result: {result}")
    return result

# ================= STRATEGY RUNNER =================
def run_strategy():
    df = get_data(CONFIG["symbol"], CONFIG["timeframe"], 300)

    ema_signal = ema_strategy(df)
    macd_signal = macd_strategy(df)

    print(f"EMA: {ema_signal}, MACD: {macd_signal}")

    if ema_signal == macd_signal and ema_signal is not None:
        print(f"🚀 Taking {ema_signal.upper()} trade (confluence)")
        send_order(ema_signal)
    else:
        print("⏸ No confluence, no trade.")

# ================= MAIN =================
if __name__ == "__main__":
    connect_mt5()
    try:
        while True:
            run_strategy()
            time.sleep(60)  # run every 1 minute
    except KeyboardInterrupt:
        print("🛑 Bot stopped manually")
    finally:
        disconnect_mt5()
