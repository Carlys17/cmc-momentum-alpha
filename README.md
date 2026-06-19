# CMC Momentum Alpha

<p align="center">
  <img src="logo.png" alt="CMC Momentum Alpha" width="480">
</p>

> BNB Hack: AI Trading Agent Edition — Track 2: Strategy Skills ($6,000)

A **CMC Skill** — a structured strategy spec that any AI agent can read and execute. The agent fetches real market data, computes 6 technical and sentiment signals, detects market regime, and generates trading recommendations for 149 eligible BNB Chain tokens.

---

## How It Works

```
┌─────────────────────────────────────────────────────┐
│                    AI AGENT                          │
│                                                     │
│  1. Read SKILL.md (strategy spec)                   │
│  2. Fetch data from Binance + CMC + alternative.me  │
│  3. Compute 6 signals                               │
│  4. Detect regime (BULL/BEAR/RANGING)               │
│  5. Generate buy/sell/hold recommendations           │
└─────────────────────────────────────────────────────┘

Or, as a human:
  Run backtest.py → see real results
```

---

## Quick Start

### As an AI Agent (primary use)

Load `SKILL.md` into any LLM and ask:

```
Read the SKILL.md file. Fetch data from the endpoints listed,
compute all 6 signals for the top eligible tokens, and give
me today's trading recommendations.
```

### As a Human (verification)

```bash
git clone https://github.com/Carlys17/cmc-momentum-alpha.git
cd cmc-momentum-alpha
pip install requests
python3 backtest.py
```

---

## Files

| File | Purpose | Who Reads It |
|------|---------|--------------|
| `SKILL.md` | Strategy specification | AI Agent (primary deliverable) |
| `backtest.py` | Walk-forward backtest | Human judges (verification) |
| `backtest_results.json` | Full trade log + equity curve | Human judges (proof) |
| `eligible_tokens.txt` | 149 approved BEP-20 tokens | AI Agent |
| `README.md` | Documentation | Human judges |

---

## The Strategy (SKILL.md summary)

### 6 Signals

| # | Signal | Weight | Source | Logic |
|---|--------|--------|--------|-------|
| 1 | **RSI (14-period)** | 25% | Binance 1d OHLCV | Oversold (<30) + RSI rising = buy |
| 2 | **MACD Histogram** | 20% | Binance 1d OHLCV | Bullish crossover = buy |
| 3 | **Trend Filter** | 25% | Binance SMA20/SMA50 | Price > SMA20 = uptrend |
| 4 | **Bollinger Bands** | 10% | Binance 1d OHLCV | Lower band = buy |
| 5 | **Volume Anomaly** | 10% | Binance 1d volume | High volume = confirm |
| 6 | **Fear & Greed** | 10% | alternative.me | Fear = buy opportunity |

### Regime Detection

```
BULL:   Price > SMA(20) AND SMA(20) > SMA(50) AND F&G > 40
        → Entry threshold: 0.50 (ride momentum)

BEAR:   Price < SMA(20) AND SMA(20) < SMA(50) AND F&G < 30
        → Entry threshold: 0.65 (only strong setups)

RANGING: Everything else
        → Entry threshold: 0.55 (standard)
```

### Entry / Exit Rules

```
ENTRY:  Composite score ≥ threshold (varies by regime)
EXIT:   Composite score < 0.30 OR stop-loss (-10%) OR take-profit (+20%)
RISK:   Max 5 positions, 20% each, 21-day time exit
```

---

## Example: Using with an AI Agent

### Prompt

```
You are a crypto trading analyst. Read the SKILL.md file in this repo.
It contains a trading strategy specification.

Your task:
1. Fetch 120-day OHLCV data from Binance for these tokens:
   BTC, ETH, BNB, XRP, ADA, DOGE, SOL, DOT, LINK, AVAX
   Use: GET /api/v3/klines?symbol={SYM}USDT&interval=1d&limit=120

2. Fetch Fear & Greed Index from:
   GET https://api.alternative.me/fng/?limit=120

3. For each token, compute:
   - RSI (14-period)
   - MACD histogram (12/26/9)
   - Price vs SMA20 vs SMA50
   - Bollinger Band position (20-period, 2 std dev)
   - Volume vs 7-day average

4. Detect market regime (BULL/BEAR/RANGING)

5. Calculate composite score using the weights in SKILL.md

6. Give me buy/sell/hold recommendations with reasoning
```

### Expected Output

