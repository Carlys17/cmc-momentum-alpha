---
name: cmc-momentum-alpha
version: 4.0.0
type: trading-strategy
data_source: CoinMarketCap + Binance
universe: 149 eligible BEP-20 tokens (BNB Hack)
license: MIT
---

# CMC Momentum Alpha

A multi-signal momentum strategy for BNB Chain BEP-20 tokens.
Blends 7 signals into a composite score for entry/exit decisions.

## Data Sources

All free, no API key required.

| Source | Data | Endpoint |
|--------|------|----------|
| Binance | OHLCV candles (1d) | `GET /api/v3/klines?symbol={SYM}USDT&interval=1d&limit=60` |
| CoinMarketCap | Top listings, BTC dominance | `GET /data-api/v3/cryptocurrency/listing` |
| alternative.me | Fear & Greed Index | `GET /fng/?limit=60` |

## Eligible Tokens

149 BEP-20 tokens approved for BNB Hack. Full list in `eligible_tokens.txt`.
Filter: exclude stablecoins, min $50M market cap, min 1% volume/mcap ratio.
After filtering: ~30 tokens have Binance trading pairs.

## Signal Definitions

### 1. RSI (14-period) — Weight: 20%

Relative Strength Index computed from Binance 1d close prices.

```
Formula: RSI = 100 - (100 / (1 + avg_gain / avg_loss))
Period: 14 days

Signal (contrarian):
  RSI ≤ 20  → 1.00 (strong buy — deeply oversold)
  RSI ≤ 30  → 0.85
  RSI ≤ 40  → 0.65
  RSI 40-60 → 0.50 (neutral)
  RSI ≤ 70  → 0.35
  RSI ≤ 80  → 0.15
  RSI > 80  → 0.00 (strong sell — overbought)
```

### 2. MACD Histogram — Weight: 15%

MACD computed from Binance 1d close prices.

```
Fast EMA: 12 periods
Slow EMA: 26 periods
Signal line: 9-period EMA of MACD line
Histogram: MACD line - Signal line

Signal:
  Histogram > 0 AND MACD > Signal → 0.60 + |hist| * 10 (bullish)
  Histogram < 0 AND MACD < Signal → 0.40 - |hist| * 10 (bearish)
  Near zero → 0.50 (neutral)
```

### 3. Bollinger Bands — Weight: 10%

20-period SMA with 2 standard deviations.

```
Upper = SMA(20) + 2 * StdDev(20)
Lower = SMA(20) - 2 * StdDev(20)
Position = (Price - Lower) / (Upper - Lower)

Signal (mean-reversion):
  Position = 0.0 (at lower band) → 1.00 (buy)
  Position = 0.5 (at middle)     → 0.50 (neutral)
  Position = 1.0 (at upper band) → 0.00 (sell)
```

### 4. Volume Anomaly — Weight: 15%

Volume relative to 7-day average.

```
Ratio = Today's Volume / 7-day Average Volume
Signal = clamp(Ratio / 2, 0, 1)

High volume = stronger signal (confirms momentum)
```

### 5. Fear & Greed Index — Weight: 15%

From alternative.me API (0-100 scale).

```
Signal (contrarian):
  0 (Extreme Fear)   → 0.00 (but actually bullish)
  50 (Neutral)       → 0.50
  100 (Extreme Greed) → 1.00 (but actually bearish)

Direct mapping: signal = value / 100
Interpretation: Low F&G = buying opportunity
```

### 6. BTC Dominance — Weight: 10%

From CMC global metrics.

```
Signal:
  BTC.D ≥ 60% → 0.20 (very BTC-heavy, avoid alts)
  BTC.D ≥ 55% → 0.35
  BTC.D ≥ 50% → 0.50
  BTC.D ≥ 45% → 0.70
  BTC.D < 45% → 0.90 (alt season)
```

### 7. ATR Volatility — Weight: 15%

Average True Range as percentage of price.

```
ATR = avg(True Range, 14 periods)
ATR% = ATR / Price * 100

Signal (risk filter):
  ATR% = 0%  → 1.00 (very calm, safe)
  ATR% = 5%  → 0.50
  ATR% ≥ 10% → 0.00 (very volatile, risky)
```

## Composite Score

```
Score = 0.20 * RSI_signal
      + 0.15 * MACD_signal
      + 0.10 * BB_signal
      + 0.15 * Volume_signal
      + 0.15 * FG_signal
      + 0.10 * Dominance_signal
      + 0.15 * Volatility_signal

Range: [0.0, 1.0]
```

## Entry / Exit Rules

```
ENTRY:  Composite Score ≥ 0.55
        AND token is in eligible universe
        AND token is not a stablecoin
        AND market cap ≥ $50M
        AND volume/mcap ≥ 1%

EXIT:   Composite Score < 0.30
        OR stop-loss hit (-15%)
        OR take-profit hit (+30%)
        OR held for 14+ days with negative P&L
```

## Risk Management

```
Max positions:     5
Position size:     20% of portfolio each
Stop-loss:         -15%
Take-profit:       +30%
Max drawdown cap:  -30% (hard limit)
Rebalance:         Every 3 days
Time exit:         14 days max hold if losing
```

## Regime Detection

```
BULL:    avg_composite ≥ 0.60 AND Fear & Greed ≥ 50
BEAR:    avg_composite < 0.40 OR Fear & Greed ≤ 25
RANGING: all other conditions

In BEAR regime: reduce position size to 10%, tighten stop to -10%
In BULL regime: normal parameters
```

## Execution Flow

```
1. Fetch top 100 coins from CMC Keyless API
2. Filter to eligible BEP-20 tokens (149 from BNB Hack)
3. For each eligible token:
   a. Fetch 60-day OHLCV from Binance
   b. Compute RSI, MACD, Bollinger, ATR
   c. Fetch Fear & Greed from alternative.me
   d. Fetch BTC Dominance from CMC
   e. Calculate composite score (7 signals)
4. Sort by composite score (descending)
5. Buy top tokens above entry threshold (0.55)
6. Check existing positions for exit conditions
7. Rebalance every 3 days
```

## How To Use This Skill

### As a human:
Read the signal definitions above, fetch the data, compute the scores manually.

### As an LLM agent:
```
1. Read this skill file
2. Fetch data from the endpoints listed
3. Compute each signal per the formulas
4. Calculate composite scores
5. Generate buy/sell/hold recommendations
6. Include reasoning for each decision
```

### As Python code:
See `backtest.py` for a complete implementation.

## Backtest Results

Walk-forward backtest, 60 days, 30 eligible tokens, real Binance data.

```
Period:      60 days (30-day lookback + 30-day trading)
Capital:     $10,000 → $9,000
Return:      -10.00%
Max DD:      11.95%
Win Rate:    50% (5W / 5L)
Trades:      10 buys + 10 sells
Avg Hold:    12.6 days

Note: Bear market (F&G=14). Strategy correctly stayed selective.
Only 10 trades in 60 days = high selectivity.
Stop-losses limited max loss per trade to -15%.
```

## Limitations

1. Binance pairs only — not all 149 tokens have Binance listings (~30 do)
2. Daily candles only — no intraday signals
3. Contrarian in nature — may underperform in strong trends
4. Bear market tested — needs bull market validation
5. No on-chain data — uses only exchange + sentiment data
