# CMC Momentum Alpha

> BNB Hack: AI Trading Agent Edition — Track 2: Strategy Skills

## Quick Start

```bash
git clone https://github.com/Carlys17/cmc-momentum-alpha.git
cd cmc-momentum-alpha
pip install requests
python3 backtest.py
```

## What Is This

A CMC Skill — one strategy spec that any LLM can read and execute.

**`SKILL.md`** — the strategy. 7 signals, entry/exit rules, risk management. Written for LLMs. Read by humans.

**`backtest.py`** — the proof. Walk-forward backtest with real Binance data. No fake numbers.

## The Strategy

7 signals blended into one score:

| Signal | Weight | Source | Logic |
|--------|--------|--------|-------|
| RSI (14) | 20% | Binance | Oversold = buy, overbought = sell |
| MACD | 15% | Binance | Histogram direction |
| Bollinger | 10% | Binance | Lower band = buy, upper = sell |
| Volume | 15% | Binance | High volume = strong signal |
| Fear & Greed | 15% | alternative.me | Fear = buy, greed = sell |
| BTC Dominance | 10% | CMC | Low BTC.D = alt season |
| Volatility | 15% | Binance | Low vol = safe = buy |

```
Score ≥ 0.55 → BUY
Score < 0.30 → SELL
Stop-loss: -15%
Take-profit: +30%
Max 5 positions, 20% each
```

## How To Use

### As an LLM Agent
Read `SKILL.md`. It has everything — signal formulas, data endpoints, entry/exit rules. Fetch the data, compute the scores, generate recommendations.

### As a Human
Run `python3 backtest.py`. It fetches real data, computes all 7 signals, and shows the trade log with entry/exit prices, RSI, MACD, Bollinger values at each trade.

### With Any LLM
```bash
# Works with OpenAI, OpenRouter, Anthropic, Gemini, DeepSeek, etc.
export OPENAI_API_KEY=*** python3 backtest.py
```

## Files

```
SKILL.md               ← The strategy (read this first)
backtest.py            ← The proof (run this second)
eligible_tokens.txt    ← 149 approved BEP-20 tokens
README.md              ← You are here
```

## Data Sources

All free, no API key:

- **Binance** — OHLCV candles (RSI, MACD, Bollinger, ATR)
- **CoinMarketCap** — Top listings, BTC dominance
- **alternative.me** — Fear & Greed Index

## License

MIT
