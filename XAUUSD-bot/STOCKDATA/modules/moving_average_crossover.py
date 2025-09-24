"""
xauusd_ema_bot.py
Simple EMA crossover sniper for XAUUSD on M5 timeframe.
- 9 EMA and 21 EMA crossover based entries (both buy & sell)
- 1:1 R:R -> SL and TP distance equal (in points)
- Basic checks: spread, symbol availability, cooldown, duplicate open trades
- Logs to console and logs/trades csv

Requires:
pip install MetaTrader5 pandas numpy
Run: python xauusd_ema_bot.py
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
import json
import os
from datetime import datetime, timedelta

# ---------------------------
# CONFIG (edit as needed)
# ---------------------------
CONFIG = {
    "symbol": "XAUUSD",             # instrument
    "timeframe": mt5.TIMEFRAME_M5,  # M5
    "ema_fast": 9,
    "ema_slow": 21,
    "lookback": 200,                # number of bars to fetch
    "lot": 0.01,
    "sl_points": 200,               # SL in points (for XAUUSD point usually 0.01 or 0.1 depending on broker)
    "tp_points": 200,               # TP = SL for 1:1 R:R
    "magic": 987654,
    "max_spread_points": 40,        # max allowed spread in points (tweak per broker)
    "min_equity": 50.0,             # minimum equity in account currency to allow trades
    "cooldown_seconds": 60 * 3,     # 3 minutes cooldown after placing trade
    "trade_comment": "EMA9-21-M5",
    "log_folder": "logs",
    "dry_run": False                # if True, won't send real orders (for testing)
}

# Ensure log folder
os.makedirs(CONFIG["log_folder"], exist_ok=True)
TRADE_LOG_CSV = os.path.join(CONFIG["log_folder"], "trades.csv")
RUNTIME_LOG = os.path.join(CONFIG["log_folder"], "bot.log")

# ---------------------------
# Utilities: logging
# ---------------------------
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(RUNTIME_LOG, "a") as f:
        f.write(line + "\n")

def append_trade_log(row: dict):
    df = pd.DataFrame([row])
    header = not os.path.exists(TRADE_LOG_CSV)
    df.to_csv(TRADE_LOG_CSV, mode="a", index=False, header=header)

# ---------------------------
# MT5 Connection helpers
# ---------------------------
def mt5_connect():
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize() failed, code={mt5.last_error()}")
    log("MT5 initialized")

def mt5_shutdown():
    mt5.shutdown()
    log("MT5 shutdown")

# ---------------------------
# Market data helpers
# ---------------------------
def get_rates(symbol, timeframe, n):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
    if rates is None:
        raise RuntimeError(f"Failed to get rates for {symbol}: {mt5.last_error()}")
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def calc_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

# ---------------------------
# Trading helpers
# ---------------------------
def symbol_info_ok(symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        log(f"Symbol {symbol} not found on server")
        return False
    if not info.visible:
        # try to enable
        mt5.symbol_select(symbol, True)
        info = mt5.symbol_info(symbol)
        if info is None or not info.visible:
            log(f"Symbol {symbol} not visible and cannot be selected")
            return False
    return True

def get_account_health():
    info = mt5.account_info()
    if info is None:
        raise RuntimeError("Failed to get account info")
    return {"balance": info.balance, "equity": info.equity, "leverage": info.leverage}

def has_open_trade_for_magic(symbol, magic):
    orders = mt5.positions_get(symbol=symbol)
    if orders is None:
        return False
    for o in orders:
        # Some brokers don't expose magic; compare comment or ticket if necessary.
        try:
            if int(o.magic) == magic:
                return True
        except Exception:
            # fallback to comment match
            if CONFIG["trade_comment"] in o.comment:
                return True
    return False

def place_order(symbol, order_type, volume, sl_price, tp_price):
    # order_type: "buy" or "sell"
    deviation = 20
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {"retcode": -1, "comment": "no_tick"}

    price = tick.ask if order_type == "buy" else tick.bid
    if order_type == "buy":
        _type = mt5.ORDER_TYPE_BUY
    else:
        _type = mt5.ORDER_TYPE_SELL

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(volume),
        "type": _type,
        "price": float(price),
        "sl": float(sl_price),
        "tp": float(tp_price),
        "deviation": deviation,
        "magic": CONFIG["magic"],
        "comment": CONFIG["trade_comment"]
    }

    log(f"Order request: {request}")
    if CONFIG["dry_run"]:
        # Simulate success
        fake = {"retcode": 10009, "request": request, "deal": 0, "comment": "dry_run"}
        log("DRY RUN - order not sent")
        return fake

    result = mt5.order_send(request)
    if result is None:
        log(f"Order send returned None: {mt5.last_error()}")
        return {"retcode": -1, "comment": "order_send_none"}
    log(f"Order send result: retcode={result.retcode}, comment={getattr(result, 'comment', '')}")
    return result._asdict() if hasattr(result, "_asdict") else result

# ---------------------------
# Signal logic: EMA crossover
# ---------------------------
def check_for_signal(df):
    """
    df expected to have 'close' column and be in chronological order
    We compute EMA9 and EMA21 and look for crossover on the last completed candle.
    Returns: "buy", "sell", or None
    """
    df = df.copy()
    df['ema9'] = calc_ema(df['close'], CONFIG['ema_fast'])
    df['ema21'] = calc_ema(df['close'], CONFIG['ema_slow'])

    # we use last two rows to detect recent crossover
    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Condition: prev ema9 < prev ema21 and last ema9 > last ema21 => buy
    if prev['ema9'] < prev['ema21'] and last['ema9'] > last['ema21']:
        return "buy"
    # Opposite for sell
    if prev['ema9'] > prev['ema21'] and last['ema9'] < last['ema21']:
        return "sell"
    return None

# ---------------------------
# Price helpers for SL/TP calculation
# ---------------------------
def points_to_price(symbol, price, points):
    """Convert points to price value depending on symbol point size"""
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError("Symbol info not available for point conversion")
    point = info.point
    return price + points * point

# ---------------------------
# Main loop
# ---------------------------
def main_loop():
    last_trade_time = None

    symbol = CONFIG["symbol"]
    if not symbol_info_ok(symbol):
        log("Symbol check failed, exiting")
        return

    log("Starting main loop. Fetching historical data and waiting for signals...")
    while True:
        try:
            # Basic account health check
            acc = get_account_health()
            if acc['equity'] < CONFIG['min_equity']:
                log(f"Equity too low ({acc['equity']}). Sleeping 60s.")
                time.sleep(60)
                continue

            # Fetch data
            df = get_rates(symbol, CONFIG['timeframe'], CONFIG['lookback'])
            if df.shape[0] < CONFIG['lookback']:
                log("Not enough bars fetched, sleeping 10s.")
                time.sleep(10)
                continue

            # Spread check
            info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)
            if tick is None or info is None:
                log("Tick or symbol info missing, retrying.")
                time.sleep(5)
                continue
            spread_points = abs(tick.ask - tick.bid) / info.point
            if spread_points > CONFIG['max_spread_points']:
                log(f"Spread too high: {spread_points} points (max {CONFIG['max_spread_points']}). Sleeping 30s.")
                time.sleep(30)
                continue

            # Check for signal on last completed candle (exclude in-progress candle)
            # We will use df up to second-last bar to ensure candle closed
            df_for_signal = df.iloc[:-1].copy()  # last closed candle is at -2 index; slicing ensures we use closed candles
            signal = check_for_signal(df_for_signal)

            if signal is None:
                # no entry
                # optionally print EMAs for debugging
                e9 = calc_ema(df['close'], CONFIG['ema_fast']).iloc[-1]
                e21 = calc_ema(df['close'], CONFIG['ema_slow']).iloc[-1]
                log(f"No signal. EMA9={e9:.3f}, EMA21={e21:.3f}. Sleeping 20s.")
                time.sleep(20)
                continue

            # Cooldown and duplicate checks
            now = datetime.now()
            if last_trade_time:
                if (now - last_trade_time).total_seconds() < CONFIG['cooldown_seconds']:
                    log("Recently traded. Still in cooldown. Skipping this signal.")
                    time.sleep(10)
                    continue

            if has_open_trade_for_magic(symbol, CONFIG['magic']):
                log("Existing open trade for this bot/magic exists. Skipping new entry.")
                time.sleep(10)
                continue

            # Prepare order params
            # Use current tick to compute SL/TP from price
            tick = mt5.symbol_info_tick(symbol)
            price = tick.ask if signal == "buy" else tick.bid
            info = mt5.symbol_info(symbol)
            point = info.point

            # Calculate SL and TP price (1:1)
            if signal == "buy":
                sl_price = price - CONFIG['sl_points'] * point
                tp_price = price + CONFIG['tp_points'] * point
            else:
                sl_price = price + CONFIG['sl_points'] * point
                tp_price = price - CONFIG['tp_points'] * point

            # Additional check: SL/TP reasonable (not beyond limits)
            # Use symbol_info to check min/max deviation; many brokers have limits but skipping complex checks here.

            # Place order
            log(f"Signal: {signal.upper()} - placing order at price {price:.5f} SL={sl_price:.5f} TP={tp_price:.5f}")
            result = place_order(symbol, signal, CONFIG['lot'], sl_price, tp_price)

            # Record trade attempt
            trade_row = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": symbol,
                "signal": signal,
                "price": price,
                "sl": sl_price,
                "tp": tp_price,
                "lot": CONFIG['lot'],
                "retcode": getattr(result, "retcode", result.get("retcode") if isinstance(result, dict) else "unknown"),
                "comment": getattr(result, "comment", result.get("comment") if isinstance(result, dict) else ""),
            }
            append_trade_log(trade_row)

            # If order placed (retcode 10009 or similar success codes vary by broker), set last_trade_time
            rc = trade_row["retcode"]
            if rc in (10009, 10004, 0, 100):  # include commonly used success-ish codes; depends on broker/API
                last_trade_time = datetime.now()
                log(f"Order presumed placed successfully. retcode={rc}")
            else:
                log(f"Order may have failed or partial. retcode={rc}, comment={trade_row['comment']}")

            # wait a bit before next loop
            time.sleep(5)

        except KeyboardInterrupt:
            log("KeyboardInterrupt received. Exiting loop.")
            break
        except Exception as e:
            log(f"Exception in main loop: {e}")
            time.sleep(5)

# ---------------------------
# Quick sanity function: test indicators on recent bars
# ---------------------------
def debug_print_emas(symbol, timeframe, lookback=50):
    df = get_rates(symbol, timeframe, lookback)
    df['ema9'] = calc_ema(df['close'], CONFIG['ema_fast'])
    df['ema21'] = calc_ema(df['close'], CONFIG['ema_slow'])
    last = df.iloc[-5:]
    log("Last 5 closed candles (time, close, ema9, ema21):")
    for i, r in last.iterrows():
        log(f"{r['time']} | close={r['close']:.3f} ema9={r['ema9']:.3f} ema21={r['ema21']:.3f}")

# ---------------------------
# ENTRY POINT
# ---------------------------
if __name__ == "__main__":
    try:
        log("=== EMA9-21 M5 Bot Starting ===")
        mt5_connect()
        debug_print_emas(CONFIG["symbol"], CONFIG["timeframe"], lookback=60)
        main_loop()
    except Exception as e:
        log(f"Fatal error: {e}")
    finally:
        try:
            mt5_shutdown()
        except Exception:
            pass
        log("Bot stopped.")