```
MARKET REGIME: RANGING (F&G=14, BTC.D=58.2%)

RECOMMENDATIONS:

BUY:
  TRX  $0.3225  Score: 0.6517  RSI:25.0 ↑ MACD:+0.005 Trend:above SMA20
  → Oversold reversal confirmed. RSI turning up, price above short-term trend.
  → Entry: $0.3225 | Stop-loss: $0.2903 (-10%) | Take-profit: $0.3870 (+20%)

  XRP  $1.1334  Score: 0.6596  RSI:16.3 ↑ MACD:+0.023 Trend:below SMA20
  → Deeply oversold but RSI rising. High entry threshold (BEAR regime).
  → Entry: $1.1334 | Stop-loss: $1.0201 (-10%) | Take-profit: $1.3601 (+20%)

HOLD:
  ETH  $1,701    Score: 0.5200  RSI:62.3 MACD:neutral Trend:above SMA20
  → Neutral. Wait for pullback or stronger signal.

SELL:
  BNB  $579      Score: 0.2800  RSI:52.8 MACD:bearish Trend:below SMA20
  → Below SMA20 and SMA50. Downtrend confirmed. Exit if holding.
```

---

## Example: Using with Different LLMs

### OpenAI (GPT-4o)
```bash
export OPENAI_API_KEY=*** python3 backtest.py
```

### OpenRouter (any model)
```bash
export OPENROUTER_API_KEY=*** python3 backtest.py
```

### DeepSeek
```bash
export DEEPSEEK_API_KEY=*** python3 backtest.py
```

### Anthropic (Claude)
```bash
export ANTHROPIC_API_KEY=*** python3 backtest.py
```

### Google Gemini
```bash
export GEMINI_API_KEY=*** python3 backtest.py
```

### Custom Provider
```bash
export LLM_BASE_URL="https://your-provider.com/v1"
export LLM_API_KEY=*** python3 backtest.py
```

---

## Backtest Results

Walk-forward backtest with **real Binance 1d OHLCV data**. No lookahead bias. No fake data.

```
Period:         120 days (60-day lookback + 60-day trading)
Universe:       57 eligible BEP-20 tokens
Data:           Binance OHLCV (free, no key)
Fear & Greed:   alternative.me (120 days)
BTC Dominance:  CMC Keyless API

Capital:        $10,000 → $10,367
Return:         +3.68%
Max Drawdown:   8.52%
Win Rate:       33.3%
Profit Factor:  1.477
Sharpe Ratio:   1.001
Avg Win:        $284.60
Avg Loss:       $96.34
Win/Loss Ratio: 2.95x
Trades:         12 buys + 12 sells (6/month)
```

### Exit Breakdown

| Reason | Count | P&L |
|--------|-------|-----|
| Take-profit (+20%) | 4 | +$1,138 |
| Stop-loss (-10%) | 4 | -$568 |
| Time exit (21 days) | 4 | -$202 |

### Sample Trades

```
BUY   ZEC  $316.75  day 60  RSI:48.7  MACD:bull  Trend:above  Score:0.6466
SELL  ZEC  $384.97  day 70  +$430.75  take_profit

BUY   DYDX $0.1557  day 90  RSI:29.3  MACD:bull  Trend:above  Score:0.6976
SELL  DYDX $0.1908  day 100 +$260.00  take_profit

BUY   LRC  $0.0402  day 60  RSI:16.0  MACD:bear  Trend:below  Score:0.5790
SELL  LRC  $0.0348  day 64  -$171.94  stop_loss
```

Full log: `backtest_results.json`

---

## Data Sources (All Free, No Key)

| Source | Data | Endpoint |
|--------|------|----------|
| **Binance** | OHLCV candles (1d, 120 days) | `GET /api/v3/klines?symbol={SYM}USDT&interval=1d&limit=120` |
| **CMC Keyless** | BTC dominance, global metrics | `GET /data-api/v3/global-metrics/quotes/latest` |
| **alternative.me** | Fear & Greed Index (120 days) | `GET /fng/?limit=120` |

---

## CMC Skill Specification

The strategy is exported as a structured CMC Skill in `SKILL.md`:
- YAML frontmatter (name, version, type, data_source)
- Signal definitions with formulas
- Regime detection rules
- Entry/exit rules with thresholds
- Risk management parameters
- How-to guide for LLM agents

Any AI agent can read `SKILL.md` and execute the strategy.

---

## Judging Criteria

| Criteria | How We Address It |
|----------|-------------------|
| **Technical execution** | Real Binance OHLCV, computed RSI/MACD/BB, walk-forward backtest |
| **Originality** | Regime-adaptive thresholds, RSI rising confirmation, trend filter |
| **Real-world relevance** | Works with any LLM, bear market tested, risk-managed |
| **Demo** | `python3 backtest.py` → instant results |

### Juri Example Match

| Example | Status |
|---------|--------|
| "momentum Skill that blends RSI, MACD, and Fear & Greed" | ✓ |
| "regime-detection Skill that switches strategy" | ✓ |
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
