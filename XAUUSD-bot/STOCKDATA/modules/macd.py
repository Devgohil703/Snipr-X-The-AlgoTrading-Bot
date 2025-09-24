"""
xauusd_macd_bot.py
MACD signal-line crossover sniper for XAUUSD on M5 timeframe.
- MACD(12,26,9) crossover based entries (both buy & sell)
- 1:1 R:R -> SL and TP set equal (points)
- Basic checks: spread, symbol availability, cooldown, duplicate open trades
- Logs to console and logs/trades csv

Requires:
pip install MetaTrader5 pandas numpy
Run: python xauusd_macd_bot.py
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime

# ---------------------------
# CONFIG (edit as needed)
# ---------------------------
CONFIG = {
    "symbol": "XAUUSD",
    "timeframe": mt5.TIMEFRAME_M5,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "lookback": 300,
    "lot": 0.01,
    "sl_points": 200,
    "tp_points": 200,
    "magic": 112233,
    "max_spread_points": 40,
    "min_equity": 50.0,
    "cooldown_seconds": 60 * 3,
    "trade_comment": "MACD-12-26-9-M5",
    "log_folder": "logs",
    "dry_run": False
}

os.makedirs(CONFIG["log_folder"], exist_ok=True)
TRADE_LOG_CSV = os.path.join(CONFIG["log_folder"], "macd_trades.csv")
RUNTIME_LOG = os.path.join(CONFIG["log_folder"], "macd_bot.log")

# ---------------------------
# Logging utils
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
# MT5 helpers
# ---------------------------
def mt5_connect():
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize() failed, code={mt5.last_error()}")
    log("MT5 initialized")

def mt5_shutdown():
    mt5.shutdown()
    log("MT5 shutdown")

def symbol_info_ok(symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        log(f"Symbol {symbol} not found")
        return False
    if not info.visible:
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
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        return False
    for p in positions:
        try:
            if int(p.magic) == magic:
                return True
        except Exception:
            if CONFIG["trade_comment"] in p.comment:
                return True
    return False

# ---------------------------
# Market data & MACD calc
# ---------------------------
def get_rates(symbol, timeframe, n):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
    if rates is None:
        raise RuntimeError(f"Failed to fetch rates for {symbol}: {mt5.last_error()}")
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def calc_macd(df_close, fast=12, slow=26, signal=9):
    """
    Return DataFrame with macd, signal, hist
    macd = EMA(fast) - EMA(slow)
    signal = EMA(macd, signal)
    hist = macd - signal
    """
    ema_fast = df_close.ewm(span=fast, adjust=False).mean()
    ema_slow = df_close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - signal_line
    return macd, signal_line, hist

# ---------------------------
# Order placement
# ---------------------------
def place_order(symbol, side, volume, sl_price, tp_price):
    deviation = 20
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {"retcode": -1, "comment": "no_tick"}

    price = tick.ask if side == "buy" else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(volume),
        "type": order_type,
        "price": float(price),
        "sl": float(sl_price),
        "tp": float(tp_price),
        "deviation": deviation,
        "magic": CONFIG["magic"],
        "comment": CONFIG["trade_comment"]
    }

    log(f"Placing order request: {request}")
    if CONFIG["dry_run"]:
        log("DRY RUN - order not sent")
        fake = {"retcode": 10009, "request": request, "comment": "dry_run"}
        return fake

    result = mt5.order_send(request)
    if result is None:
        log(f"order_send returned None: {mt5.last_error()}")
        return {"retcode": -1, "comment": "order_send_none"}
    log(f"order_send result: retcode={result.retcode}, comment={getattr(result, 'comment', '')}")
    return result._asdict() if hasattr(result, "_asdict") else result

def points_to_price(symbol, base_price, points):
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError("Symbol info missing")
    return base_price + points * info.point

# ---------------------------
# Signal detection (MACD crossover)
# ---------------------------
def check_macd_signal(df):
    """
    Use closed candles: df should exclude in-progress candle (use df.iloc[:-1])
    Detect MACD line crossing signal line on last closed candle:
    - prev macd < prev signal  AND last macd > last signal => BUY
    - prev macd > prev signal  AND last macd < last signal => SELL
    Additionally require histogram momentum confirmation (optional)
    """
    macd, sig, hist = calc_macd(df['close'], CONFIG['macd_fast'], CONFIG['macd_slow'], CONFIG['macd_signal'])
    df2 = df.copy()
    df2['macd'] = macd
    df2['signal'] = sig
    df2['hist'] = hist

    prev = df2.iloc[-2]
    last = df2.iloc[-1]

    # Crossover
    if prev['macd'] < prev['signal'] and last['macd'] > last['signal']:
        # optionally require last.hist > 0 to confirm bullish momentum
        if last['hist'] > 0:
            return "buy"
        else:
            # still allow but log weak hist
            return "buy"
    if prev['macd'] > prev['signal'] and last['macd'] < last['signal']:
        if last['hist'] < 0:
            return "sell"
        else:
            return "sell"
    return None

# ---------------------------
# Main loop
# ---------------------------
def main_loop():
    last_trade_time = None
    symbol = CONFIG['symbol']

    if not symbol_info_ok(symbol):
        log("Symbol not ok. Exiting.")
        return

    log("Starting MACD main loop...")
    while True:
        try:
            acc = get_account_health()
            if acc['equity'] < CONFIG['min_equity']:
                log(f"Equity low ({acc['equity']}). Waiting 60s.")
                time.sleep(60)
                continue

            df = get_rates(symbol, CONFIG['timeframe'], CONFIG['lookback'])
            if df.shape[0] < 50:
                log("Not enough bars. Sleeping 10s.")
                time.sleep(10)
                continue

            info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)
            if tick is None or info is None:
                log("Missing tick/info. Retry in 5s.")
                time.sleep(5)
                continue

            spread_points = abs(tick.ask - tick.bid) / info.point
            if spread_points > CONFIG['max_spread_points']:
                log(f"Spread too high: {spread_points} > {CONFIG['max_spread_points']}. Sleep 30s.")
                time.sleep(30)
                continue

            # Use closed candles only
            df_for_signal = df.iloc[:-1].copy()
            signal = check_macd_signal(df_for_signal)

            if signal is None:
                # debug print last macd values
                macd, sig, hist = calc_macd(df['close'], CONFIG['macd_fast'], CONFIG['macd_slow'], CONFIG['macd_signal'])
                log(f"No signal. last MACD={macd.iloc[-1]:.5f}, signal={sig.iloc[-1]:.5f}, hist={hist.iloc[-1]:.5f}. Sleep 20s.")
                time.sleep(20)
                continue

            # cooldown check
            now = datetime.now()
            if last_trade_time and (now - last_trade_time).total_seconds() < CONFIG['cooldown_seconds']:
                log("In cooldown after last trade. Skipping.")
                time.sleep(10)
                continue

            # duplicate open trade check
            if has_open_trade_for_magic(symbol, CONFIG['magic']):
                log("Existing open trade found for magic. Skipping entry.")
                time.sleep(10)
                continue

            # Prepare SL/TP
            tick = mt5.symbol_info_tick(symbol)
            price = tick.ask if signal == "buy" else tick.bid
            point = info.point

            if signal == "buy":
                sl_price = price - CONFIG['sl_points'] * point
                tp_price = price + CONFIG['tp_points'] * point
            else:
                sl_price = price + CONFIG['sl_points'] * point
                tp_price = price - CONFIG['tp_points'] * point

            log(f"Signal {signal.upper()} detected. Price={price:.5f}, SL={sl_price:.5f}, TP={tp_price:.5f}")
            result = place_order(symbol, signal, CONFIG['lot'], sl_price, tp_price)

            # Log trade attempt
            retcode = getattr(result, "retcode", result.get("retcode") if isinstance(result, dict) else "unknown")
            comment = getattr(result, "comment", result.get("comment") if isinstance(result, dict) else "")
            trade_row = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": symbol,
                "signal": signal,
                "price": price,
                "sl": sl_price,
                "tp": tp_price,
                "lot": CONFIG['lot'],
                "retcode": retcode,
                "comment": comment
            }
            append_trade_log(trade_row)

            if retcode in (10009, 10004, 0, 100):
                last_trade_time = datetime.now()
                log(f"Order success-ish. retcode={retcode}")
            else:
                log(f"Order may have failed. retcode={retcode}, comment={comment}")

            time.sleep(5)

        except KeyboardInterrupt:
            log("KeyboardInterrupt — exiting.")
            break
        except Exception as e:
            log(f"Exception in loop: {e}")
            time.sleep(5)

def debug_macd_print(symbol, timeframe, lookback=30):
    df = get_rates(symbol, timeframe, lookback)
    macd, sig, hist = calc_macd(df['close'], CONFIG['macd_fast'], CONFIG['macd_slow'], CONFIG['macd_signal'])
    df2 = df.copy()
    df2['macd'] = macd
    df2['signal'] = sig
    df2['hist'] = hist
    last = df2.iloc[-6:]
    log("Last 6 closed candles (time, close, macd, signal, hist):")
    for i, r in last.iterrows():
        log(f"{r['time']} | close={r['close']:.3f} macd={r['macd']:.5f} sig={r['signal']:.5f} hist={r['hist']:.5f}")

# ---------------------------
# ENTRY
# ---------------------------
if __name__ == "__main__":
    try:
        log("=== MACD 12-26-9 M5 Bot Starting ===")
        mt5_connect()
        debug_macd_print(CONFIG['symbol'], CONFIG['timeframe'], lookback=80)
        main_loop()
    except Exception as e:
        log(f"Fatal error: {e}")
    finally:
        try:
            mt5_shutdown()
        except Exception:
            pass
        log("Bot stopped.")
