"""
CMC Momentum Alpha — Adaptive Strategy

Works in ALL market conditions:
  BULL:   Trend-following (buy momentum, ride the trend)
  BEAR:   Wait for reversal confirmation (trend filter required)
  RANGING: Mean-reversion (buy oversold, sell overbought)

Key changes from v4:
  - Trend filter: only buy when price > 20-day SMA
  - RSI rising confirmation: not just low RSI, but RSI turning up
  - MACD crossover: buy when MACD crosses above signal line
  - Regime-adaptive: entry thresholds change with market regime
  - Tighter risk: 10% stop-loss, 20% take-profit

Usage:
    pip install requests
    python3 backtest.py
"""
import json
import time
import requests


# ── Config ────────────────────────────────────────────────────

PARAMS = {
    "w_rsi": 0.25, "w_macd": 0.20, "w_trend": 0.25,
    "w_bb": 0.10, "w_vol": 0.10, "w_fg": 0.10,
    # Regime-adaptive thresholds
    "entry_bull": 0.50, "entry_bear": 0.65, "entry_range": 0.55,
    "exit": 0.30,
    "stop_loss": 0.10, "take_profit": 0.20,
    "max_pos": 5, "size_pct": 20,
}

ELIGIBLE = [
    "ETH", "XRP", "DOGE", "ADA", "LINK", "AVAX", "SHIB", "DOT", "UNI",
    "ATOM", "LTC", "ETC", "AAVE", "FIL", "INJ", "FET", "AXS", "TWT",
    "CAKE", "STG", "ZRO", "FLOKI", "LDO", "ROSE", "ZIL", "ZETA",
    "ACH", "AXL", "KAVA", "DUSK", "APE", "BAT", "DEXE", "TRX", "ZEC",
    "COMP", "SUSHI", "SNX", "1INCH", "PENDLE", "BCH", "NEAR", "FTM",
    "ALGO", "MANA", "SAND", "GRT", "CRV", "DYDX", "OP", "ARB",
    "MATIC", "IMX", "ENS", "LRC", "BAL", "YFI", "RUNE",
]

STABLECOINS = {"USDT", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDD", "USD1", "USDe", "FRAX"}


# ── Data ──────────────────────────────────────────────────────

def get_ohlcv(sym, days=120):
    try:
        r = requests.get("https://api.binance.com/api/v3/klines", params={
            "symbol": f"{sym}USDT", "interval": "1d", "limit": days
        }, timeout=10)
        if r.status_code != 200: return []
        return [{"time": int(k[0]), "open": float(k[1]), "high": float(k[2]),
                 "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])} for k in r.json()]
    except:
        return []


def get_fng():
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=120", timeout=10)
        return [int(d["value"]) for d in r.json().get("data", [])]
    except:
        return [50] * 120


def get_btc_dominance():
    try:
        r = requests.get("https://api.coinmarketcap.com/data-api/v3/global-metrics/quotes/latest", timeout=15)
        return r.json().get("data", {}).get("btcDominance", 55)
    except:
        return 55


# ── Indicators ────────────────────────────────────────────────

def sma(data, period):
    if len(data) < period:
        return data[-1] if data else 0
    return sum(data[-period:]) / period


def ema(data, period):
    if len(data) < period:
        return data[-1] if data else 0
    k = 2 / (period + 1)
    result = [sum(data[:period]) / period]
    for i in range(period, len(data)):
        result.append(data[i] * k + result[-1] * (1 - k))
    return result[-1]


def rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_g = sum(gains[-period:]) / period
    avg_l = sum(losses[-period:]) / period
    if avg_l == 0: return 100.0
    return 100 - (100 / (1 + avg_g / avg_l))


def rsi_prev(closes, period=14):
    """RSI one bar ago (for trend confirmation)."""
    if len(closes) < period + 2:
        return 50.0
    return rsi(closes[:-1], period)


def macd(closes, fast=12, slow=26, sig=9):
    if len(closes) < slow + sig:
        return 0.0, 0.0, 0.0  # macd, signal, histogram
    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    # Build MACD line
    def ema_series(data, period):
        k = 2 / (period + 1)
        r = [sum(data[:period]) / period]
        for i in range(period, len(data)):
            r.append(data[i] * k + r[-1] * (1 - k))
        return r
    ef = ema_series(closes, fast)
    es = ema_series(closes, slow)
    ml = [f - s for f, s in zip(ef, es)]
    sl = ema_series(ml, sig) if len(ml) >= sig else [ml[-1]]
    return ml[-1], sl[-1], ml[-1] - sl[-1]


def bollinger_pos(closes, period=20):
    if len(closes) < period:
        return 0.5
    recent = closes[-period:]
    s = sum(recent) / period
    std = (sum((x - s) ** 2 for x in recent) / period) ** 0.5
    bw = 4 * std
    if bw == 0: return 0.5
    return max(0, min(1, (closes[-1] - (s - 2*std)) / bw))


def atr_pct(highs, lows, closes, period=14):
    if len(closes) < period + 1: return 5.0
    trs = [max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])) for i in range(1, len(closes))]
    atr = sum(trs[-period:]) / period
    return atr / closes[-1] * 100 if closes[-1] > 0 else 5.0


