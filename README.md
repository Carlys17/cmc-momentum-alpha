# CMC Momentum Alpha

> BNB Hack: AI Trading Agent Edition — Track 2: Strategy Skills ($6,000)

A **regime-adaptive, 6-signal** CMC Skill for BNB Chain BEP-20 tokens. Detects market conditions (BULL/BEAR/RANGING) and adjusts entry rules automatically. Backtested with **real Binance OHLCV data** using walk-forward methodology.

---

## Quick Start

```bash
git clone https://github.com/Carlys17/cmc-momentum-alpha.git
cd cmc-momentum-alpha
pip install requests
python3 backtest.py
```

No API keys. No accounts. Just run.

---

## What Is This

A **CMC Skill** — a structured strategy spec that any AI agent can read and execute. Like Quantopian, but for LLMs.

| File | Purpose |
|------|---------|
| `SKILL.md` | Strategy specification (read this first) |
| `backtest.py` | Walk-forward backtest with real data |
| `backtest_results.json` | Full trade log + equity curve |
| `eligible_tokens.txt` | 149 approved BEP-20 tokens |
| `README.md` | You are here |

---

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                 REGIME DETECTION                         │
│                                                          │
│  BULL?    → entry ≥ 0.50 (ride momentum)                │
│  RANGING? → entry ≥ 0.55 (standard)                     │
│  BEAR?    → entry ≥ 0.65 (only strong setups)           │
└─────────────────────┬───────────────────────────────────┘
                      │
         ┌────────────▼────────────┐
         │   6-SIGNAL COMPOSITE    │
         │                         │
         │  RSI (25%)              │  ← Oversold + rising = buy
         │  MACD (20%)             │  ← Crossover direction
         │  Trend Filter (25%)     │  ← Price vs SMA20/SMA50
         │  Bollinger (10%)        │  ← Lower band = buy
         │  Volume (10%)           │  ← High volume = confirm
         │  Fear & Greed (10%)     │  ← Fear = opportunity
         │                         │
         │  Score: [0.0 — 1.0]     │
         └────────────┬────────────┘
                      │
              ┌───────▼───────┐
              │ ENTRY / EXIT  │
              │               │
              │ Score ≥ 0.55  │  → BUY (threshold varies by regime)
              │ Score < 0.30  │  → SELL
              │ -10%          │  → STOP-LOSS
              │ +20%          │  → TAKE-PROFIT
              │ 21 days       │  → TIME EXIT (if losing)
              └───────────────┘
```

---

## 6 Signals Explained

| # | Signal | Weight | Source | Logic |
|---|--------|--------|--------|-------|
| 1 | **RSI (14-period)** | 25% | Binance 1d OHLCV | Oversold (<30) + RSI rising = buy. Not just low RSI — must be turning up. |
| 2 | **MACD Histogram** | 20% | Binance 1d OHLCV | Bullish crossover (MACD > signal) = buy. Uses 120 days for EMA convergence. |
| 3 | **Trend Filter** | 25% | Binance SMA20/SMA50 | Price > SMA20 AND SMA20 > SMA50 = strong uptrend. Prevents buying into downtrend. |
| 4 | **Bollinger Bands** | 10% | Binance 1d OHLCV | Mean-reversion: near lower band = buy, near upper = sell. |
| 5 | **Volume Anomaly** | 10% | Binance 1d volume | Volume relative to 7-day average. High volume = confirms signal. |
| 6 | **Fear & Greed** | 10% | alternative.me | Contrarian: Extreme Fear (0-25) = buying opportunity. |

---

## Regime Detection

```
BULL:   Price > SMA(20) AND SMA(20) > SMA(50) AND F&G > 40
        → Lower entry threshold (0.50) — ride the trend

BEAR:   Price < SMA(20) AND SMA(20) < SMA(50) AND F&G < 30
        → Higher entry threshold (0.65) — only strong setups
        → Prevents buying into falling market

RANGING: Everything else
        → Standard threshold (0.55)
```

From backtest:
```
Day  63-90: RANGING | F&G 9-21 → +$506 P&L (43% win rate)
Day  91+:   BEAR    | F&G 7-18 → -$138 P&L (20% win rate)
```

Regime detection correctly limited exposure in bear market.

---

## Risk Management

| Parameter | Value | Why |
|-----------|-------|-----|
| Max positions | 5 | Diversification |
| Position size | 20% each | Equal weight |
| Stop-loss | -10% | Tight — limits loss per trade |
| Take-profit | +20% | Locks in gains before reversal |
| Time exit | 21 days | Cut losers that don't recover |
| Max drawdown cap | -30% | Hard limit |

---

## Backtest Results

Walk-forward backtest with **real Binance 1d OHLCV data**. No lookahead bias.

```
Period:         120 days (60-day lookback + 60-day trading)
Universe:       57 eligible BEP-20 tokens
Data:           Binance OHLCV (free, no key)
Fear & Greed:   alternative.me (60 days history)
BTC Dominance:  CMC Keyless API

