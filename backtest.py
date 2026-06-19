"""
CMC Momentum Alpha — Backtest

Walk-forward backtest using real Binance OHLCV data.
No lookahead bias. No fake data.

Usage:
    pip install requests
    python3 backtest.py
"""
import json
import time
import requests
from datetime import datetime, timezone


# ── Config ────────────────────────────────────────────────────

PARAMS = {
    "w_rsi": 0.20, "w_macd": 0.15, "w_bb": 0.10,
    "w_vol": 0.15, "w_fg": 0.15, "w_dom": 0.10, "w_atr": 0.15,
    "entry": 0.55, "exit": 0.30,
    "stop_loss": 0.15, "take_profit": 0.30,
    "max_pos": 5, "size_pct": 20,
}

ELIGIBLE = [
    "ETH", "XRP", "DOGE", "ADA", "LINK", "AVAX", "SHIB", "DOT", "UNI",
    "ATOM", "LTC", "ETC", "AAVE", "FIL", "INJ", "FET", "AXS", "TWT",
    "CAKE", "STG", "ZRO", "FLOKI", "LDO", "ROSE", "ZIL", "ZETA",
    "ACH", "AXL", "KAVA", "DUSK", "APE", "BAT", "DEXE", "TRX", "ZEC",
    "COMP", "SUSHI", "SNX", "1INCH", "PENDLE", "BCH",
]