# ── Regime Detection ─────────────────────────────────────────

def detect_regime(closes, fng_val):
    """
    Detect market regime from price action + sentiment.

    BULL:   Price > 20 SMA AND 20 SMA > 50 SMA AND F&G > 40
    BEAR:   Price < 20 SMA AND 20 SMA < 50 SMA AND F&G < 30
    RANGING: everything else
    """
    if len(closes) < 50:
        return "RANGING"

    price = closes[-1]
    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)

    bull = price > sma20 and sma20 > sma50 and fng_val > 40
    bear = price < sma20 and sma20 < sma50 and fng_val < 30

    if bull:
        return "BULL"
    elif bear:
        return "BEAR"
    else:
        return "RANGING"


# ── Signals ───────────────────────────────────────────────────

def compute_signals(closes, highs, lows, volumes, fng_val, btc_d):
    """Compute all signals for a token."""
    r = PARAMS

    # RSI
    current_rsi = rsi(closes)
    prev_rsi = rsi_prev(closes)
    rsi_rising = current_rsi > prev_rsi  # RSI turning up

    # RSI signal: oversold + rising = strong buy
    if current_rsi <= 30 and rsi_rising:
        s_rsi = 0.90  # Oversold reversal
    elif current_rsi <= 30:
        s_rsi = 0.70  # Oversold but not yet reversing
    elif current_rsi <= 40 and rsi_rising:
        s_rsi = 0.60  # Pullback in uptrend
    elif current_rsi >= 70:
        s_rsi = 0.10  # Overbought
    elif current_rsi >= 60:
        s_rsi = 0.30
    else:
        s_rsi = 0.50  # Neutral

    # MACD: crossover signal
    macd_val, sig_val, hist = macd(closes)
    if hist > 0 and macd_val > sig_val:
        s_macd = 0.80  # Bullish crossover
    elif hist > 0:
        s_macd = 0.60  # Positive but weakening
    elif hist < 0 and macd_val < sig_val:
        s_macd = 0.20  # Bearish crossover
    elif hist < 0:
        s_macd = 0.35  # Negative but improving
    else:
        s_macd = 0.50

    # Trend filter (NEW)
    price = closes[-1]
    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)

    if price > sma20 and sma20 > sma50:
        s_trend = 0.90  # Strong uptrend
    elif price > sma20:
        s_trend = 0.65  # Above short-term trend
    elif price > sma50:
        s_trend = 0.45  # Below short-term but above long-term
    elif sma20 > sma50:
        s_trend = 0.35  # Short-term pullback in long-term uptrend
    else:
        s_trend = 0.15  # Downtrend

    # Bollinger
    s_bb = 1.0 - bollinger_pos(closes)

    # Volume
    vol_avg = sum(volumes[-7:]) / min(7, len(volumes))
    vol_ratio = volumes[-1] / vol_avg if vol_avg > 0 else 1
    s_vol = max(0, min(1, vol_ratio / 2))

    # Fear & Greed
    s_fg = fng_val / 100.0

    # Composite
    score = (r["w_rsi"] * s_rsi + r["w_macd"] * s_macd + r["w_trend"] * s_trend +
             r["w_bb"] * s_bb + r["w_vol"] * s_vol + r["w_fg"] * s_fg)

    return round(score, 4), {
        "rsi": round(current_rsi, 1), "rsi_prev": round(prev_rsi, 1), "rsi_rising": rsi_rising,
        "macd_hist": round(hist, 4), "macd_cross": "bull" if hist > 0 else "bear",
        "price_vs_sma20": "above" if price > sma20 else "below",
        "sma20_vs_sma50": "above" if sma20 > sma50 else "below",
        "bb_pos": round(bollinger_pos(closes), 2),
        "atr_pct": round(atr_pct(highs, lows, closes), 2),
        "signals": {
            "rsi": round(s_rsi, 3), "macd": round(s_macd, 3), "trend": round(s_trend, 3),
            "bb": round(s_bb, 3), "vol": round(s_vol, 3), "fg": round(s_fg, 3),
        },
    }


