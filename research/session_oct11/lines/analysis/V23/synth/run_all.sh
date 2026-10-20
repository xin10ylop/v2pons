#!/bin/sh
# Re-runs the synthesizer's steps in order (no network; read-only on the repo and on the analysts'/skeptics' directories). ~10 s.
cd "$(dirname "$0")"
for s in s01_verdicts s02_lines s03_forward s04_pumpgate356 s05_probe s06_window_buys s07_halts s08_stake; do python3 -B $s.py > /dev/null || exit 1; done
echo ok
