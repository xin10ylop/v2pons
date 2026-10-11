# The bot's 3.0 and 5.0 ETH lines, Oct 10 14:00 - Oct 11 14:30 UTC: regime and replay (HANDOFF 16.14)

Data: every v3.0 (708) and v5.0 (223) launch of the 24 hours (`data/window.json`), every Swap and ModifyLiquidity log to launch + 1,200
blocks and every transaction of those swaps (54,950), fetched over the public RPC by `fetch.py`, `fetch_txs.py`; the big files
(`data/events.json` 44 MB, `rec.json` 35 MB, `txs_*.jsonl`, `pools.json`, `inits.json`, `facts.json`) were not kept in the repository (the
fetch rebuilds them in about 15 minutes). `regime.py` -> `regime.txt`/`regime.json` (the hour-by-hour table); `botbuys.py`, `actors.py`,
`trap_offsets.py`, `trap.py` (the outsider-and-pull evidence); `replay_rules.py` -> `replay_rules.txt`/`.json` (the exact replay of the
candidate rules, old and new regime, 0.002 and 0.0058 ETH; its model is in its docstring). The analysis agent stopped before writing up;
the reading of the results is HANDOFF 16.14.