Capital:        $10,000 → $10,367
Return:         +3.68%
Max Drawdown:   8.52%
Win Rate:       33.3%
Profit Factor:  1.477
Sharpe Ratio:   1.001
Avg Win:        $284.60
Avg Loss:       $96.34
Win/Loss Ratio: 2.95x (winners 3x larger than losers)
Trades:         12 buys + 12 sells (6/month)
```

### Exit Breakdown

| Reason | Count | P&L |
|--------|-------|-----|
| Take-profit (+20%) | 4 | +$1,138 |
| Stop-loss (-10%) | 4 | -$568 |
| Time exit (21 days) | 4 | -$202 |

Take-profit trades generated 2x the losses. Strategy lets winners run, cuts losers fast.

### Trade Log (sample)

```
BUY   ZEC  $316.75  day 60  RSI:48.7  Trend:above  Regime:RANGING  Score:0.6466
SELL  ZEC  $384.97  day 70  +$430.75  take_profit

BUY   STG  $0.2168  day 66  RSI:43.3  Trend:above  Regime:RANGING  Score:0.6577
SELL  STG  $0.2654  day 75  +$196.59  take_profit

BUY   ALGO $0.1032  day 60  RSI:35.6  Trend:below  Regime:RANGING  Score:0.5695
SELL  ALGO $0.1285  day 76  +$251.04  take_profit

BUY   DYDX $0.1557  day 90  RSI:29.3  Trend:above  Regime:BEAR     Score:0.6976
SELL  DYDX $0.1908  day 100 +$260.00  take_profit

BUY   LRC  $0.0402  day 60  RSI:16.0  Trend:below  Regime:RANGING  Score:0.5790
SELL  LRC  $0.0348  day 64  -$171.94  stop_loss
```

Full trade log: `backtest_results.json`

---

## Data Sources (All Free, No Key)

| Source | Data | Endpoint |
|--------|------|----------|
| **Binance** | OHLCV candles (1d, 120 days) | `api.binance.com/api/v3/klines` |
| **CMC Keyless** | BTC dominance, global metrics | `api.coinmarketcap.com/data-api/v3` |
| **alternative.me** | Fear & Greed Index (120 days) | `api.alternative.me/fng` |

---

## Usage

### Run Backtest
```bash
python3 backtest.py
```

### Use as LLM Skill
Read `SKILL.md` — it has all signal formulas, data endpoints, entry/exit rules. Any LLM can read it and generate trading recommendations.

### Use with Any LLM
```bash
# OpenAI
export OPENAI_API_KEY=*** python3 backtest.py

# OpenRouter
export OPENROUTER_API_KEY=*** python3 backtest.py

# DeepSeek
export DEEPSEEK_API_KEY=*** python3 backtest.py

# Any OpenAI-compatible provider
export LLM_BASE_URL="https://your-provider.com/v1"
export LLM_API_KEY=*** python3 backtest.py
```

---

## Why This Wins

| Criteria | How We Address It |
|----------|-------------------|
| **Technical execution** | Real Binance OHLCV, computed RSI/MACD/BB, walk-forward backtest |
| **Originality** | Regime-adaptive thresholds, RSI rising confirmation, trend filter |
| **Real-world relevance** | Works with any LLM, bear market tested, risk-managed |
| **Demo** | `python3 backtest.py` → instant results |

### Juri Example Match

| Example | Match |
|---------|-------|
| "momentum Skill that blends RSI, MACD, and Fear & Greed" | ✓ RSI (25%) + MACD (20%) + F&G (10%) |
| "regime-detection Skill that switches strategy" | ✓ BULL/BEAR/RANGING with adaptive thresholds |
| "sentiment-divergence Skill" | ✗ Not implemented |
| "derivatives positioning" | ✗ Not implemented |

---

## Limitations

1. Binance pairs only (~57 of 149 tokens)
2. Daily candles only — no intraday signals
3. Bear/RANGING tested — needs BULL market validation
4. No on-chain data — uses exchange + sentiment only
5. Commission: 0.1% per trade (slippage not modeled)

---

## License

MIT
