# research/session_oct9_10: the Oct 9-10 research, copied from the session's scratch directory

Every script and every result file under 1.5 MB (caches, raw block dumps and pickles were not copied; the scripts re-fetch them from
the public RPC; the review agents' directories keep their scripts and short text outputs only). `docs/HANDOFF.md` section 6 says what
each directory found. Two absolute paths appear in the scripts and must be edited before running them:
`/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad` is now this directory, and `/home/user/v2pons` is the
repository root. `chain.py` here is the RPC helper every script imports (rpc, batch, logs, block_at, the PoolManager and event topics).

| directory | what (handoff section) |
|---|---|
| `.` (this directory) | Oct 9 paper and probes: the Oct 8-9 night, the seat, the evening pulls, the crowd's funding, fingerprint scans (6.12) |
| `money/`, `origins/`, `ops/`, `ops2/` | operator A's money loop, pots, origins, launcher birth and copies (6.4) |
| `third/` | a third launch system (a bonding-curve factory, first launch Sep 21): its creators, relayer and first holders; parked (6.4, 12.6) |
| `others/` | the census of every v4 ETH pool Oct 8-9, 625 launch families, the follow trade priced on each (6.5) |
| `vbot/` | the volume bot's families, decoder, reaction census, hold-30 replay (6.6) |
| `explore/` (+ `adv/`, `chk/`, `v5/`) | the 33,984-rule search on 24 families; the front rule's exact replay and checks (6.7, 6.8) |
| `fp/`, `fpv/` | the v2.433 fingerprint day by day, Sep 10 - Oct 10 (6.9) |
| `dry1/` (+ `skeptic/`) | the front dry run checked against the chain; the 435-pool census of the 24 h before; the live audit (6.10, 6.11) |
| `yday/` | the exact follow and seat pricers on Oct 8's launches (6.2) |
| `protect/` | the follow exit variants against a faster operator (6.3) |
| `review*/`, `verify*/`, `vfy_*/`, `rv*/`, `vdstop*/`, `vlate/`, `vpnl/`, `score_mix/`, `rt/`, `repro/`, `tests/`, `chk/` | the independent review agents' reproductions for releases 0.6-0.9 (6.1); scripts and notes only |

## Scripts by directory (the first line of each docstring)

### `.` (56 files)

- `all15.py`
- `blocks.py`
- `bt.py`
- `burst.py`
- `chain.py`
- `crowd.py`
- `crowdmin.py`
- `day.py`: hours by interpolation
- `dry1.py`
- `evening.py`
- `exits.py`
- `find.py`
- `fp_d10_30.py`
- `fp_d2_9.py`
- `fp_d2_9_all.py`
- `fp_d2_9_an.py`: senders of family
- `fp_d2_9_v2.py`: (1) logs, fresh, with a half-split completeness check per chunk
- `fund.py`
- `fund2.py`
- `fund3.py`
- `fund4.py`
- `liq.py`
- `moved.py`
- `newlaunch.py`
- `newpaper.py`
- `newtrades.py`
- `now.py`
- `now2.py`
- `overnight.py`
- `overnight_paper.py`
- `pred.py`
- `quiet.py`: 1. launches through the operator's launcher since 14:45
- `replay.py`: Replay the real blocks around the eight live trades through the release 0.3 engine in DRY_RUN, without our own transactions: what would it have done?
- `replay_seat.py`
- `res_c2.py`: results.py: the flip engine's results in one screen. The engine's state (live or dry run, halted or not), the launches it saw, every trade with its re
- `reverts.py`
- `scen.py`: A: shared daily stop: a front pull at FRONT_STAKE 0.006 stops follow
- `seat.py`: $3 at the head of block B; exit_rule(sw_after) -> landing block; -100% if the pull lands first
- `seat2.py`
- `tick.py`: non-boundary prices: off-by-one only within float eps of a boundary
- `today3.py`
- `today4.py`
- `today5.py`
- `tp_bug.py`
- `tp_bug2.py`
- `tp_calc.py`: ETH depth: virtual ETH reserve = L*Q96/sp
- `trades.py`
- `where.py`: the burst signature on any pool, whatever the launch call: two or more real buys by brand-new wallets in one block, within 20 blocks of the launch
- `why.py`: find the reverted txs again by scanning
- `why2.py`

### `dry1` (8 files)

- `fetch.py`: Every v2.433 family launch from FROM to (head - 300): Initialize logs on the PoolManager, the launch tx filter (to the PositionManager, 1,444 bytes, 2
- `final.py`
- `replay.py`: Exact replay of the release-0.9 'front' rule on every v2.433 launch in data.pkl (fetch.py), against the chain. Engine (flip_engine 0.9, front): - arme
- `sens.py`: Sensitivity only (not from this window): if the operator answers our buy like the census outsiders >= 0.0002 ETH (25 of 26 pulled within 15 blocks; la

### `dry1/skeptic` (14 files)

- `ana_s.py`: skeptic replay: sequential integer simulation of each family pool with our 0.0012 ETH buy inserted (own code).
- `census_ana.py`: pre-bot buys
- `census_dig.py`: approximate time: window start block 84855917 = 08:24:24; 0.1035 s/block
- `census_replay.py`: no-reaction replay of the 0.9 front rules on every v2.433 family pool of the 24 h before the window + the window (own code)
- `census_s.py`: broader census (own code): v2.433 family launches over the 24 h before the dry-run window plus the window; pull offsets; buys before the bot's first b
- `fetch_s.py`: skeptic fetch: launches of the v2.433 family from the dry-run start to head; Swap+ModifyLiquidity logs of their pools; blocks around them.
- `fetch_tx.py`
- `funder.py`
- `funder2.py`
- `react_s.py`: operator reaction (own code): every non-bot buy >= 0.0002 ETH before the pull, in the 24 h census + the window; lag to the pull

### `explore` (31 files)

- `after.py`: Do the candidate families keep launching after the census window? Initialize logs (currency0 = ETH) from the window end to the head, their launch txs;
- `depth.py`
- `detail.py`: Per-trade detail of one rule on one pool: why (tp/deadline/pulled), send offset, cheap-pricer ret (as sim.py) and an exact replay ret: our buy inserte
- `fams.py`: Family definitions (launch-time observable fields only) shared by the analysis scripts.
- `fwd_eval.py`: Forward test: the rules chosen on the first half (rules.json, 'mean' and 'tstat'), frozen, on launches after the census window. -> fwd.json
- `fwd_fetch.py`: Forward data: candidate-family pools launched after the census window (b0 > 84238619) whose [b0, b0+3000] is complete; their Swap + ModifyLiquidity lo
- `getters.py`
- `minout.py`
- `outsiders.py`
- `overview.py`
- `overview2.py`
- `overview3.py`
- `peek.py`
- `prep.py`: Compact per-pool dataset from others/cache_plogs.pkl + cache_inits.pkl + census.jsonl -> explore/pools.pkl per pool: b0, fee, ts, hooks, sp0, tick0, s
- `profile.py`
- `realism.py`
- `report.py`: Full survivor test on the rules chosen in rules.json (both selection criteria), with per-trade detail and the exact replay. Writes report.json.
- `rules.py`: Per family x stake: pick the best rule on the first half (by launch time), report it on the second half and per 6-hour slice. rule = (entry e: launch+
- `sim.py`: Rule grid simulator (cheap single-range pricer, same conventions as others/analyze.py, with the task's timing): entry e < 39 : fire at F = b0 + K (K =
- `summary.py`: Robustness of the chosen rules: neighbourhood on the test half, slices, sub-families, canonical rules per family, negative results. -> summary.json
- `taxcheck.py`
- `tokcode.py`
- `ts.py`
- `who.py`

### `explore/adv` (19 files)

- `activity.py`: Family launches per hour from the census start to the chain head (census pools.pkl + Initialize logs after the census window).
- `advreplay.py`: Exact feed replay of the PM1444 v2.433 front-run rule (fire at launch + K, TP on the first feed buy that prices the sell >= TP after gas, else send at
- `armlag.py`: Expected return per launch if the engine arms from the launch RECEIPT (fires when the receipt arrives: feed blocks elapsed, from the live probe yday/s
- `census.py`: by hour: first-big-buy offset and competitor presence
- `early.py`
- `fetch.py`: Adversarial check of PM1444 v2.433: raw chain data for an exact feed replay on a sample of pools. Pools: 12 in-window (pools.pkl, stratified over time
- `fingerprint.py`: Launch fingerprint: decode the multicall of the sampled launch txs (PoolKey from calldata alone), token bytecode hash, and how many blocks before the 
- `look.py`
- `minout.py`
- `peek.py`
- `popreplay.py`: Population replay (logs only) of the v2.433 front-run on every family pool: 531 in-window (pools.pkl) + 102 forward (fwd_pools.pkl). Same engine/trade
- `quote.py`: Which pool state does the volume bot's minOut come from? minOut = floor(0.99 * quote)?; compare with buy_out_int at the state after each earlier swap 
- `react.py`: Pull risk and the operator's reaction to outsiders on the v2.433 family (logs; 531 in-window + 102 forward pools). outsider swap = a buy >= 1e-5 ETH w
- `react2.py`
- `who.py`: feed view on the 24 fetched pools: every tx touching the token in +0..+45, by (to, sel, from-class)

### `explore/chk` (17 files)

- `early_pulls.py`
- `fetch_replay.py`: Data for the exact feed replay of the v2.433 rule: 12 census pools + 8 forward pools + the newest launches (Initialize logs to the head). Per pool: fu
- `look.py`
- `minout2.py`: v2.433: the volume bot's router buys (c1120e3d): minOut (word 4) vs the tokens it got, and vs the exact quote at each earlier state: which state did i
- `prebuy.py`: v2.433 census: buys by anyone other than the volume bot, the deployer and the launch dust trio BEFORE the bot's first buy; what followed (the bot's fi
- `quotemodel.py`: Which earlier buys does the volume bot's first-buy quote include? Implied net ETH bought before its quote = (1/s_q - 1/s_0) L, from minOut = 0.99 x bu
- `quotestate.py`
- `react_all.py`: Outsider-buy reaction in the three PM1444 families: pulls within 15 blocks after an outsider's first buy in a pool (outsiders other than the launch du
- `react_base.py`: v2.433: outsider buys (not the volume bot, not the deployer) by wallet; pull within 1..15 blocks after the buy vs the base rate of a pull in the same 
- `react_ev.py`: Expected return of the v2.433 rule if the operator treats our buy like the other outsiders' buys >= 0.0002 ETH (25 of 26 pulled within 15 blocks; lag 
- `replay.py`: Exact feed replay of the v2.433 rule (launch+2, TP 5%, H 19) on replay_data.pkl, adapted from yday/follow.py. Engine model (flip_engine 0.8 logic, wit
- `replay_k.py`: replay.py's exact feed replay at other fire blocks (K = 3..6, TP 5% and 1%), and the cheap pricer (detail.detail) on the same pools.
- `txform.py`: example bot buy

### `explore/v5` (15 files)

- `bound.py`: Upper bound given the operator's reaction: buy at B (after the other swaps of B), sell at the head of the block right after the FIRST operator buy beh
- `fetch.py`: Adversarial check of PM1444 v5.0 (fee 1%, ts 200, 5.0 ETH): raw chain data for an exact feed replay. Pools: 14 in-window (pools.pkl, stratified over t
- `lags.py`: reaction lags (blocks from a non-operator buy > 2e-5 ETH to the 100% pull) in the v5.0 census -> v5/lags.json
- `look.py`: per pool swap timings
- `outs.py`: pools with a non-UR buy or odd-size buy before block 70
- `path.py`: also vs launch price
- `react.py`: base: for pools without non-UR buys, pull hazard in a random 30-block window at similar offsets
- `react2.py`: base hazard: per-block pull probability for pools at the same offsets with no outsider before
- `react3.py`: Does the full liquidity get removed?
- `react_fwd.py`
- `replay.py`: Exact feed replay of the PM1444 v5.0 rule (launch+3, TP 5%, H 60) on v5/cache.pkl (22 pools: 13 in-window, 5 forward, 4 fresh). Engine/trade logic = e
- `who.py`

### `fp` (23 files)

- `d10_30_days.py`
- `d10_30_final.py`
- `d10_30_logs.py`
- `d10_30_peek.py`
- `d10_30_tx.py`
- `oct10_check.py`: re-scan in 25k chunks to cross-check counts
- `run_oct10.py`: dedupe
- `run_recent.py`

### `fpv` (8 files)

- `cachechk.py`: tx caches
- `days.py`: verify UTC day labels of all 3491 family rows in the four agent files from fresh block headers
- `derive.py`: dedupe check
- `scan.py`
- `scan_an.py`: compare to agent files
- `spot.py`

### `money` (29 files)

- `back.py`: incoming value transfers to x, scanning back from block b in 200-block chunks
- `collector.py`
- `copies.py`
- `deployers.py`
- `eras.py`: sample launches across the launcher's history: funding before (sweep/dispatcher signature?) and payout after the pull
- `fullscan.py`: every block in [a, b]: all plain transactions (no calldata) with value > 0, plus every tx from/to a crowd-A wallet; streamed to a jsonl
- `launches_now.py`: every ETH pool launched through the original launcher (or call 0x2fcb9108) in [a, b], with its deployer and pull
- `loop.py`: the operator's money loop from the plain transfers: sweeps (many in -> one ~7 ETH out), dispatchers (one ~7 ETH in -> many out), which launch each dis
- `signature.py`: the loop fingerprint over every plain transfer collected so far: SWEEPS (fresh wallet: >= 15 transfers in within 60 blocks, then one transfer out at n
- `speed.py`
- `step1.py`: the three 7-ETH recipients from today's pulls, and the extra source of 0xaee54a9f
- `tr.py`: block-scan tracer: every plain transaction to/from a set of addresses in a block window (no archive, no trace API)
- `windows.py`: for every launch since 09:00: the 450 blocks before it (sweep -> dispatcher -> this deployer) and the 450 after its pull (deployer -> sweep); plain tr

### `ops` (35 files)

- `b_launches.py`: Per B launch: launch/pull tx details, swaps by group (A, B, fresh, outsider, us, ...), ETH in/out before the pull, after.
- `b_list.py`: Reproduce crowd families A/B from load_all + classify; list B wallets, the B launches, per-launch group flows.
- `bcurve.py`: Token creations on the bonding-curve factory 0xe33e9e47 and the address lists the new curves emit at creation (topic 0xe4b7e48f).
- `bcurve2.py`: the listing event: topic0 of curve log in the f3d9 creation
- `bcx.py`: Helpers over the shared block cache (lch/bc.py): sent/received txs of an address in a block range.
- `bprof.py`: Log-based profile of wallets: every ERC-20/721 Transfer to/from it and Approval by it in [START, head]; the txs behind them. Usage: bprof.py START w..
- `code.py`
- `deployers.py`: B-launch deployers: funding (scan back from the launch for a plain transfer to it / input naming it) and every tx they sent after the pull.
- `disasm.py`
- `fpcmp.py`: Compare A vs B tx fingerprints (all keys of fp), buy timing after launch, sizes, sell behaviour, via contract.
- `hop.py`: Funding of a wallet: scan back from block B for a value tx to it (or input naming it). Usage: hop.py w B [maxback]
- `lchlogs.py`: try a single big query first
- `lchtx.py`
- `lib.py`: full blocks lo..hi-1 (splits a batch whose response is too large)
- `lists.py`: All bonding-curve 'listing' events (topic 0xe4b7e48f..., topic1 = an address) naming any A or B crowd wallet, Oct 7 -> head; per curve: which A/B wall
- `mlogs.py`: Batched multi-address log scan: Transfer to/from and Approval by any address in the list, [START, END] in 30k chunks. Usage: mlogs.py START END out.js
- `oct9b.py`: Oct 9 B launches 09:24 (0x758c3c5f) and 10:48 (0x2a928e99): deployer funding back 3 hops; deployer's txs after the pull, and the next hop.
- `scan.py`: Full-block scanner: for blocks [a, b) writes chunk files idx/<start>.json.gz (chunks of 5000 blocks) with P: every plain ETH transfer (value>0, input 
- `sets.py`: A-system and B-system address sets from: crowd lists, bonding-curve list creators, loop traces (lch), B deployers/funders.
- `speed.py`
- `speed2.py`

### `ops/lch` (63 files)

- `alllaunchers.py`: Every contract that ever emitted the launcher's Launched event topic 0x03f29fb2... (original, copies, any other deployment of the same code).
- `alllaunchers2.py`: Every contract other than the original that emitted the launcher's event topic, scanned newest-first in 250k-block steps (progress printed).
- `bc.py`: Compact block cache + scanners. Cache: bc/<c>.json for 1000-block chunks (legacy) or bc/q<c>.json for 250-block chunks {bn: [ts, [[hash, from, to, val
- `creator.py`: Launcher 0x3194e326 = CREATE(0x3b11cafa..., nonce 0). Find that deploy tx and the creator's funding (scan backwards from the first launch).
- `decode.py`: decode launcher launch(0x2fcb9108) calldata
- `depfund.py`: For a launcher deployer: its funding tx, the funder's fan-out (families), the funder's own funding (consolidation) and that one's inputs. Usage: depfu
- `follow.py`: Follow ETH forward through single-output hops until it fans out (a distributor) or stops. Usage: follow.py addr start_block maxhops [maxfwd]
- `grepc.py`: grep the local block cache for txs touching addresses. Usage: grepc.py addr [addr...]
- `hops.py`: Follow a chain of funders backwards: for addr, find most recent incoming value tx before block; repeat while the funder's tx nonce <= maxn. Usage: hop
- `hops2.py`: Backward funding chain with all txs of each wallet listed in a window: for addr, list incoming value txs (scan back up to maxback from `before`, stop 
- `launches.py`: List every launch (orig + copy) Oct 8 00:00 -> Oct 9 ~12:06 with family (A/B/copy/fresh/no_crowd_buy, same rule as protect/measure.py), deployer, laun
- `loop.py`: Walk a rolling capital loop forward: at each wallet take its first plain ETH transfer > MIN (the capital), log fan-outs (distributor -> creator + crow
- `loopback.py`: Walk a capital loop BACKWARD: at each wallet, list incoming value txs (scan back from `before`, keep 150 blocks past the first hit), tag senders by fa
- `patch1.py`: value>0 txs to addr before block `before`, scanning backwards; after the first hit look only `extra` blocks further back
- `patch2.py`
- `patch3.py`
- `patch4.py`: fetch blocks by number; items failing in a batch (e.g. 'response too large') are retried in smaller batches
- `population.py`: Every launch ever made through launcher 0x3194e326 (7,485 Launched events, block 19.37M = 2026-07-25 -> now): who sent them, nonce, recipient, metadat
- `show.py`
- `showback.py`
- `showloop.py`
- `sim.py`: Simulate a launch on the original launcher and on a copy, at latest, from a random address (eth_call with a balance state override).
- `timeline.py`
- `trace.py`: Money graph around launches: deployer funding back 3 hops, pull proceeds forward 2 hops. Block scans via bc.py cache. Usage: trace.py <pid-prefix> [..
- `wtx.py`: All txs from/to the given wallets in [a, b] (fetching blocks as needed). Usage: wtx.py a b addr [addr...]

### `ops/lch/tr` (26 files)


### `ops/lch/web` (3 files)


### `ops2` (66 files)

- `agap.py`: crowd A (32 wallets): last tx sent before 83385500 and first tx sent at/after 83647500, over every cached block (no RPC); nonce difference - 1 = numbe
- `anonce.py`: nonce accounting for crowd-A wallets (incl. 0x5861, 0x20d811c8) and crowd-B wallets across the copy-loop period, cache only: last tx sent before 83320
- `back2.py`: backward money trace through the shared block cache: hop to the largest incoming plain transfer; fetches missing 250-block chunks politely (gentle_pos
- `bpot.py`: B-pot (4.86 ETH) dispatchers and sweeps in the local plain-transfer windows (money/part*.jsonl + win.jsonl): inputs, outputs, labels.
- `bytecode.py`: Launcher 0x3194e326 runtime: section boundaries, selectors, access-control opcodes in the launcher's own code (bytes 0..3607), revert strings; diff vs
- `copies_create.py`: For every one-shot launcher copy (other_launcher_logs.json: 1,784 emitters of the Launched topic, blocks 67.9M-83.48M): is the copy address = CREATE(r
- `copyset.py`: copy loop, blocks 83396250-83518499 (cache only, run after the full scan): every wallet the collector paid or was paid by, and their own plain-transfe
- `creation.py`: Verify launcher creation tx + funding hops (by tx hash), deployer-chain nonces at latest, and code hashes of the launcher and sample copies.
- `cross.py`: Over every cached block (ops/lch/bc + money/blocks.pkl): plain ETH transfers between A-side and B-side addresses, and third parties that exchange plai
- `dep4cd.py`: cache-wide (no RPC): deposits into 0x4cd00e38 (selector 0x49290c1c) on Oct 8-9 by nonce-0 senders, and who funded each sender (the plain transfer into
- `fill.py`: fill the shared block cache for [lo, hi] chunk by chunk (one process, gentle_post: <=50 per batch, backoff on 429/errors)
- `firstpull.py`: What happened to the LP of the very first launch (by the launcher's own deployer 0x3b11cafa)? ModifyLiquidity events of its pool via eth_getLogs.
- `fresh.py`: the 'fresh' family pot (Oct 8 11:45-13:21), cache only: for each fresh deployer, funding chain back to a hub (a wallet with >=8 inputs) and the hub's 
- `fwd.py`: first outgoing tx(s) of an address scanning forward chunk by chunk from block a (max n blocks). usage: fwd.py addr a n [want]
- `fwd2.py`: forward money trace, cache only: from addr after block b, take its next outgoing plain transfer(s); follow the largest (> min_eth); print hub fan-outs
- `gapscan.py`: scan backwards from HI to LO (chunks of 250 via bc cache, gentle RPC) for txs touching B wallets, 0xb5d3df36, 0xa57fb285; stop 2 chunks after the firs
- `grepc.py`: cache-wide (no RPC): every cached tx from/to the given addresses
- `hashes.py`: full tx hashes (from the block cache) for the money links cited in the conclusion
- `labels.py`: label map: crowd A (32), crowd B (31), main-loop dispatchers/sweeps (Oct 9 scans), fingerprint families (b_list fam), key addresses
- `latest.py`: latest nonce (eth_getTransactionCount 'latest') for the collector and every wallet that sent to it after the last copy pull, compared with the nonce o
- `lib2.py`: ops2 helpers: the shared bc block cache (ops/lch/bc) with a gentler RPC post (batches <= 50, long backoff on 429/errors).
- `logsof.py`: all logs naming an address in topics 1-3 over [a, b]; usage: logsof.py addr a b
- `loop_ro.py`: the operator's money loop from the plain transfers: sweeps (many in -> one ~7 ETH out), dispatchers (one ~7 ETH in -> many out), which launch each dis
- `mix.py`: cache-wide (no RPC) mixing test between the pots: every cached block file under ops/lch/bc. Sets: crowd A (32), crowd B (31), copy-loop wallets (colle
- `mix4.py`: cache-wide (no RPC) money-mixing test between four pots. A: crowd A + A hubs (Oct 9) + Oct 8 A hubs/capital; B: crowd B + B hubs + Oct 8 B hubs/capita
- `pop.py`: Population stats of all 7,485 launch txs on launcher 0x3194e326: recipient vs sender, metadata host, 'auto' prefix, event topics.
- `potnonce.py`: for the Oct 8 A-pot and B-pot wallets: last outgoing tx seen anywhere in the block cache vs the latest nonce now; and every cached tx they sent to the
- `potnonce9.py`: Oct 9 hubs (pots.json: A_7.01 and B_4.86 dispatchers/sweeps): last sent tx seen in the block caches (bc + money/blocks.pkl + money plain-transfer logs
- `potsets.py`: Oct 8 pot wallets from the earlier loop traces (full addresses): A pot 11:19-11:48 (loop_A.jsonl) + the 21:57 restart hubs, B pot 11:11-11:54 (loop_B2
- `q1.py`: 0x3fc5b8b8 in every cached block range (no RPC): all txs from/to it
- `q2.py`
- `q3.py`
- `q4.py`
- `q5.py`
- `qback_ops2.py`: fetch chunks backward from hi until an incoming plain transfer to addr appears (one process, gentle). usage: qback_ops2.py addr hi lo
- `qfill_ops2.py`: fill the shared block cache for [lo, hi] chunk by chunk (one process, gentle_post: <=50 per batch, backoff on 429/errors)
- `receipts.py`: Every log in a few launch receipts, every address named, every Transfer decoded: is any value routed to a fixed (fee) address?
- `sim.py`: eth_call at latest: launch(...) on the original launcher from a fresh random address, with calldata of the most recent real launch in launcher_txs.jso
- `sim_copy.py`: Same permission test on one-shot copy 0xd1cc99aa33.. (code hash 2793923d): new salt, random sender + random recipient, 1000 ETH override.
- `uri.py`: token metadata URI (launch calldata string s3) and gas parameters for sample launches of each pot: copy launches (per-launch launcher copies), B launc
- `who.py`: all cached txs touching addresses in [lo, hi] (cache only, no RPC). usage: who.py lo hi addr...

### `ops2/bcrowd` (13 files)

- `bpot.py`: B-pot (4.86 ETH) dispatchers and sweeps in the local plain-transfer windows (money/part*.jsonl + win.jsonl): inputs, outputs, labels.
- `bpothist.py`: B pot history over all cached blocks (bc cache, local only): every address that sends plain ETH to >= 15 B wallets (dispatcher) or receives from >= 15
- `bw.py`: plain ETH transfers of 6 B wallets in every cached block today (cache only, no RPC); counterparty roles from the B loop.
- `cross.py`: Over every cached block (ops/lch/bc + money/blocks.pkl): plain ETH transfers between A-side and B-side addresses, and third parties that exchange plai
- `fwd.py`: first outgoing tx(s) of an address scanning forward chunk by chunk from block a (max n blocks). usage: fwd.py addr a n [want]
- `gapscan.py`: scan backwards from HI to LO (chunks of 250 via bc cache, gentle RPC) for txs touching B wallets, 0xb5d3df36, 0xa57fb285; stop 2 chunks after the firs
- `libb.py`: ops2 helpers: the shared bc block cache (ops/lch/bc) with a gentler RPC post (batches <= 50, long backoff on 429/errors).
- `logsof.py`: all logs naming an address in topics 1-3 over [a, b]; usage: logsof.py addr a b
- `loop_ro.py`: the operator's money loop from the plain transfers: sweeps (many in -> one ~7 ETH out), dispatchers (one ~7 ETH in -> many out), which launch each dis

### `ops2/verify3` (15 files)

- `attrib.py`: cache-only attribution of every launch Oct 8 05:00 -> Oct 9 11:20 to a pot by the deployer's funder (A dispatcher refills crowd A, B refills crowd B, 
- `base.py`: Base (8453) public RPC helper for following Relay cash-out recipients (historical nonce binary search).
- `basefollow.py`: follow each Relay cash-out recipient on Base: find each outgoing tx by binary search on historical nonce, record to/value; up to 2 hops.
- `cachescan.py`: no-RPC scan of every cached block (ops/lch/bc + money/blocks.pkl) for plain/any value transfers touching a target set; writes cachescan.json
- `ffund.py`: find who funded F-seed deployer 0x8a10f14e before its launch (blk 81255830): gentle backward block scan, stop when found
- `links.py`: Adversarial re-fetch of key money links by tx hash: from, to, value, nonce, block, status (receipt).
- `vlib.py`: verify3 helpers: read the shared bc cache (no RPC) and a gentle block fetch for small uncached ranges.

### `ops2/verify3/relay` (21 files)


### `origins` (129 files)

- `act2.py`: Log activity of a few wallets: any log with the wallet in topic1, topic2 or topic3 (ERC20 Transfer/Approval, etc.), 30000-block windows from HI down t
- `activity.py`: When were a wallet set active? ERC20 Transfer logs to (topic2) any wallet of the set, in 30000-block windows, walking back from START. Usage: activity
- `analyze.py`: Rebuild loop A from scanned value>0 txs: dispatchers (>=10 plain outs to crowd), sweeps (>=10 plain ins from crowd), launch wallets (non-crowd recipie
- `baseact.py`: Base public RPC: every tx from/to an address in blocks [a, a+n). Usage: baseact.py addr a n
- `basefwd.py`: Base (8453) public RPC: given a Relay fill tx hash and its recipient, scan forward blocks for the recipient's next tx (where the bridged ETH went). Us
- `fam.py`: Pot wallets of each crowd family (A, B) from the cached plain transfers, and every cross-family plain transfer / shared counterparty.
- `fb.py`: Block fetcher sharing the ops/lch/bc cache format (q<c>.json = 250 blocks {bn: [ts, [[hash, from, to, value, nonce, sel, inputlen, idx]...]]}). Small 
- `fill.py`: Fill the shared 250-block cache (ops/lch/bc) for ranges, one process, with pauses; optional stop-condition: an incoming value tx to ADDR. usage: fill.
- `firstseen.py`: Earliest token activity of each crowd-B (and crowd-A) wallet: ERC20 Transfer logs with topic2 (to) = wallet, 30k-block windows, 10 windows per batched
- `h.py`: h.py addr [lo hi]: value txs from/to addr in the cached index (vt.pkl); prints sender-side nonces.
- `hopback.py`: Who funded a wallet: scan blocks backward from B (shared cache, polite fetcher) for value>0 txs to it, and its own txs, until the first incoming is fo
- `idx.py`: Index of every value>0 tx (plain or call) in the shared block cache ops/lch/bc + all txs sent by crowd A/B wallets. Output vt.pkl: list of (bn, ts, ha
- `olib.py`: block cache + scanning for the origins work. Chunks of 500 blocks stored gzip-json in origins/blk/<start>.json.gz tx tuple: [bn, ts, hash, from, to, v
- `poolbuyers.py`: Who traded in the pool created by a launch tx: Swap logs (PoolManager) for the pid between launch and `until`, tx senders and ETH amounts. Usage: pool
- `potpath.py`: Big (>0.5 ETH) plain transfers touching family-F pot wallets (non-crowd), time-ordered, with F of both ends; marks cache-range boundaries.
- `pullof.py`: pull block(s) of the pool created by a launch tx: Initialize log -> pid -> ModifyLiquidity with negative delta. Usage: pullof.py txhash [span]
- `winscan.py`: Scan block windows (via the shared ops/lch/bc.py block cache) and write every value>0 tx to a jsonl: [bn, ts, hash, from, to, value_wei, nonce, sel]. 

### `origins/base` (3 files)

- `bfund.py`: Base: who funded address X (first block where balance > 0, binary search with historical state), print the funding tx(s).
- `bfwd.py`: Base (chain 8453) forward tracer via public RPC with historical state: for an address, find each outgoing tx (nonce increments) in [lo, hi] by binary 

### `origins/eras` (43 files)

- `B.py`: cached full-block fetch (chunks of 200 blocks, gzip json in origins/eras/blk). row: [bn, ts, hash, from, to, value_wei_str, nonce, type, sel]
- `L.py`: era study helpers: launch table from launcher logs + txs
- `back.py`: follow money backwards: for addr, scan back from block `bn` in 200-block chunks (max `lim` blocks) for value transfers INTO it; follow the largest inb
- `fp.py`: decode launch calldata: words, strings (name/symbol/uri); fingerprint per track
- `nonces.py`: for each traced launch: buy txs (from p1 buys) -> tx sender + nonce (eth_getTransactionByHash, batches of 40). out: nonces.json
- `one.py`: detail one launch: creator funding, buyers' funding + nonces, post-pull flows. usage: one.py <launch block or sender prefix> [pre] [post]
- `p1.py`: phase 1: for every launch, the pull block (first negative ModifyLiquidity on its pid within 200k blocks) and token buyers/sellers (Transfer PM->x / x-
- `p2.py`: cluster launches into loops by shared repeat buyers (crowd wallets)
- `p3.py`
- `p4.py`: daily view: launches, component membership, overlap (max simultaneous open launch->pull intervals)
- `p5.py`: 1) core overlaps between components
- `p6.py`: proper crowd per component: wallets with >=90% of their buys inside the component and present in >=25% of its launches; overlaps
- `p7.py`: per component: daily segments; crowd-A / crowd-B wallets' first/last buy and which components; L006 Sep-11 part
- `scan.py`: scan.py tag a b addr...: every tx touching addrs in [a,b] (cached full blocks)
- `summarize.py`: compile traces.jsonl (+ nonces.json) into samples.json and a printed table
- `t1.py`
- `trace.py`: money trace around one launch, from full-block scans of [bn-PRE, bn+5] and [pull, pull+POST]: creator funding chain (up to 4 hops back), crowd wallets
- `trace_disp.py`: trace_disp.py addr bn: find the wallet that funded addr (scan back up to 1000 blocks), then that funder's full in/out list in [bn-1500, bn+50] (dispat
- `who.py`: who.py addr...: launches each address created or bought in (component, time, value)

### `origins/relay` (4 files)


### `origins/relayB` (6 files)


### `origins/verify` (25 files)

- `bsrc.py`: For Base senders into a collector: find the funding tx (binary search on historical balance, up to 300 blocks back), then ask Relay API (v2 by fill ha
- `btx.py`: Base: fetch txs by hash (from, to, value, nonce, block, time, input head).
- `first_tok.py`: Earliest ERC20 Transfer (to = wallet) and earliest (from = wallet) for a wallet list, by eth_getLogs in windows walking back from END to FLOOR. usage:
- `scan.py`: Scan full Robinhood blocks [a,b] and print txs whose from or to is in the watch set (or all value txs with --all). usage: scan.py a b addr1,addr2,... 
- `tx.py`: Re-fetch Robinhood-chain txs by hash: from, to, value, nonce, block, time, status.

### `others` (15 files)

- `analyze.py`: Census analysis: per pool (census.jsonl) the launch, the gates, the crowd's buys, the pull, and the cheap paper FOLLOW trade from the pool's own Swap 
- `crowd.py`: Crowd fingerprint per family: for a sample of each family's pools, the transactions behind the real buys (>= 0.0002 ETH) in the first 300 blocks: the 
- `crowdtrace.py`: Where else does our operator's crowd buy? (1) the wallets behind the real buys (>= 0.0002 ETH, first 300 blocks) on every original-launcher pool; the 
- `families.py`: Families from census.jsonl: launch contract (address, or the code-size class for per-launch contracts) + selector + calldata length + fee tier + tick 
- `fetch.py`: Census fetch: every v4 ETH pool (Initialize, currency0 = 0) from Oct 8 00:00 UTC to the head; its launch tx; the launch contract's code hash; the pool
- `mintrig.py`: Variant: a larger minimum trigger (the first buy >= MIN after +6, within 150 blocks); hold 2 (engine) or 30; land 1/2.
- `seat1444.py`: PM1444 family (PositionManager multicall, 1,444-byte calldata): a fixed-time entry (our buy at the head of launch + K, no trigger needed) and the sell
- `sigsweep.py`: Signature sweep: the first two real buys of every non-operator pool with >= 2 real buys in its first 300 blocks (not sampled before): calldata length,
- `variants.py`: Exit/entry variants of the paper FOLLOW on the candidate families (same pricing as analyze.py): the hold (the last block the sell may be sent after ou

### `others/ctl` (7 files)

- `ctl_follow.py`: Exact FOLLOW re-pricing (yday/follow.py's price_launch, unchanged: full-block feed replay + Swap/ModifyLiquidity logs) of chosen original-launcher (0x
- `famanalyze.py`: The original-launcher family (94 pools): crowd (fingerprint, wallets, recurring), deployer (nonce, next tx = pull?), reaction (pull after the first ou
- `famfetch.py`: Fetch for the whole original-launcher family (94 pools, Oct 8 00:00 - Oct 9 14:48): the transaction of every real buy (>= 0.0002 ETH into the pool) up
- `live.py`: our relay's swaps since Oct 8 00:00 (cheap getLogs) -> the pools our bot traded live; map to census rows

### `others/verify` (16 files)

- `v1_check.py`: Verifier step 1b: compare the fresh data (fresh.pkl) with the census row and the census cache; re-derive the gates, trigger, pull; re-price FOLLOW (la
- `v1_fresh.py`: Verifier step 1: fresh chain data (not the census caches) for sample pools of each claimed family: the Initialize log, the launch tx, the pool's Swap 
- `v2_price.py`: Verifier step 2: re-price the candidate families with the independent pricer (vprice: sequential exact-input replay, sells by others re-simulated) fro
- `v3_analyze.py`: PM1444 v3.0 sample: bot vs outsider buys, sellers, the pull (who, through what, when, after which outsider buy), the hold-30 trades' exits relative to
- `v3_fetch.py`: Verifier step 3 fetch: for a random sample of PM1444 v3.0 pools (plus every pool the hold-30 paper marks pulled or losing) the transaction behind ever
- `v4_pm2276_burst.py`: PM2276 with the 0.01 ETH minimum trigger: where does our buy land relative to the burst? The burst = the run of buy blocks from the trigger with gaps 
- `v5_reaction.py`: All PM1444 pools (logs only): an outsider buy = a swap paying 0.0002-0.02 ETH (every bot buy in the 181-pool tx sample was >= 0.0247 ETH, every non-bo
- `v6_analyze.py`: Post-census launches (84,238,620 -> head): families, our operator, rates per hour; the engine-rule paper (independent pricer) on every pool with a ful
- `v6_fetch.py`: Verifier step 6 fetch: (a) an independent recount of the census window's Initialize logs (currency0 = 0), in 50,000-block chunks; (b) every v4 ETH poo
- `v7_fetch.py`: Verifier step 7 fetch: (a) timestamps of the post-census original-launcher launches and the first 6 real-buy txs on each (crowd signature); (b) our re
- `vprice.py`: Independent paper pricer for the verifier (does not use v4math or the census's 1/sqrtP shortcut). Replays the pool's logged swaps in order (block, log

### `protect` (75 files)

- `bynonce.py`: Find the transaction a wallet sent with a given nonce: binary search on eth_getTransactionCount(w, block), then the block's txs.
- `classify.py`: Shared classification: crowd = the operator crowd's transaction fingerprint (UR execute, 1124 bytes, deadline 2^256-1, type 2, priority 0.02 gwei, gas
- `exits_bt.py`: Exit timing against a faster operator: Oct 8's original-launcher launches (follow entry, flip_engine 0.8), priced by the verified follow pricer (prote
- `exits_cadence.py`: where the crowd's buys after the trigger land (feed buys >= 0.0002 ETH, offsets from the trigger block T), on the 46 traded Oct 8 original-launcher la
- `exits_live9.py`: today's (Oct 9) live relay trades: buy block, sell block, pull block, from the chain
- `exits_live9b.py`: today's relay trades: the swaps on each pool from the first real buy to our sell (blocks relative to the first >= 0.0002 ETH buy)
- `exits_stakes.py`: exits_bt's pricer at the larger stakes: V0 (current exit) with the buy at T+1, V1 (sell sent at B+1) with the buy at T+1 and T+2 (the delayed entry), 
- `exits_summary.py`: compact tables from exits_bt.json (fast landing = as every live sell), and where V0's edge over V1 comes from
- `fetch9.py`: Same as ../yday/fetch.py + fetch_fp.py, for the operator's Oct 9 launches (oct9_pools.json kind orig/copy): the Initialize log, every Swap / ModifyLiq
- `fetch9b.py`: launches9.py + fetch9.py for the operator's launches after oct9_pools.json's last block (84115823) up to the head: writes oct9b_pools.json and react9b
- `follow.py`: Paper-price the FOLLOW entry of flip_engine 0.8 (ENTRY=auto -> follow on launches through the original launcher) on every Oct 8 2026 launch of kind "o
- `follow_money.py`
- `fresh_exit.py`: On the fresh-trigger launches (trigger wallet nonce <= 3) of the Oct 8 paper: the current trade (buy T+1, V0) against the delayed entry (buy T+2, sell
- `ladder_sim.py`: The stake ladder and its warnings replayed on the real sequence: Oct 8's 46 follow launches priced by the verified pricer at every stake (yday/follow_
- `ladder_sim2.py`: ladder_sim.py with the design finally proposed: a one-time RAMP (climb one rung after K clean trades in a row; WATCH resets the count) and, after a WA
- `launches9.py`: Every ETH-paired v4 pool initialised from Oct 9 00:00 UTC (block 83719339) to the head, with its launch tx; kind orig (tx to the original launcher), c
- `live_all.py`: Every relay trade of ours Oct 8 00:00 -> head: buy block, sell block, the trigger (first real >= 0.0002 ETH non-us buy before our buy), the trigger tx
- `load.py`: Uniform loader: every operator launch Oct 8 00:00 -> now (Oct 8 from ../yday/react_data.json + react_fp.json, Oct 9 from react9_data.json). Each pool:
- `load_all.py`: load.load() (Oct 8 00:00 -> Oct 9 11:19) plus react9b_data.json (Oct 9 11:19 -> 12:06, fetch9b.py), same pool records; the crowd classification of cla
- `measure.py`: The operator's reaction, measured on every operator launch Oct 8 00:00 UTC -> now (89 orig + 49 copy; Oct 8 data from ../yday/react_data.json, Oct 9 f
- `opnl.py`: crowd B: fingerprinted wallets that never buy on a launch outside the 7 low-fee long launches
- `precursor.py`: What precedes the pull: for every pull that came <= 60 blocks after a non-crowd real buy (the reactions), every transaction in the blocks from the buy
- `prot_eval.py`: Protections against a pull before our sell: every candidate rule checked against every operator launch Oct 8 00:00 -> Oct 9 12:06 UTC (94 original-lau
- `pulls_feed.py`: Can the engine see each pull in the feed and tie it to its pool? For every pull (first negative ModifyLiquidity) on the 143 operator launches: the pul
- `residual.py`: Residual risk after the protections: an ABRUPT operator speed-up (reaction <= 3 blocks) that no WARN saw coming. Loss = the stake of the first of our 
- `scan_funding.py`: Scan full blocks [a, b] for transactions from / to a wallet or naming it in the input (funding, first tx). Usage: scan_funding.py w a b
- `summary.py`: Summaries over measure.json: reaction lags (first non-crowd buy per launch, all non-crowd buys), by day / hour, the engine's triggers, margins of the 
- `today.py`
- `tokens_origin.py`: For tokens a wallet holds that are not the operator's Oct 8/9 launch tokens: the v4 pool(s) they trade in (Initialize log with the token as currency1 
- `wallet_logs.py`: Every ERC-20 Transfer to / from a wallet and every Approval by it (all contracts), Oct 8 00:00 -> head; which of those tokens are the operator's launc
- `wallet_profile.py`: A wallet's on-chain profile from logs (no archive state on this RPC): every ERC-20 Transfer to/from it and every Approval by it since START; the trans

### `protect/review` (10 files)

- `rv1.py`: Adversarial review 1: fingerprint fields of every buy on the 143 launches, by class; the speck wallet; crowd buys followed by a pull within 0-6.
- `rv2.py`: who was the 1124-byte type-0 UR tx
- `rv3.py`: Independent: every Swap sent by our relay from Oct 8 00:00 to the head (eth_getLogs topic2 = relay), paired into buy/sell per pool; the first negative
- `rv4.py`: Chain re-check: (a) the 16:13 copy-pool outsider buy -> pull lag; (b) the fingerprint of today's trigger txs, read raw from the chain.
- `rv5.py`
- `rv6.py`: If the feed treated ANY non-fingerprint, non-us swap tx naming the token (value 0 included, buys or sells, any size) as an outsider: how often would t
- `rv7.py`
- `rv8.py`: Pre-fire rule with no 60-block limit: any non-fingerprint, non-us, non-dust buy of >= 0.0001 ETH (or value 0, size unknown to the feed) from launch to
- `rv9.py`: residual.py's f re-run with the cooldown the design actually specifies: a canary WARN puts us at the minimum only until 3 CLEAN trades (no reaction) i

### `third` (44 files)

- `back_first.py`: backward scan from the first third-system launch (Sep 21 12:18:27, block 68790933) for funding of: relayer 37bd8ddc, creator 2bea0fb6, the 65 first ho
- `bdis.py`
- `blk3.py`: small block cache for sampling: third/blk/<bn//100>.json; tx = [hash, from, to, value_str, nonce, sel, inputlen]
- `classify.py`: classify launches inside a cached block window: creator funding pattern (dispatcher burst), crowd buys, creator 7702 delegate
- `creators9.py`: Oct 9 launches: creator code -> 7702 delegate; delegate code -> does it embed executor bbd947c3?
- `crosscheck.py`: offline pass over the whole shared bc cache: any tx between third-system set S and loops A/B set P (+ injectors); txs touching relayer/executor by P
- `curvepath.py`: price path of third-system launches: curve buy/sell events (ec36bf57 buy, 8113d738 sell) from launch to dump+50, crowd vs outsiders
- `ex_hist.py`: executor bbd947c3 dump events (a801e276) per 1M-block window, whole history; keep [bn, tx, token]
- `fac_logs.py`: factory 0x7ed598bc create events (8d4aad49). Keep compact [bn, tx, token, curve, creator, d0, d1, d2] for the last NKEEP blocks; for older windows onl
- `lib3.py`
- `links.py`: for executor dumps/sweeps in [lo,hi]: receipt -> collector(s) (wallet 0571d85f events); token -> launch (factory event) -> creator; cache: collector o
- `otherbundles.py`: launches in cached window with >=6 distinct buyers within 100 blocks but no dispatcher burst: who are the buyers, how were they funded (any tx touchin
- `sample.py`: trace one executor dump: token, launch, creator funding (dispatcher burst), dispatcher's funder, buyers, collector onward
- `scan_cache.py`: one pass over cached blocks [lo,hi]: creation txs (created addr), txs of relayer 37bd8ddc / to bbd947c3 / to e33e9e47

### `third/verify` (2 files)

- `v1.py`

### `vbot` (57 files)

- `analyze.py`: Summaries of replay.py output: python3 analyze.py res.pkl [stake]
- `breaker.py`: Pull exposure of the hold-30 follow on every family launch with logs (census 718 + post-census 175), from the pool logs: our buy lands at first real b
- `explore.py`
- `fetch.py`: Raw chain data for the sampled PM1444 v3.0 pools: the launch receipt, every block b0..b0+SCAN with its full transactions, the pool's Swap + ModifyLiqu
- `fetch_blocks.py`: Full blocks (every transaction, with calldata), as the sequencer feed carries them, cached in vbot/blocks/<n // 1000>.pkl: {block: (timestamp, base_fe
- `fetch_launch.py`: Fetch the full launch transaction (with input) of every census pool launched by a call to the v4 PositionManager (0x58daec31...), 3,386 pools; cache v
- `fingerprint.py`: The family fingerprint, level by level, over the census's 5,164 v4 ETH pools (Oct 8 00:00 - Oct 9 14:48 UTC): how many pools each level matches, how m
- `launch_decode.py`: Decode a v4 PositionManager launch (multicall 0xac9650d8 = initializePool + modifyLiquidities) from its calldata alone, as the engine sees it in the s
- `names.py`: name/symbol/codesize of the PM1444 family tokens (all pools in fam.pkl + recent.json) -> names.json
- `newlaunch.py`: Find PM1444 v3.0 launches after the census window (Initialize logs, ETH as currency0, fee 10000, ts 200, no hook; launch tx to the PositionManager, se
- `post_check.py`: Out-of-sample: every PM1444-like launch after the census head (84,238,619) up to now. Fetch the launch txs (input) and their Initialize logs, test the
- `post_feed.py`: Out-of-sample feed check on 16 launches after the census (Oct 9 14:48 - 21:xx UTC): full blocks [b0 - 3, b0 + 100] (vbot/blocks) and the pool logs fro
- `probe1.py`
- `pulls.py`: First liquidity removal (pull) of every PM1444 v3.0 pool, census + new, from ModifyLiquidity logs (chunks of pids); the block time.
- `quotelag.py`: When does the volume bot quote its buy? For each router buy (0x1cbaf24d c1120e3d), word 4 = minOut; tokens/minOut ~ 1/0.95. Find the pool state (after
- `quotelag2.py`: Which pool state does the bot's minOut come from? For each router buy, minOut/(0.95 x quote) at the state after each earlier swap (and the initial sta
- `quotelag3.py`
- `reaction.py`: Does the PM1444 v3.0 deployer pull after an outside buy? (reaction_cache.pkl from reaction_fetch.py; pulls.json for times) Buy classes: BOT = the volu
- `reaction_fetch.py`: Does the v3.0 deployer pull after an OUTSIDE buy? Data: every pool's Swap + ModifyLiquidity logs [b0, b0+1500] (census: cache_plogs; new pools: fetche
- `reaction_fetch_new.py`: The same transactions as reaction_fetch.py, for the post-census pools only (newest first), into reaction_new_tx.pkl (merged by reaction.py).
- `reaction_summary.py`: The deployer's reaction to outside buys, all PM1444 v3.0 pools (reaction.json from reaction.py, run without a filter). An outside buy: not the volume 
- `recent_pulls.py`: Every strict-fingerprint launch after the census (cache_post_launch.pkl, refreshed by post_check.py): its pool's Swap/ModifyLiquidity logs over [b0, b
- `replay.py`: Exact feed-replay pricing of a 'hold and sell into the volume bot's next buy' trade on PM1444 v3.0 pools (fee 1%, tick spacing 200, 3 ETH full-range p
- `replay_window.py`: Replay a contiguous window of full blocks (vbot/blocks) the way the engine reads the feed, with the recognition this family needs: * every transaction
- `report.py`: The report's numbers from replay.py output (res.pkl) and reaction.json: python3 report.py res.pkl -> report.json + text Robust variant: for each (entr
- `sample_feed.py`: Feed-level look at PM1444 v3.0 launches from full blocks (vbot/blocks, as the sequencer feed carries them) joined with the pool's Swap/ModifyLiquidity
- `sells_fixed.py`: Every Universal Router call (24856bc3, 1,060 bytes) carrying a family token in the cached blocks: the fixed byte offsets of the bot's sell layout vs t
- `stale.py`: How stale is the volume bot's quote (its buy's minOut)? For each router buy after the pool's first: r_k = minOut / (0.95 x exact quote at the state af
- `stale2.py`: P(the bot's quote saw a swap that landed L blocks before its buy), from every (bot buy, earlier swap within 25 blocks) pair: the quote state is the la
- `trade_replay.py`: Cross-check of the hold-30 follow on this family with the feed-side recognition only (vbot_feed): arm from the launch calldata in the launch block; th
- `vbot_feed.py`: What the engine needs to recognise and follow the PM1444 v3.0 "volume bot" family from the sequencer feed, from calldata alone: launch_of(to, value, d

### `vbot/go` (2 files)

- `prearm_clock.py`: Does the deployer's reaction clock start at an outsider's buy, or at the bot's first buy? Natural experiment: outsider buys that land BEFORE the bot's

### `vbot/react` (32 files)

- `bot.py`: The volume bot's own schedule in the census pools (txs complete to min(pull, +300)): its 1st/2nd buys (block, size), whether the 2nd comes by +40, its
- `chains.py`: Deployer funding, two hops, from the full-block scan 84431185-84443384: for each family launch in the window, the plain ETH transfers into its deploye
- `common.py`: shared loader for the PM1444-family reaction study: pools (census + recent), their logs, the tx cache
- `extract.py`: Extract the PM1444 families' (v3.0, v5.0, v2.433) census rows and pool logs into vbot/fam.pkl.
- `fetchtx.py`: Fetch the transaction behind every Swap / ModifyLiquidity log of the PM1444 families (v3.0, v5.0, v2.433) in the census windows [launch, launch + 3000
- `fetchtx2.py`: tx behind every Swap log of the recent (post-census) family pools up to min(pull, +600), the pull txs of every pool (census + recent) and the launch t
- `fundcheck.py`: Do the bot's trading wallets get their ETH inside the deployer's router call (0x7422a284, token create)? Latest launches only (state is kept ~6,000 bl
- `ghost.py`: Pulls with no visible outsider swap before them: every tx in [launch, pull] whose calldata mentions the token (or the pool id), with its receipt statu
- `midlife.py`: Pulls beyond the tx-covered window: fetch the txs of every swap in the 25 blocks before each such pull, then classify the pull as REACTIVE (an outside
- `mlall.py`: Every ModifyLiquidity log of every PM1444-family pool (census + recent launches) from its launch to the head -> mlall.pkl {pid: [(bn, li, liqDelta, tx
- `names2.py`: name/symbol of a time-spread sample of PM1444-family tokens (40 per family) -> names2.json
- `prearm.py`: LEAD ONLY (cheap pricer, census pools): buy BEFORE the bot's first buy (land at launch + K) and sell into that first buy (the sell lands L blocks afte
- `pulls.py`: Every pull inside the tx-covered window (census <= +300, recent <= +600): what preceded it within 25 blocks (outsider buys by wallet, bot buys/sells),
- `pulltime.py`: Pull timing: per family, lifetime (launch -> pull) split into REACTIVE (an outsider buy >= 3e-5 ETH, by tx or by a non-Universal-Router swap sender, w
- `react.py`: Outsider buys in the PM1444 families and what followed. A swap is the BOT's if its tx goes to the bot router 0x1cbaf24d or comes from a wallet that ev
- `react2.py`: Reaction detail. Outsider buys AFTER the bot's first buy ('armed'), by size class; for each: pulled within 25 blocks?, lag, the bot's buys/sells betwe
- `recent.py`: Launches since the census head (84238619) to now: every v4 ETH pool Initialize, its launch tx, PM1444 family classification. Writes recent.json (pid, 
- `recentlogs.py`: Swap + ModifyLiquidity logs for the recent (post-census) PM1444-family pools over [launch, launch + 6000] (or head) -> recentlogs.pkl, same tuple shap
- `rpc2.py`: patient JSON-RPC (the public endpoint is shared with sibling jobs and rate limits): retries up to ~15 min, batches <= 50
- `scan.py`: Full-block scan [a, b]: every tx (hash, from, to, value, nonce, selector, calldata length, prio) per block -> vbot/scan_<a>_<b>.pkl.

### `vbot/review` (4 files)

- `r1_reaction.py`: background: pools with no outside buy (non-WL, any size), P(pull in a window)
- `r2_adjusted.py`: a sanity variant: what if the operator ignores 0.0012 ETH more than 0.0001 (reaction only with prob x)? break-even reaction prob
- `r4_prearm.py`: Reviewer check: outsider buys BEFORE the bot's first buy (the 0.9 FRONT entry slot), per family: was the pool pulled, when, relative to the outsider b
- `r5_prearm_lag.py`

### `yday` (41 files)

- `calldata.py`
- `crowd_minout.py`: For follow.json: would the crowd buys our sell profits from (behind our buy, before our sell lands) still go through with our buy ahead of them? Their
- `dustcheck.py`: the code hash of the copy launchers
- `explore.py`
- `explore2.py`
- `explore3.py`: wallets on 2..20 launches with any real buy
- `explore4.py`
- `explore5.py`
- `fetch.py`: Fetch, for every operator launch on Oct 8 (orig + copy, oct8_pools.json) and the Oct 9 00:11 pool we traded: the Initialize log, every Swap / ModifyLi
- `fetch_fp.py`: The fingerprint of every buy transaction (before the pull + 50 blocks) on the operator's launches: tx type, gas limit, priority fee, calldata length, 
- `follow.py`: Paper-price the FOLLOW entry of flip_engine 0.8 (ENTRY=auto -> follow on launches through the original launcher) on every Oct 8 2026 launch of kind "o
- `fp_tab.py`
- `funding.py`: Who funded a wallet: the first block where its balance is non-zero (binary search on historical balance), then the transaction in that block that name
- `probe.py`
- `reaction.py`: How the operator reacts when someone else is in its pool (the paper prices assume it does not react to us). Reads react_data.json (fetch.py: every Swa
- `seat.py`: Paper-price the SEAT entry of flip_engine 0.8 (ENTRY=auto -> seat on a launch through a per-launch launcher copy whose code hash is in SEAT_CODE_HASHE
- `seat_crowd_slip.py`: The crowd's own slippage limit: decode each burst buy's Universal Router V4_SWAP (SWAP_EXACT_IN_SINGLE amountOutMinimum, TAKE_ALL minAmount) and compa
- `seat_engine_replay.py`: Cross-check: the engine's own code (flip_engine 0.8, DRY_RUN=1, ENTRY=auto, LAUNCH_SELECTORS=2fcb9108) fed the real transactions of L..L+15 of every O
- `seat_explore.py`: per pool timeline
- `seat_fetch.py`: Fetch (and cache) the chain data the seat pricer needs for every Oct 8 launch of kind "copy" in oct8_pools.json: the launcher copy's code at the launc
- `seat_fetch_deploy.py`: For each copy launch: the launcher copy's creation (a tx with to=null in L-40..L-1 whose receipt's contractAddress is the copy), and the copy's code a
- `seat_rpc_lag_probe.py`: Live probe (today, from this container, not the box): for transactions seen in the sequencer feed, how long until the public RPC serves their receipt 
- `stakes_follow.py`: Paper-price the FOLLOW entry of flip_engine 0.8 (ENTRY=auto -> follow on launches through the original launcher) on every Oct 8 2026 launch of kind "o
- `validate_follow.py`: Checks for follow.py, from its cache: (1) v4math against our real relay fills on Oct 8 (buy tokens at the chain state just before our buy; sell ETH at

### `yday/vfy` (11 files)

- `vcopies.py`: selectors of orig launch txs
- `vcross.py`
- `vcrowd.py`: For every paper trade that sells: each crowd buy landing between our buy (end of B) and our sell (head of S): would it still fill with our buy ahead o
- `vfetch.py`: Verifier's own raw-data fetch (independent of follow.py / cache_follow.pkl). For each 'orig' launch of Oct 8: the launch receipt, every Swap/ModifyLiq
- `vfix.py`: Write follow_verified.json: follow.json with the one record-level correction found (trade 8's live field omitted the two approval transactions our wal
- `vgas.py`
- `vpfee.py`: all ProtocolFeeUpdated on the PM over the day + margin
- `vprice.py`: Verifier's independent paper pricer for the FOLLOW entry (flip_engine 0.8, ENTRY=auto -> follow on the original launcher). Reads only raw/<block>.json

### `yday/vseat` (5 files)

- `vfetch.py`: Independent fetch for the seat verifier (not using the pricer's cache): for chosen copy launches, the launch tx + receipt, the launcher's code at late
- `vprice.py`: Independent re-pricing of the seat entry (flip_engine 0.8) on chosen Oct 8 copy launches, from raw/<L>.json (vfetch.py). Written fresh; imports only v

- `chk/`: 1 files (review agents' scratch)
- `repro/`: 1 files (review agents' scratch)
- `review06_concurrency/`: 25 files (review agents' scratch)
- `review06_correctness/`: 3 files (review agents' scratch)
- `review06_fixes/`: 4 files (review agents' scratch)
- `review06_lc/`: 12 files (review agents' scratch)
- `review06_nonce/`: 9 files (review agents' scratch)
- `review06_ops/`: 10 files (review agents' scratch)
- `review06_ops_halt/`: 2 files (review agents' scratch)
- `review06_refute3/`: 2 files (review agents' scratch)
- `review06_refute_buyblock/`: 5 files (review agents' scratch)
- `review06_refute_getcode/`: 15 files (review agents' scratch)
- `review06_refute_wedge/`: 17 files (review agents' scratch)
- `review06_regr/`: 1 files (review agents' scratch)
- `review06_regressions/`: 10 files (review agents' scratch)
- `review06_tests/`: 46 files (review agents' scratch)
- `review06_user/`: 22 files (review agents' scratch)
- `rt/`: 3 files (review agents' scratch)
- `rv/`: 25 files (review agents' scratch)
- `rv09money/`: 4 files (review agents' scratch)
- `score_mix/`: 1 files (review agents' scratch)
- `vdstop3/`: 1 files (review agents' scratch)
- `verify_adversarial/`: 11 files (review agents' scratch)
- `verify_backtest/`: 6 files (review agents' scratch)
- `verify_dstop/`: 1 files (review agents' scratch)
- `verify_engine/`: 7 files (review agents' scratch)
- `verify_live/`: 11 files (review agents' scratch)
- `verify_slot/`: 1 files (review agents' scratch)
- `verify_wd/`: 1 files (review agents' scratch)
- `vfy_lookalike/`: 1 files (review agents' scratch)
- `vlate/`: 2 files (review agents' scratch)
- `vpnl/`: 1 files (review agents' scratch)