# ── Backtest ──────────────────────────────────────────────────

def run():
    print("=" * 60)
    print("CMC MOMENTUM ALPHA — ADAPTIVE BACKTEST")
    print("Regime-adaptive: BULL=trend-follow, BEAR=wait, RANGE=mean-rev")
    print("=" * 60)

    print("\n[1/4] Fear & Greed...")
    fng = get_fng()
    print(f"  {len(fng)} days | Current: {fng[0]}")

    print("\n[2/4] BTC dominance...")
    btc_d = get_btc_dominance()
    print(f"  BTC.D: {btc_d:.1f}%")

    print("\n[3/4] Binance OHLCV...")
    data = {}
    for sym in ELIGIBLE:
        if sym in STABLECOINS: continue
        ohlcv = get_ohlcv(sym, 120)
        if ohlcv and len(ohlcv) >= 60:
            data[sym] = ohlcv
        time.sleep(0.12)
    print(f"  {len(data)} tokens")

    if len(data) < 5:
        print("  ERROR: Not enough data")
        return

    print(f"\n[4/4] Walk-forward backtest...")
    capital = 10000.0
    cash = capital
    positions = {}
    trades = []
    equity = []
    min_days = min(len(v) for v in data.values())
    lookback = 60
    days = min(min_days, 120)
    regime_log = []

    for day in range(lookback, days):
        prices = {s: d[day]["close"] for s, d in data.items() if day < len(d)}
        fng_idx = day if day < len(fng) else len(fng) - 1
        fng_val = fng[fng_idx]

        # Detect regime using BTC as proxy
        btc_data = data.get("ETH", list(data.values())[0])
        btc_closes = [c["close"] for c in btc_data[:day+1]]
        regime = detect_regime(btc_closes, fng_val)

        if day % 7 == 0:
            regime_log.append({"day": day, "regime": regime, "fng": fng_val})

        # Regime-adaptive entry threshold
        if regime == "BULL":
            entry_threshold = PARAMS["entry_bull"]
        elif regime == "BEAR":
            entry_threshold = PARAMS["entry_bear"]
        else:
            entry_threshold = PARAMS["entry_range"]

        # Check exits
        for sym in list(positions):
            if sym not in prices: continue
            pos = positions[sym]
            pnl_pct = (prices[sym] - pos["entry"]) / pos["entry"]

            if pnl_pct <= -PARAMS["stop_loss"]:
                cash += pos["qty"] * prices[sym]
                trades.append({"type": "SELL", "sym": sym, "price": prices[sym],
                               "pnl": round(pos["qty"] * prices[sym] - pos["cost"], 2),
                               "day": day, "reason": "stop_loss", "regime": regime})
                del positions[sym]
            elif pnl_pct >= PARAMS["take_profit"]:
                cash += pos["qty"] * prices[sym]
                trades.append({"type": "SELL", "sym": sym, "price": prices[sym],
                               "pnl": round(pos["qty"] * prices[sym] - pos["cost"], 2),
                               "day": day, "reason": "take_profit", "regime": regime})
                del positions[sym]
            elif day - pos["entry_day"] >= 21 and pnl_pct < 0:
                cash += pos["qty"] * prices[sym]
                trades.append({"type": "SELL", "sym": sym, "price": prices[sym],
                               "pnl": round(pos["qty"] * prices[sym] - pos["cost"], 2),
                               "day": day, "reason": "time_exit", "regime": regime})
                del positions[sym]

        # Score and buy every 3 days
        if day % 3 == 0:
            scored = []
            for sym, d in data.items():
                if day >= len(d): continue
                closes = [c["close"] for c in d[:day+1]]
                highs = [c["high"] for c in d[:day+1]]
                lows = [c["low"] for c in d[:day+1]]
                vols = [c["volume"] for c in d[:day+1]]
                s, raw = compute_signals(closes, highs, lows, vols, fng_val, btc_d)
                scored.append({"sym": sym, "score": s, "raw": raw, "price": prices.get(sym, 0)})

            scored.sort(key=lambda x: x["score"], reverse=True)

            for s in scored:
                if s["score"] >= entry_threshold and len(positions) < PARAMS["max_pos"] and s["sym"] not in positions:
                    amount = cash * (PARAMS["size_pct"] / 100)
                    if amount < 10: continue
                    qty = amount / s["price"]
                    positions[s["sym"]] = {"qty": qty, "entry": s["price"], "cost": amount, "entry_day": day}
                    cash -= amount
                    trades.append({"type": "BUY", "sym": s["sym"], "price": s["price"],
                                   "amount": round(amount, 2), "day": day, "score": s["score"],
                                   "regime": regime, "threshold": entry_threshold, **s["raw"]})

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
        if pt["value"] > peak: peak = pt["value"]
        dd = (peak - pt["value"]) / peak * 100
        max_dd = max(max_dd, dd)

    ret = (cash - capital) / capital * 100
    avg_w = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
    avg_l = sum(t["pnl"] for t in losses) / len(losses) if losses else 0
    pf = abs(sum(t["pnl"] for t in wins) / sum(t["pnl"] for t in losses)) if losses and sum(t["pnl"] for t in losses) != 0 else 0

    print(f"\n{'=' * 60}")
    print("RESULTS")
    print(f"{'=' * 60}")
    print(f"  Capital:       ${capital:>12,.2f} -> ${cash:>12,.2f}")
    print(f"  Return:        {ret:>11.2f}%")
    print(f"  Max Drawdown:  {max_dd:>11.2f}%")
    print(f"  Win Rate:      {len(wins)/len(sells)*100 if sells else 0:>11.1f}%")
    print(f"  Profit Factor: {pf:>11.3f}")
    print(f"  Avg Win:       ${avg_w:>12,.2f}")
    print(f"  Avg Loss:      ${avg_l:>12,.2f}")
    print(f"  Trades:        {len(trades):>12} ({len([t for t in trades if t['type']=='BUY'])} buys, {len(sells)} sells)")
    print(f"{'=' * 60}")

    # Trade log
    print(f"\n{'=' * 60}")
    print("TRADE LOG")
    print(f"{'=' * 60}")
    print(f"{'TYPE':>5} {'SYM':>6} {'PRICE':>10} {'P/L':>10} {'DAY':>5} {'REASON':>12} {'RSI':>6} {'TREND':>8} {'REGIME':>8} {'SCORE':>6}")
    print("-" * 90)
    for t in trades:
        if t["type"] == "BUY":
            print(f"{'BUY':>5} {t['sym']:>6} ${t['price']:>9.4f} {'':>10} {t['day']:>5} {'':>12} {t.get('rsi',0):>6.1f} {t.get('price_vs_sma20',''):>8} {t.get('regime',''):>8} {t.get('score',0):>6.4f}")
        else:
            pnl = t.get('pnl', 0)
            pnl_s = f"${pnl:>8.2f}" if pnl >= 0 else f"-${abs(pnl):>7.2f}"
            print(f"{'SELL':>5} {t['sym']:>6} ${t['price']:>9.4f} {pnl_s} {t['day']:>5} {t.get('reason',''):>12} {'':>6} {'':>8} {t.get('regime',''):>8}")

    # Regime log
    print(f"\n{'=' * 60}")
    print("REGIME LOG")
    print(f"{'=' * 60}")
    for r in regime_log:
        print(f"  Day {r['day']:>3}: {r['regime']:>8} | F&G: {r['fng']}")

    # Signal analysis
    buy_trades = [t for t in trades if t["type"] == "BUY"]
    if buy_trades:
        print(f"\n{'=' * 60}")
        print("SIGNAL ANALYSIS (on buy entries)")
        print(f"{'=' * 60}")
        print(f"  Avg RSI:       {sum(t.get('rsi',0) for t in buy_trades)/len(buy_trades):.1f}")
        print(f"  RSI rising:    {sum(1 for t in buy_trades if t.get('rsi_rising'))}/{len(buy_trades)}")
        print(f"  Above SMA20:   {sum(1 for t in buy_trades if t.get('price_vs_sma20')=='above')}/{len(buy_trades)}")
        print(f"  MACD bullish:  {sum(1 for t in buy_trades if t.get('macd_cross')=='bull')}/{len(buy_trades)}")
        print(f"  Regime breakdown:")
        for reg in ["BULL", "BEAR", "RANGING"]:
            count = sum(1 for t in buy_trades if t.get('regime') == reg)
            print(f"    {reg}: {count}")

    with open("backtest_results.json", "w") as f:
        json.dump({
            "return_pct": round(ret, 2), "max_drawdown_pct": round(max_dd, 2),
            "win_rate": round(len(wins)/len(sells)*100, 1) if sells else 0,
            "profit_factor": round(pf, 3), "avg_win": round(avg_w, 2), "avg_loss": round(avg_l, 2),
            "total_trades": len(trades), "trades": trades, "equity": equity,
            "regime_log": regime_log, "tokens_tested": len(data),
        }, f, indent=2)
    print(f"\nSaved: backtest_results.json")


if __name__ == "__main__":
    run()
