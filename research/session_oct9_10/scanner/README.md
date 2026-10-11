# Scanner for other operators on Robinhood Chain (12.6), Oct 10 18:15-22:10 UTC; second pass Oct 11 02:50-03:50 UTC

The question (the owner's): the volume bot exists, so other operators with the same structural edge (a scheduled own buy after the launch,
slack in its minOut, a pull that comes later) should exist on this chain. Find them and say what the engine would need.

Run as one workflow of 36 Opus agents from the research container over the public RPC (the box's feed was blocked, 16.11 of the handoff):
a census agent, 29 family analysts (one per group of families with 5 or more launches), 5 skeptics (one per flagged family, each
re-deriving the analyst's numbers from the raw rows with its own code and tracing the operator's money), and a synthesis agent that did not
produce its report. A second pass (3 more Opus agents on the cached results, Oct 11 02:50-03:50 UTC) wrote `report/REPORT_owner.md`, a critic
checked it and HANDOFF 16.12 against the raw data and the engine's code (`report/CRITIQUE.md`: 14 corrections, 10 omissions, all applied to
16.12), and `report/REPORT_final.md` merged them; the second pass also read the chain to block 85,513,808 (`report/work/`, `report/merge/`;
the two large event dumps were not kept). `REPORT.md` is the first run's result as returned: the census summary, the ranked list, and the
five skeptics' full verdicts (identity, recomputed numbers, strongest objection, proposed live test). The summary for the owner is HANDOFF
16.12.

## Layout

- `census/`: `README.md` (what was fetched, counts, the file formats, `load.py`), `code/` (`fetch.py` stages, `build.py`), the small outputs
  (`summary*.json`, `families.json`, `loose_families.json`, `code_families.json`, `to_families.json`, `blocks*.json`, `other_dex.json`). Not
  copied (937 MB in the session's scratch, gone with the container): `cache/` (raw RPC answers), `pools.jsonl`, `events.jsonl`, `txs.jsonl`,
  `dex_pairs.jsonl`, `bonding_creates.jsonl`, `v4_other_pools.jsonl`. `code/fetch.py` rebuilds them from the RPC (about 20 minutes, 1,800 POSTs).
- `analyse_N/`: each analyst's scripts and result JSON (`results.json` or `results_final.json`, `calib*`, `validate*`), 29 groups.
- `skeptic_*/`: the five skeptics' scripts (`s1`-`s14`, `b*`, `c*`, `d*`) and results (`reaction.json`, `replay.json`, `fresh_summary.json`,
  `money.json`, `hops.json`, `minout.json`, `balances_now.json`, ...). JSON files over 300 KB were not copied.
- `report/`: the synthesis agent's scratch (no report).

## Window and counts

48 hours to 2026-10-10 18:20:47 UTC (blocks 83,520,210-85,203,897; 1,683,688 blocks at 0.1026 s). 11,889 PoolManager `Initialize` logs,
6,865 of them ETH pairs (currency0 = 0); every pool's events to launch + 3,000 blocks (about 5 minutes) are complete. 1,644 strict launch
families (launch target or code hash, selector, calldata length, fee, tick spacing, hooks), 104 with 5 or more launches (5,069 pools), 175
with 3 or more. Known: volume bot v2.433 1,843 pools, the bot's other sizes 1,436, operator A 77, none 3,509. Other DEXes in the window, not
analysed for the edge: two V2 factories (3,753 and 2,986 pairs, mostly WETH), one V3 factory (645 pools), the bonding-curve factory
`0x7ed598bc` (4,693 creates), a dozen small ones. 153 families were analysed; 7 were flagged; 5 distinct ones were judged (the fee 500/ts 10
entry is the small-pot family's second fee tier, judged with it).

## Verdicts (the skeptics'; the detail and the numbers are in REPORT.md)

| family (strict key) | launches / 48 h | skeptic's verdict | one line |
|---|---|---|---|
| hooked launcher, code hash `f07d1c53`, `e1e75b94`, 5,572 B, fee 2500/ts 25 | 102 (one 23-minute burst) | not a candidate (medium) | a one-off: 48 ETH moved from one buyer wallet into 100 fresh wallets through throwaway tokens; buy at +15, pull at +30, supply burnt; minOut 0.95 x quote, room 0.027-0.039 ETH; no recurrence, the hook unverified. Watch only. |
| volume bot v3.0: POSM `ac9650d8`, 1,444 B, exactly 3.0 ETH, fee 10000/ts 200 (and v5.0: 5.0 ETH) | 889 (444 a day) + 434 v5.0 (217 a day); still launching Oct 11 03:00 | **candidate, conditional (medium)** | the bot's own second line, same router `0x1cbaf24d`, buy at +6..+10 (92%), minOut 0.95 x the launch quote; front replay at 0.0058 ETH +6.0% mean, 99.2% win, $0.90 a trade, ~$400 a day (235 fresh pools +6.2%); v5.0 +1.75%, ~$57 a day. Trap pull at bot+3 after an outsider. Since 01:57 UTC Oct 11 wallet `0x8cf143dd` fronts it (85 of 97 launches) and sells into the bot's buy; the pull answers at bot+3. The engine needs a front-only fee bound first (`FEE_MAX_PPM` 9999 rejects fee 10000). |
| operator C-1: POSM `ac9650d8`, 2,276 B, value 0, fee 100/ts 1; crowd router `0xd6d35b56` (1,049+ wallets) | 245 (124 a day with one 92-launch slice; ~84-89 a day otherwise) | **candidate, different trade (medium)** | a self-funded wash crowd (creators -> multisend `0xf341c935` -> next launcher -> hub `0xbae53801` -> router, 76 ETH in the router); the edge is a 50-block ride after the router's first buy: +11.5% mean, +5.7% median, 69% win, 2.4% pulled, $1.73 a trade, about $90-127 a day (27 fresh rides +8.1%). Not a front; needs a new entry type. |
| operator C-2: PM `initialize` 196 B fee 500/ts 1, then a POSM 1,380 B mint ~41 blocks later; routers `0x628bd69e` etc. | 192 | not a candidate (high) | a trap: 24 of 25 outsider buys of 1e-4 ETH or more were followed by a pull within 166 blocks, 5 of them exactly 4 blocks later; ride EV -96% with the reaction. Do not trade. |
| small pot: POSM `ac9650d8`, 1,444 B, 1.5-2.5 ETH, fee 100/ts 1 or 500/ts 10; a dispatcher funds 10 fresh crowd wallets | 22 (339 since Sep 11, ~11 a day in sessions) | not a candidate (high) | operator A's dispatcher design with its own 2.5 ETH pot; the no-reaction replay is +50-60%, but the operator aborts (pulls with no crowd) on early holders of 0.002 ETH or more: wallet `0x578e7a8e`'s 24 probes at 0.005 ETH on Oct 5-6 were tolerated for 10 pools, then 10 of 14 aborted. Negative at $15. |
