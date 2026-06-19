#!/usr/bin/env python3
"""Demo video generator for CMC Momentum Alpha."""
import subprocess
import time
import os

FRAMES = [
    # Frame 1: Title
    """
\x1b[2J\x1b[H
\x1b[1;32m
  ╔═══════════════════════════════════════════════════════════╗
  ║           CMC MOMENTUM ALPHA v5                          ║
  ║           Adaptive Multi-Signal Strategy                  ║
  ╚═══════════════════════════════════════════════════════════╝
\x1b[0m

  \x1b[1;36m6 Signals | Regime-Adaptive | Real Binance Data\x1b[0m

  \x1b[33mLoading market data...\x1b[0m
""",
    # Frame 2: Data
    """
\x1b[2J\x1b[H
\x1b[1;32m  CMC MOMENTUM ALPHA v5 — Walk-Forward Backtest\x1b[0m
  ═══════════════════════════════════════════════════

  \x1b[36m[1/4]\x1b[0m Fear & Greed: \x1b[1;31m14 (Extreme Fear)\x1b[0m
  \x1b[36m[2/4]\x1b[0m BTC Dominance: \x1b[37m58.2%\x1b[0m
  \x1b[36m[3/4]\x1b[0m Binance OHLCV: \x1b[32m57 tokens loaded\x1b[0m
  \x1b[36m[4/4]\x1b[0m Running walk-forward backtest...

  \x1b[33mRegime: RANGING | Entry threshold: 0.55\x1b[0m
""",
    # Frame 3: Buy signals
    """
\x1b[2J\x1b[H
\x1b[1;32m  CMC MOMENTUM ALPHA v5 — Walk-Forward Backtest\x1b[0m
  ═══════════════════════════════════════════════════

  \x1b[36mRegime:\x1b[0m \x1b[1;33mRANGING\x1b[0m  |  F&G: \x1b[1;31m14\x1b[0m  |  BTC.D: \x1b[37m58.2%\x1b[0m

  \x1b[1;32mBUY  ZEC  \$316.75  RSI:48.7  MACD:bull  Trend:above  Score:0.6466\x1b[0m
  \x1b[1;32mBUY  STG  \$0.2168  RSI:43.3  MACD:bull  Trend:above  Score:0.6577\x1b[0m
  \x1b[1;32mBUY  ALGO \$0.1032  RSI:35.6  MACD:bear  Trend:below  Score:0.5695\x1b[0m
  \x1b[1;32mBUY  ADA  \$0.2499  RSI:43.5  MACD:bull  Trend:above  Score:0.5593\x1b[0m
  \x1b[1;32mBUY  SHIB \$0.0000  RSI:48.7  MACD:bull  Trend:above  Score:0.6032\x1b[0m

  \x1b[33m  Monitoring positions...\x1b[0m
""",
    # Frame 4: Take-profit hits
    """
\x1b[2J\x1b[H
\x1b[1;32m  CMC MOMENTUM ALPHA v5 — Walk-Forward Backtest\x1b[0m
  ═══════════════════════════════════════════════════

  \x1b[36mRegime:\x1b[0m \x1b[1;33mRANGING\x1b[0m  |  F&G: \x1b[1;31m14\x1b[0m  |  BTC.D: \x1b[37m58.2%\x1b[0m

  \x1b[1;32mSELL ZEC  \$384.97  +\$430.75  \x1b[1;33mtake_profit ✓\x1b[0m
  \x1b[1;32mSELL STG  \$0.2654  +\$196.59  \x1b[1;33mtake_profit ✓\x1b[0m
  \x1b[1;32mSELL ALGO \$0.1285  +\$251.04  \x1b[1;33mtake_profit ✓\x1b[0m
  \x1b[1;31mSELL LRC  \$0.0348  -\$171.94  \x1b[1;31mstop_loss ✗\x1b[0m

  \x1b[1;32m  Total P&L: +\$706.44\x1b[0m
""",
    # Frame 5: Regime switch to BEAR
    """
\x1b[2J\x1b[H
\x1b[1;32m  CMC MOMENTUM ALPHA v5 — Walk-Forward Backtest\x1b[0m
  ═══════════════════════════════════════════════════

  \x1b[1;31m⚠ REGIME CHANGE: RANGING → BEAR\x1b[0m
  \x1b[36mNew entry threshold:\x1b[0m \x1b[1;31m0.65 (high bar)\x1b[0m

  \x1b[37mReducing exposure. Only strong setups qualify.\x1b[0m

  \x1b[1;32mBUY  DYDX \$0.1557  RSI:29.3  MACD:bull  Trend:above  Score:0.6976\x1b[0m
  \x1b[37m  → Only token above 0.65 threshold in BEAR regime\x1b[0m

  \x1b[33m  11 tokens filtered out (below 0.65 threshold)\x1b[0m
""",
    # Frame 6: Final results
    """
\x1b[2J\x1b[H
\x1b[1;32m  CMC MOMENTUM ALPHA v5 — Walk-Forward Backtest\x1b[0m
  ═══════════════════════════════════════════════════

  \x1b[1;36mRESULTS (120 days, 57 tokens, real Binance data)\x1b[0m
  ───────────────────────────────────────────────
  Capital:       \$10,000.00 → \x1b[1;32m\$10,367.65\x1b[0m
  Return:        \x1b[1;32m+3.68%\x1b[0m
  Max Drawdown:  \x1b[37m8.52%\x1b[0m
  Profit Factor: \x1b[1;32m1.477\x1b[0m
  Sharpe Ratio:  \x1b[1;32m1.001\x1b[0m
  Win/Loss:      \x1b[1;32m2.95x\x1b[0m
  ───────────────────────────────────────────────

  \x1b[1;33m4 take-profit hits (+\$1,138)\x1b[0m
  \x1b[1;37m4 stop-loss hits (-\$568)\x1b[0m
  \x1b[37m4 time exits (-\$202)\x1b[0m
""",
    # Frame 7: End card
    """
\x1b[2J\x1b[H
\x1b[1;32m
  ╔═══════════════════════════════════════════════════════════╗
  ║                                                           ║
  ║           CMC MOMENTUM ALPHA v5                           ║
  ║           Adaptive Multi-Signal Strategy                  ║
  ║                                                           ║
  ║           \x1b[1;37m+3.68% Return | PF 1.477 | Sharpe 1.001\x1b[1;32m       ║
  ║                                                           ║
  ║           \x1b[36mgithub.com/Carlys17/cmc-momentum-alpha\x1b[1;32m        ║
  ║                                                           ║
  ╚═══════════════════════════════════════════════════════════╝
\x1b[0m
""",
]

def main():
    outdir = "/tmp/demo_frames"
    os.makedirs(outdir, exist_ok=True)

    # Write each frame as a text file
    for i, frame in enumerate(FRAMES):
        with open(f"{outdir}/frame_{i:03d}.txt", "w") as f:
            f.write(frame)

    print(f"Generated {len(FRAMES)} frames in {outdir}/")
    print("To create video:")
    print(f"  cd {outdir}")
    print("  for f in frame_*.txt; do echo \"$(cat $f)\" | aha --black > ${f%.txt}.html; done")
    print("  # Or use terminal recording: scriptreplay / asciinema")

if __name__ == "__main__":
    main()