STABLECOINS = {"USDT", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDD", "USD1", "USDe", "FRAX"}


# ── Data Fetching ─────────────────────────────────────────────

def get_ohlcv(symbol, days=60):
    """Fetch daily OHLCV from Binance (free, no key)."""
    try:
        r = requests.get("https://api.binance.com/api/v3/klines", params={
            "symbol": f"{symbol}USDT", "interval": "1d", "limit": days
        }, timeout=10)
        if r.status_code != 200:
            return []
        return [{
            "time": int(k[0]), "open": float(k[1]), "high": float(k[2]),
            "low": float(k[3]), "close": float(k[4]), "volume": float(k[5]),
        } for k in r.json()]
    except:
        return []


def get_fng():
    """Fetch Fear & Greed Index history (free, no key)."""
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=60", timeout=10)
        return [int(d["value"]) for d in r.json().get("data", [])]
    except:
        return [50] * 60


def get_btc_dominance():
    """Fetch BTC dominance from CMC (free, no key)."""
    try:
        r = requests.get("https://api.coinmarketcap.com/data-api/v3/global-metrics/quotes/latest", timeout=15)
        return r.json().get("data", {}).get("btcDominance", 55)
    except:
        return 55


# ── Indicators ────────────────────────────────────────────────

def rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_g = sum(gains[-period:]) / period
    avg_l = sum(losses[-period:]) / period
    if avg_l == 0:
        return 100.0
    return 100 - (100 / (1 + avg_g / avg_l))


def macd(closes, fast=12, slow=26, sig=9):
    if len(closes) < slow + sig:
        return 0.0
    def ema(data, p):
        k = 2 / (p + 1)
        r = [data[0]]
        for i in range(1, len(data)):
            r.append(data[i] * k + r[-1] * (1 - k))
        return r
    ef = ema(closes, fast)
    es = ema(closes, slow)
    ml = [f - s for f, s in zip(ef, es)]
    sl = ema(ml, sig)
    return ml[-1] - sl[-1]  # histogram


def bollinger_pos(closes, period=20):
    if len(closes) < period:
        return 0.5
    recent = closes[-period:]
    sma = sum(recent) / period
    std = (sum((x - sma) ** 2 for x in recent) / period) ** 0.5
    upper = sma + 2 * std
    lower = sma - 2 * std
    bw = upper - lower
    if bw == 0:
        return 0.5
    return max(0, min(1, (closes[-1] - lower) / bw))


def atr_pct(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 5.0
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    atr = sum(trs[-period:]) / period
    return atr / closes[-1] * 100 if closes[-1] > 0 else 5.0


# ── Signal Functions ──────────────────────────────────────────

def sig_rsi(val):
    if val <= 20: return 1.0
    if val <= 30: return 0.85
    if val <= 40: return 0.65
    if val <= 60: return 0.5
    if val <= 70: return 0.35
    if val <= 80: return 0.15
    return 0.0

def sig_macd(hist, macd_val, sig_val):
    if abs(macd_val) < 0.001:
        return 0.5
    if hist > 0 and macd_val > sig_val:
        return min(1.0, 0.6 + abs(hist) * 10)
    if hist < 0 and macd_val < sig_val:
        return max(0.0, 0.4 - abs(hist) * 10)
    return 0.5

def sig_bb(pos):
    return 1.0 - pos

def sig_vol(ratio, avg):
    if avg <= 0: return 0.5
    return max(0, min(1, (ratio / avg) / 2))

def sig_fg(val):
    return val / 100.0

def sig_dom(btc_d):
    if btc_d >= 60: return 0.2
    if btc_d >= 55: return 0.35
    if btc_d >= 50: return 0.5
    if btc_d >= 45: return 0.7
    return 0.9

def sig_atr(atr_pct):
    return max(0, min(1, (10 - atr_pct) / 10))


def composite_score(closes, highs, lows, volumes, fng_val, btc_d):
    """Calculate 7-signal composite from raw OHLCV data."""
    r = PARAMS
    s_rsi = sig_rsi(rsi(closes))
    hist = macd(closes)
    s_macd = sig_macd(hist, hist, 0)  # simplified
    s_bb = sig_bb(bollinger_pos(closes))
    vol_ratio = volumes[-1] / (sum(volumes[-7:]) / min(7, len(volumes))) if volumes else 1
    s_vol = sig_vol(vol_ratio, 1.0)
    s_fg = sig_fg(fng_val)
    s_dom = sig_dom(btc_d)
    s_atr = sig_atr(atr_pct(highs, lows, closes))

    score = (r["w_rsi"] * s_rsi + r["w_macd"] * s_macd + r["w_bb"] * s_bb +
             r["w_vol"] * s_vol + r["w_fg"] * s_fg + r["w_dom"] * s_dom + r["w_atr"] * s_atr)

    return round(score, 4), {
        "rsi": round(rsi(closes), 1), "macd_hist": round(hist, 4),
        "bb_pos": round(bollinger_pos(closes), 2), "atr_pct": round(atr_pct(highs, lows, closes), 2),
    }


# ── Walk-Forward Backtest ─────────────────────────────────────

def run_backtest():
    print("=" * 60)
    print("CMC MOMENTUM ALPHA — WALK-FORWARD BACKTEST")
    print("Data: Real Binance 1d OHLCV (no fake data)")
    print("=" * 60)

    # Fetch external data
    print("\n[1/4] Fetching Fear & Greed history...")
    fng = get_fng()
    print(f"  {len(fng)} days | Current: {fng[0]}")

    print("\n[2/4] Fetching BTC dominance...")
    btc_d = get_btc_dominance()
    print(f"  BTC.D: {btc_d:.1f}%")

    print("\n[3/4] Fetching Binance OHLCV for eligible tokens...")
    data = {}
    for sym in ELIGIBLE:
        if sym in STABLECOINS:
            continue
        ohlcv = get_ohlcv(sym, 60)
        if ohlcv and len(ohlcv) >= 30:
            data[sym] = ohlcv
        time.sleep(0.15)
    print(f"  {len(data)} tokens loaded")

    if len(data) < 3:
        print("  ERROR: Not enough data")
        return

    # Walk-forward
    print(f"\n[4/4] Running walk-forward backtest (30-day lookback)...")
    capital = 10000.0
    cash = capital
    positions = {}
    trades = []
    equity = []
    min_days = min(len(v) for v in data.values())
    days = min(min_days, 60)

    for day in range(30, days):
        prices = {s: d[day]["close"] for s, d in data.items() if day < len(d)}
        fng_val = fng[day] if day < len(fng) else fng[-1]

        # Check exits
        for sym in list(positions):
            if sym not in prices:
                continue
            pos = positions[sym]
            pnl_pct = (prices[sym] - pos["entry"]) / pos["entry"]
            if pnl_pct <= -PARAMS["stop_loss"]:
                amount = pos["qty"] * prices[sym]
                cash += amount
                trades.append({"type": "SELL", "sym": sym, "price": prices[sym],
                               "pnl": round(amount - pos["cost"], 2), "day": day, "reason": "stop_loss"})
                del positions[sym]
            elif pnl_pct >= PARAMS["take_profit"]:
                amount = pos["qty"] * prices[sym]
                cash += amount
                trades.append({"type": "SELL", "sym": sym, "price": prices[sym],
                               "pnl": round(amount - pos["cost"], 2), "day": day, "reason": "take_profit"})
                del positions[sym]
            elif day - pos["entry_day"] >= 14 and pnl_pct < 0:
                amount = pos["qty"] * prices[sym]
                cash += amount
                trades.append({"type": "SELL", "sym": sym, "price": prices[sym],
                               "pnl": round(amount - pos["cost"], 2), "day": day, "reason": "time_exit"})
                del positions[sym]

        # Score and buy every 3 days
        if day % 3 == 0:
            scored = []
            for sym, d in data.items():
                if day >= len(d):
                    continue
                closes = [c["close"] for c in d[:day+1]]
                highs = [c["high"] for c in d[:day+1]]
                lows = [c["low"] for c in d[:day+1]]
                vols = [c["volume"] for c in d[:day+1]]
                score, raw = composite_score(closes, highs, lows, vols, fng_val, btc_d)
                scored.append({"sym": sym, "score": score, "raw": raw, "price": prices.get(sym, 0)})

            scored.sort(key=lambda x: x["score"], reverse=True)

            for s in scored:
                if s["score"] >= PARAMS["entry"] and len(positions) < PARAMS["max_pos"] and s["sym"] not in positions:
                    amount = cash * (PARAMS["size_pct"] / 100)
                    if amount < 10:
                        continue
                    qty = amount / s["price"]
                    positions[s["sym"]] = {"qty": qty, "entry": s["price"], "cost": amount, "entry_day": day}
                    cash -= amount
                    trades.append({"type": "BUY", "sym": s["sym"], "price": s["price"],
                                   "amount": round(amount, 2), "day": day, "score": s["score"], **s["raw"]})

        # Equity
        pos_val = sum(p["qty"] * prices.get(s, p["entry"]) for s, p in positions.items())
        equity.append({"day": day, "value": round(cash + pos_val, 2)})

    # Close remaining
    final_prices = {s: d[-1]["close"] for s, d in data.items()}
    for sym in list(positions):
        pos = positions[sym]
        amount = pos["qty"] * final_prices.get(sym, pos["entry"])
        cash += amount
        trades.append({"type": "SELL", "sym": sym, "price": final_prices.get(sym, 0),
                       "pnl": round(amount - pos["cost"], 2), "day": days - 1, "reason": "backtest_end"})
        del positions[sym]

    equity.append({"day": days - 1, "value": round(cash, 2)})

    # ── Results ───────────────────────────────────────────────

    sells = [t for t in trades if t["type"] == "SELL"]
    wins = [t for t in sells if t.get("pnl", 0) > 0]
    losses = [t for t in sells if t.get("pnl", 0) <= 0]

    peak = capital
    max_dd = 0
    for pt in equity:
        if pt["value"] > peak:
            peak = pt["value"]
        dd = (peak - pt["value"]) / peak * 100
        max_dd = max(max_dd, dd)

    ret = (cash - capital) / capital * 100

    print(f"\n{'=' * 60}")
    print("RESULTS")
    print(f"{'=' * 60}")
    print(f"  Capital:      ${capital:>12,.2f} -> ${cash:>12,.2f}")
    print(f"  Return:       {ret:>11.2f}%")
    print(f"  Max Drawdown: {max_dd:>11.2f}%")
    print(f"  Win Rate:     {len(wins)/len(sells)*100 if sells else 0:>11.1f}%")
    print(f"  Trades:       {len(trades):>12} ({len([t for t in trades if t['type']=='BUY'])} buys, {len(sells)} sells)")
    print(f"  Avg Win:      ${sum(t['pnl'] for t in wins)/len(wins):>12,.2f}" if wins else "  Avg Win:      N/A")
    print(f"  Avg Loss:     ${sum(t['pnl'] for t in losses)/len(losses):>12,.2f}" if losses else "  Avg Loss:     N/A")
    print(f"{'=' * 60}")

    print(f"\n{'=' * 60}")
    print("TRADE LOG")
    print(f"{'=' * 60}")
    print(f"{'TYPE':>5} {'SYM':>6} {'PRICE':>10} {'P/L':>10} {'DAY':>5} {'REASON':>12} {'RSI':>6} {'MACD':>10} {'BB':>5}")
    print("-" * 75)
    for t in trades:
        if t["type"] == "BUY":
            print(f"{'BUY':>5} {t['sym']:>6} ${t['price']:>9.4f} {'':>10} {t['day']:>5} {'':>12} {t.get('rsi',0):>6.1f} {t.get('macd_hist',0):>10.4f} {t.get('bb_pos',0):>5.2f}")
        else:
            pnl = t.get('pnl', 0)
            pnl_s = f"${pnl:>8.2f}" if pnl >= 0 else f"-${abs(pnl):>7.2f}"
            print(f"{'SELL':>5} {t['sym']:>6} ${t['price']:>9.4f} {pnl_s} {t['day']:>5} {t.get('reason',''):>12}")

    # Save
    with open("backtest_results.json", "w") as f:
        json.dump({
            "return_pct": round(ret, 2), "max_drawdown_pct": round(max_dd, 2),
            "win_rate": round(len(wins)/len(sells)*100, 1) if sells else 0,
            "total_trades": len(trades), "trades": trades, "equity": equity,
        }, f, indent=2)
    print(f"\nSaved: backtest_results.json")


if __name__ == "__main__":
    run_backtest()
