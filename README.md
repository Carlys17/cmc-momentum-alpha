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

**`SKILL.md`** — the strategy. 6 signals, regime-adaptive entry/exit, trend filter. Written for LLMs.

**`backtest.py`** — the proof. Walk-forward backtest with real Binance data. +3.68% return in bear market.

## The Strategy

6 signals, regime-adaptive:

| Signal | Weight | Source | Logic |
|--------|--------|--------|-------|
| RSI (14) | 25% | Binance | Oversold + rising = buy |
| MACD | 20% | Binance | Crossover direction |
| **Trend Filter** | **25%** | **Binance** | **Price vs SMA20/SMA50** |
| Bollinger | 10% | Binance | Lower band = buy |
| Volume | 10% | Binance | High volume = strong signal |
| Fear & Greed | 10% | alternative.me | Fear = buy |

```
BULL market  → entry ≥ 0.50 (ride momentum)
RANGING      → entry ≥ 0.55 (standard)
BEAR market  → entry ≥ 0.65 (only strong setups)

Stop-loss: -10% | Take-profit: +20%
```

## Backtest Results (Real Binance Data)

```
Return:        +3.68%  (bear market — F&G 7-21)
Max Drawdown:  8.52%
Win Rate:      33.3%
Profit Factor: 1.477
Avg Win:       $284.60
Avg Loss:      $96.34
Win/Loss:      2.95x (winners 3x larger than losers)
```

## Files

```
SKILL.md               ← The strategy (read this first)
backtest.py            ← The proof (run this second)
backtest_results.json  ← Full trade log + equity curve
eligible_tokens.txt    ← 149 approved BEP-20 tokens
README.md              ← You are here
```

## License

MIT
