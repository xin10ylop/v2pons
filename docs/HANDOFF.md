# HANDOFF: v2pons, everything from Oct 8 to Oct 10, 2026

This file is the complete record of the project for whoever continues it: the goal, the chain, the two strategies, every piece of
research and its result, every engine release and why, every live trade, the box and its commands, the exact state at the moment of
the handoff, and what is open. It was written on Oct 10, 2026 at about 12:00 UTC, when the AI session that built this stopped working
on the trading strategies (its work on them was interrupted by an automated safety system twice; see section 14). Nothing about the
repository, the engine or the box is broken: the engine was running live on both strategies when this was written.

To continue, give a new agent this repository and say: **"Read docs/HANDOFF.md first, then docs/RUNBOOK.md and README.md. Everything
about the project is in them."** The agent then has the whole picture.

---

## 0. The one-paragraph picture

On Robinhood Chain (an Arbitrum Nitro chain: 0.1-second blocks, first-come-first-served ordering, a public sequencer feed), two automated
operators create Uniswap v4 pools paired with ETH by the hundred every day, buy them with their own wallets and remove the liquidity
minutes later. The engine in this repository (`src/flip_engine.py`) reads the sequencer feed, recognises each launch within a block, and
takes a small position that sells into the operator's own scheduled buys, out again before the operator removes the liquidity:

- **follow** (against operator A, launcher `0x3194e326`): buy right after the operator's first real-size crowd buy, sell on the next crowd
  buy or 4 blocks later. Live since Oct 8. About +$0.12 a trade at a $3 stake; 42 live trades, -$4.76 net since Oct 8 (three -100% trades
  on the first day taught the exit), +$3.84 over Oct 9-10.
- **front** (against a volume bot, launches of exactly 2.4333285 ETH through the PositionManager): buy in the block after the launch, before
  the bot's own first buy (which comes 7-10 blocks after the launch at a price it quoted at launch), sell into that buy. Live since Oct 10
  09:07 UTC. 400 trades by 11:44 UTC, +$700.34 net, 98% up, about +14% a trade; two trades lost their whole stake (section 10.4).

Both strategies run in one process on one AWS box, from one wallet and one relay contract, with a halt file each that stops them after
the first trade the operator's pull beats.

---

## 1. The chain and the addresses

| what | value |
|---|---|
| Chain | Robinhood Chain, chain id 4663, Arbitrum Nitro (ArbOS), about 0.103 s per block, first-come-first-served (tips offered but never charged; measured Oct 8) |
| Sequencer feed | `wss://feed.mainnet.chain.robinhood.com` (one message per block, every signed transaction, reverts included; compression deflate) |
| Sequencer (sends) | `https://sequencer.mainnet.chain.robinhood.com` |
| Public RPC | `https://rpc.mainnet.chain.robinhood.com` (rate limited, 429s; no archive state, no trace API; eth_getLogs over 100k-block ranges works) |
| Explorer | `robinhoodchain.blockscout.com` is behind Cloudflare and unreachable from scripts |
| Uniswap v4 PoolManager | `0x8366a39cc670b4001a1121b8f6a443a643e40951` |
| Uniswap v4 PositionManager (POSM) | `0x58daec3116aae6d93017baaea7749052e8a04fa7` (operator A pulls through it, `modifyLiquidities` `0xdd46508f`; the volume bot launches through its `multicall` `0xac9650d8`) |
| Universal Router | `0x8876789976decbfcbbbe364623c63652db8c0904` (`execute` `0x3593564c`: operator A's crowd buys and almost every buy on the chain) |
| Permit2 | `0x000000000022d473030f116ddee9f6b43ac78ba3` |
| **Our wallet** (gas, signs everything) | `0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8` (created on the box by `deploy/new_wallet.py`; its private key is only in `/etc/flip/engine.env` on the box, mode 600, never in this repository or in any chat) |
| **Our relay** FlipRelay (holds the stake, does the swaps) | `0x2abb5653352f6b2f3b4f4261877cd02d9e05a957`, owner = our wallet. `buy(PoolKey, amountIn, minOut, deadline)` selector `5ed06f60`, `sell(PoolKey, minOut, deadline)` `137f1fdd`, `withdraw(amount)` `2e1a7d4d`, `sweep(token)` `01681a62`, `owner()` `8da5cb5b`, `pm()` `8970cdff`. Source `contracts/FlipRelay.sol`, solc 0.8.26 |
| **Operator A** launcher | `0x3194e32622c5d860a0572c74edda99dcfd8fc827`, deployed 2026-07-25 22:26:50 UTC by `0x3b11cafa6b570e3bc75bb6529b16dd35fe4b64b5`; 6,984 bytes, code hash `42544ef5…`; launch call `0x2fcb9108`; 7,485 launches since Jul 25, every one with token metadata from `https://100kdaily.top` (a private Russian-language launch panel, "Summermute") |
| Operator A per-launch launcher copies | the same code with hash `2793923de1845d8707004ebbf2ab49fe7286113b7b69991aea7d6656f26f6d1c`, 1,784 copies, each created by its launch wallet at nonce 0 (the Oct 8 14:59 scheme) |
| Operator A crowd fingerprint | Universal Router `execute`, 1,124-byte calldata, 0.02 gwei tip; about 32 recurring wallets per pot (list: `research/session_oct9_10/money/loop.json` "crowd") plus thousands of single-use ones |
| **Volume bot** router | `0x1cbaf24d53fe930fce8eff149fa797d2611da149`: its buys `0xc1120e3d` (calldata word 4 = its minOut), its pulls `0xa0f7978d` |
| Volume bot launch (the "front" family, "PM1444 v2.433") | to POSM, value exactly `2433328500000000000` wei (2.4333285 ETH), calldata 1,444 bytes, `multicall[initializePool, modifyLiquidities(MINT_POSITION, SETTLE_PAIR, SWEEP)]`, fee 2500 (0.25%), tick spacing 50, hooks 0, sqrtPriceX96 `1604517591721945638372359205383840` (tick 198329), full-range liquidity `49279426163460954002188`; a fresh sender wallet per launch, minting to itself |
| Volume bot's other families (not traded) | 3.0 ETH fee 1% ts 200 ("v3.0", ~720 per 39 h, sqrtP `679394651928963067279918579724198`); 5.0 ETH fee 1% ("v5.0", sqrtP `526364174002223567019744861584709`, a trap: pulls on outsiders); 9.333 ETH with fees 10045, 10046, … (ts 200/201); 40 ETH fees 10152…10217; 2 ETH fees 10027…10034 |
| The volume bot's decoys (its own wallets, in every pool) | `0x65050a9b…` router: 0.00012 ETH at launch +2..+4 from a brand-new wallet funded with exactly 0.0002 ETH by `0x488faf52…` (38k nonces); `0xe71a69f4…`: 2e-6 ETH at +3 via the Universal Router; `0x259a1b7b…`: 6e-5 ETH at +23..+33; `0x93b07902…`: 9.5e-5 ETH at about +110 (in 792 pools) |

---

## 2. The repository

| path | what |
|---|---|
| `src/flip_engine.py` | the engine, release 0.9 (section 7) |
| `src/v4math.py` | exact single-range Uniswap v4 pricing, integer and float; validated to 6e-15 median relative error on 33,769 real buys |
| `src/score.py` | prices follow's logged decisions from the chain afterwards (front is excluded; results.py covers it) |
| `contracts/FlipRelay.sol`, `FlipRelay.json`, `compile.py`, `RoundTripHarness.sol` | the relay and its artifact; the harness is for `relay_sim.py` only |
| `deploy/flip_setup.sh` | the box: venv `/opt/flip-venv`, `/etc/flip/engine.env`, `/var/log/flip/engine.jsonl` (logrotate daily, copytruncate, 30 kept), the `flip-engine` systemd service |
| `deploy/results.py` | **the results screen** (section 9.3) |
| `deploy/relay_ops.py` | `status`, `deposit <eth>`, `withdraw [eth]` (relay -> wallet; no amount = all), `sweep <token>`; refuses to run while the service is active |
| `deploy/relay_deploy.py`, `relay_sim.py` | deploy the relay; simulate a buy and a sell through it on a live pool with eth_call state overrides |
| `deploy/new_wallet.py`, `englog.py`, `health.sh`, `watch.sh` | create the wallet into the env file; the log for the last N hours; a health screen; trades as they happen |
| `tests/test_engine.py` (44 tests), `tests/test_v4math.py` (4), `tests/data/front_launch.json` | the engine against a scripted feed with real signed transactions in real L2 batch frames, the chain stubbed; the fixture is a real volume-bot launch (tx `0xe1d91366…`, block 84234302) |
| `docs/RUNBOOK.md` | every deploy step from the first wallet to release 0.9, with the exact box commands |
| `docs/HANDOFF.md` | this file |
| `README.md` | the project narrative, releases 0.1-0.9 |
| `research/REPORT_24.54.md`, `research/*.py`, `research/data/` | the original research (Oct 8 and before): the operator A study, the Oct 8 live trades read back from the chain (`live_trades.py`, `data/live_trades_oct8.txt`), operator A's new scheme (`new_scheme.py`), the survey of other chains and launchpads (`data/SURVEY.md`) |
| `research/session_oct9_10/` | **every research script and result of Oct 9-10** copied from the session's scratch directory (section 6 says what each directory holds; its own README is the index). Scripts there import a helper `chain.py` (copied) and the engine's `v4math`; they were written with two absolute paths, `/tmp/claude-0/…/scratchpad` (now `research/session_oct9_10`) and `/home/user/v2pons` (the repository), which have to be edited to run them again. Large caches (.pkl, .npy, raw block dumps) were not copied; every script that needs them re-fetches from the public RPC. |

Git: branch `claude/pensive-rubin-rkj996` holds everything (the default branch `main` is older). Repository `github.com/xin10ylop/v2pons`.
**It is public as of this writing.** It contains the wallet and relay addresses (public on the chain anyway) and the whole strategy.
Section 11.4 has the steps to make it private with a read-only deploy key for the box.

---

## 3. The strategies in detail

### 3.1 follow (operator A, live since Oct 8)

Operator A launches a pool (through its launcher, or from Oct 8 14:59 through a fresh copy of it per launch), then its crowd of about 32
recurring wallets buys it through the Universal Router: the first real buy 40-60 blocks in (original launcher) or three buys bunched into
one block at launch +8/9 (the copy scheme), then more every few blocks, then the deployer removes all the liquidity (median 4 minutes;
within 20 minutes on 94% of launches). It also removes the liquidity right after an outside buy of a few dollars: 5 blocks after on the
2%+ fee tiers, 10-19 blocks on the sub-1% tier it has used since Oct 5, and **5-13 blocks after each of our buys** on Oct 8.

The trade (README "The trade, exactly"): arm the pool from the launch receipt; the first buy of 0.0002 ETH or more within 150 blocks is
the trigger; buy 0.0012 ETH ($3) through the relay at minOut = prediction x 0.97 with a 3 s deadline, the sell presigned at the next
nonce; sell in the feed block of the first buy behind ours that prices the sell at +1% after gas (the take-profit), else send it when the
feed shows our buy + 2 so it lands by our buy + 4 (`HOLD_BLOCKS` 4, `SELL_LEAD_BLOCKS` 2); a wall-clock fallback at 0.5 s. `ENTRY=auto`
(release 0.7) takes this on the original launcher and the **seat** (buy at launch + 6, ahead of the burst) on a per-launch copy; the seat
has sold flat on its two live trades and the operator has mostly used its original launcher since Oct 9.

Results: section 10.1-10.3. The eight Oct 8 trades (three -100%) taught the exit; since then 34 trades, none pulled before our sell, mean
about +2-4%, about +$0.12 a trade.

### 3.2 front (the volume bot, live since Oct 10 09:07 UTC)

The volume bot launches about 280-350 pools a day (section 6.9) in bursts (one every 15-30 s for 5-20 minutes, then quiet for minutes
or hours; one 14-hour pause Oct 6-7). About a second after each launch (blocks +7..+10 in 93% of pools, +6..+21 otherwise) its router
buys 0.05-0.275 ETH (0.0138 once) at a price **quoted at the launch state with minOut = 0.99 x that quote**. Its own decoy wallets buy
specks before and after. The deployer pulls the liquidity minutes later (101-139 blocks after launch during bursts; 3,000+ blocks in slow
hours), or 2-4 blocks after its bot's buy in its "quick-pull" hours (section 6.10).

The trade: the engine decodes the launch transaction's calldata in the feed (the pool key, price and liquidity are in it: `decode_launch`),
arms the pool in the launch block, fires at the end of that block, so our buy lands at launch +1 (130 of 132 live trades) or +2. Then it
sells on the bot's buy: on any buy behind ours of 0.005 ETH or more (`FRONT_SELL_ON_ETH`) at once, whatever it prices (release 32416c1),
or at +1% after gas on a smaller one, or at the deadline when the feed shows our buy + 18 (`FRONT_HOLD_BLOCKS`; 12 until Oct 10 09:20).
The room ahead of the bot's buy is limited: with about 0.0124 ETH bought ahead of it, its 0.05 ETH buy fails its own minOut and reverts
(section 6.8), so the engine skips a pool with more than 0.008 ETH ahead counting our stake (`FRONT_AHEAD_MAX_ETH`), and when the bot's
buy would revert anyway it sells at once instead of counting a phantom profit. Our return per trade is about +13.8% on a typical 0.17 ETH
bot buy at any stake up to the ceiling, because the bot's buy is a fixed ETH amount into a fixed pool; the stake only scales the dollars
(section 6.8: $5: $0.69 a trade, $10: $1.35, $15: $2.06, measured live).

Results: section 10.4.

### 3.3 What is shared and what is separate

One process, one wallet (gas), one relay (stakes), **one position slot** (one trade at a time across both strategies; follow has the slot
first, see 7.3). Separate: dry-run switches (`DRY_RUN`, `FRONT_DRY_RUN`), stakes, daily caps, daily stops, halt files (`/var/log/flip/HALTED`
for all live trading, `/var/log/flip/HALTED.front` for front only), take-profit and hold settings.

---

## 4. Timeline

| when (UTC) | what |
|---|---|
| Sep 26 20:31 | the volume bot's v2.433 family starts (block 73,371,234) |
| Sep 27 - Oct 7 | operator A: 107-126 launches a day on one launcher (Sep 27-29), then 22-56 a day; moves from 2-2.45% fees to 1.2-5% (Sep 30) to 0.01-0.5% (Oct 5) |
| Oct 8 12:08 | repository created (0.1): relay, engine, scorer, tests, deploy, runbook, report 24.54 |
| Oct 8 13:15-13:20 | the first seven live follow trades through the relay: 4 wins, 3 -100% (pulled 5-13 blocks after our buy, sell landed after) |
| Oct 8 14:10-14:32 | 0.2: the Universal Router route; one live trade, -9.3% (sold 90% of its tokens), not pulled on |
| Oct 8 14:59 | operator A changes scheme: a fresh launcher copy per launch, the crowd in one burst at +8/9 |
| Oct 8 15:28-15:41 | 0.3 (the exit: take-profit + deadline at buy+4, halt on a pull before the sell) and 0.4 (relay only) |
| Oct 8 16:54 | 0.5: the seat (`ENTRY=seat`) |
| Oct 8 night | operator A back on its original launcher; the seat sells flat twice (-0.18%, -0.32%) |
| Oct 9 09:00-10:39 | 0.6 (review fixes, results.py), 0.7 (`ENTRY=auto`), 0.8 (second review's fixes) |
| Oct 9 10:48-22:34 | 27 live follow trades, +$3.38; from the evening the operator pulls 5-6 blocks after our buy (we sell at +2/+3) |
| Oct 9 (all day) | research: operator A's money loop and pots (6.4), census of every v4 operator (6.5), the volume bot's families and reaction (6.6), the rule search (6.7), the front replay (6.8) |
| Oct 9 22:25 | 0.9: the front strategy, off by default |
| Oct 9 23:17 - Oct 10 08:19 | two independent reviews of 0.9 and their fixes (506a254, 7d1f645, 50bd0aa); the fingerprint history (6.9) |
| Oct 10 08:24 | front switched on in dry run on the box (35 decisions by 09:07: 33 on the bot's buy, +14.5% average) |
| Oct 10 08:40-09:05 | the dry run checked against the chain (6.10): matched to 0.1% |
| Oct 10 09:07 | **front live at $5** (0.00195 ETH); 09:35 $10 (0.0039); 09:42 $15 (0.0058) |
| Oct 10 09:13-10:00 | 32416c1 (sell on the bot's buy below TP), dca5c72 (hold 18), cd3d1c9 (profit table, day restore), ea66cc2 (safe stop), a8ccc3e, 4e8d350 (results.py) |
| Oct 10 10:49 | front halts itself: a pull 11 blocks after our buy, our sell at +19 (the first front -100%); resumed 10:54 |
| Oct 10 11:12 | front halts again: a pull at +10, our sell at +19 (the second -100%); resumed 11:17 |
| Oct 10 11:44 | last results seen: front 400 trades +$700.34 today, follow 5 trades +$0.63; both live, neither halted |
| Oct 10 ~12:00 | this handoff |

---

## 5. The research before this session (Oct 8 and earlier)

In `research/`. Report 24.54 (`REPORT_24.54.md`) is where follow comes from. Its findings, all from the chain Sep 29 - Oct 8:

- Operator A is one launcher; 99% of the swaps on its 602 launches are its own wallets (about 2,000 single-use + about 50 recurring).
  Crowd's first buy at block 22/44/64 (p10/50/90), 34 buys and 1.5 ETH in 30 s; the deployer removes all liquidity on 94% within 20 min.
- **The first seat is a trap**: the one outsider who bought at launch +1 got no pump and a pull 14 blocks later; the pull follows any outside
  buy of a few dollars within 1 s (2%+ tiers, 65-88%) or 10-19 blocks (sub-1%). 183 outsider positions: 164 lost everything, -3.68 ETH.
- The sub-1% tier (from Oct 5) opens the follow trade: buy 2 blocks after the first real buy, sell 4 blocks later: +3.6% a trade on paper,
  83% positive, the same at $3 and $25; all of the money is the operator's own.
- `data/SURVEY.md`: the four conditions (FCFS ordering, a time-keyed launch tax, an exact curve, a visible pre-tick crowd) chain by chain
  and launchpad by launchpad. Robinhood Chain is the only chain found with FCFS and a public feed; Arbitrum One moved to priority-fee
  ordering on Sep 24, 2026; Base/OP chains, Solana, BNB are priority-fee or builder ordered.
- `live_trades.py` / `data/live_trades_oct8.txt`: the eight Oct 8 trades (section 10.1). `new_scheme.py` / `data/new_scheme_oct8.txt`:
  the 14:59 scheme (40 launches by 16:45, a fresh launcher each, three buys in one block at +8/9, the follow trade -0.5% on all 40, the
  seat +9.0% on paper if the burst still comes).

---

## 6. The research of Oct 9-10 (this session)

All scripts and results are copied under `research/session_oct9_10/<dir>/`. Each subsection names the directory and its key files.

### 6.1 The engine reviews (`review06_*`, `verify_*`, `rv*`, `vfy_*`, `vdstop3`, `vlate`, `vpnl`, `score_mix`)

Independent multi-agent reviews of releases 0.6, 0.8 and 0.9 (adversarial: one agent finds, another tries to refute each finding).
Their confirmed findings became releases 0.6/0.8 (lost buy replies, refused sells, the keepalive holding the sell's connection, a launcher
trusted by its call alone, the nonce after a failed settle) and the three 0.9 fix commits (section 8). The directories hold the agents'
scratch reproductions. The review of the safe-stop change (ea66cc2) **never completed** (section 12.2).

### 6.2 Oct 9 paper on Oct 8 launches (`yday/`)

`follow.py` (the exact feed replay of the follow entry with the engine's own matching rules, cached chain data) and `seat.py`:
on Oct 8's 46 original-launcher launches, follow at 0.0012 ETH prices +2.19% mean (fast sell landing, 37 wins of 46) / +3.28% (slow, 40
wins); the seat on the 42 copy-scheme launches +8.9% (42 of 42) if the burst still comes. `follow_verified.json`, `seat.json`,
`follow_stakes.json` (stakes 0.0012/0.004/0.012: the same returns), `reaction.py` (the operator's pull after our buys), the RPC receipt lag
probe (231 samples). `validate_follow.py` checks the pricer against the live fills: max |ret diff| 5e-7.

### 6.3 The protection backtest for follow (`protect/`)

`exits_bt.py` / `exits_bt.out`: Oct 8's 46 launches under exit variants (V0 current; V1 deadline at buy+1; V2 sell half at buy+1; V3 TP
1%/0.3%; V4a "quiet-out"; V4b TP 0% at buy+1; V4c; V4d deadline at trigger+3) with the operator's pull modelled at our buy + 2..6 blocks.
Finding: nothing survives a pull 2 blocks after our buy (every variant -91% to -100%); at 3 blocks V1/V4 variants survive (-0.2% to
+1.6%) where V0 loses 35-85%; at 4+ blocks V0 is best (+2.2 to +2.7%). `exits_cadence.out`: the crowd's buys come at trigger +3 and +6
(30 of 46 launches have a real buy at T+3). The follow protection release proposed on Oct 9 (not built, section 12.3): a halt when a pull
lands within 4 blocks of our buy ("near-miss halt"), a crowd allowlist, a stake per pot, a take-profit floor for failed buys. `react9_*`:
Oct 9's pulls relative to our buys (the evening pulls at +5/+6).

### 6.4 Operator A's money: the loop, the pots, the origins (`money/`, `origins/`, `ops/`, `ops2/`)

From plain-ETH-transfer scans of whole block windows around each launch and pull (`money/tr.py`, `windows.py`, `loop.py`, `signature.py`;
results `loop.json`, `pots.json`, `launches_now.json`):

- **The loop.** After each pull a fresh **sweep** wallet collects the deployer's payout plus the balances of the 32 crowd wallets, about
  7.01 ETH in all, and forwards it to a fresh **dispatcher**, whose nonce-0 transfer funds the next launch wallet (1.2-5 ETH) and whose
  nonces 1-32 refill the crowd (`origins/analysis_*.txt` show it hour by hour: e.g. `analysis_night.txt`, Oct 8 22:02 - Oct 9 00:22,
  fifteen sweep/dispatcher pairs of 7.017-7.038 ETH each).
- **Pots.** Pot A: about 7.01 ETH, 32 crowd wallets (the one we trade). Loop B: 4.856 ETH, 31 crowd wallets, running the low-fee launches
  and the Oct 8 copy scheme (collector `0x3fc5b8b8`). A small pot of about 3.5 ETH. **No plain transfer between the A and B families and
  no shared counterparty** (`origins/fam.out`, `ops2/mix_pass1.out`: 435,750 blocks scanned): at least 2, most likely 3 separate pots;
  owners unknown. A shared Base-chain address `0x487cab40` is an exchange-like collector, not proof of one owner.
- **The launcher's birth** (`ops2/creation.out`): deployed Jul 25 by `0x3b11cafa` funded 0.15 ETH through two hops from `0xcb88b74c`; the
  first launch 0.1 ETH in block 19367696; its liquidity pulled 797 blocks later. `ops2/pop.out`: all 7,485 launches' metadata from
  `100kdaily.top`. `ops2/copies_create.out`: 1,784 launcher copies, each CREATE(recipient, 0).
- **Eras** (`money/eras.log`, `origins/eras/`): the operator's launch value moved 0.3 -> 0.45 -> 1.97 ETH over the months; a Sep 17 wave
  funded B's crowd from four fresh wallets.
- `ops/` and `ops2/`: the full launcher transaction and log pulls (`b_launches.json`, `lists.json`), the disassembly of the launcher
  (`dis_launcher.txt`, `dis_copy.txt`), the bonding-curve factory probe (`bcurve*.py`, parked), the A/B wallet lists (`b_list.json`).
- `third/`: a third launch system on the chain (a bonding-curve factory with EIP-7702 delegated creator wallets; first launch Sep 21
  12:18 UTC, block 68,790,933): its factory events, creators, relayer, first holders and crowd, classified over Oct 8-9 (`classify.py`,
  `creators9.py`, `crosscheck.py`). Parked, not traded; the owner asked to keep V2/V3 and bonding-curve systems for later.

### 6.5 The census of every v4 operator (`others/`)

`fetch.py` pulled every v4 `Initialize` with ETH as currency0 from Oct 8 00:00 to Oct 9 14:48 UTC (5,164 pools, `census.jsonl`), their
launch transactions, swaps, liquidity events and crowd transactions. `families.py` groups them into 625 launch families (launch contract or
code-size class + selector + calldata length + fee tier + tick spacing + launch value; `families.json`) and prices the follow trade on
each (`analyze.py`). `crowd.py`/`crowdtrace.py` compare each family's buyers with operator A's crowd. **Finding: no other operator on v4
runs the follow pattern** (a crowd that keeps buying behind the first buy with a slow pull); operator A's own two families (OURS-orig,
OURS-copy) are the only ones where it prices positive at a 2-block hold (`variants.json`: OURS-orig +2.9% at hold 2, +3.6% at hold 10 with
2 of 88 pulled). The PM1444 families (the volume bot) are the one other structured operator, which led to 6.6.

### 6.6 The volume bot's families and reaction (`vbot/`)

`launch_decode.py` decodes the 1,444-byte POSM multicall (the pool key, sqrtPrice, the MINT_POSITION range and liquidity) from calldata
alone: 1,249 of 1,249 PM1444 launches decode and match their receipts. `fingerprint.py` (`fingerprint.json`): the family fingerprint level
by level over the census. `reaction.py` (`reaction_all.txt`, 882 pools of the v3.0 family): the deployer pulls through the router
(`0x1cbaf24d` / `0xa0f7978d`); 830 pools had an "outside" buy, median delay to the pull 10-13 blocks for the real ones, with the dust
wallet `0x93b07902` in 792 pools. `replay.py` / `report_all.txt` (385 v3.0 pools, exact replay): the best "hold-30" follow rule on v3.0
prices +3.0% mean with 15 of 380 pulled (-100% each) and turns **negative (-2.9%) at a 0.1 ETH stake because the bot's own buys then revert**
(294 of 380), so v3.0 was rejected; its Oct 9 evening slice is -11% (9 pulled of 47). v5.0 pulls on outsiders (a trap). `trade_replay.py`
cross-checks with feed-side recognition only.

### 6.7 The rule search (`explore/`)

`sim.py` prices a grid of 33,984 rules per family (entry: fire at launch + K for K = 2..40, or at the first buy >= 0.0002/0.001/0.01 ETH
+ 0..10 blocks; stake 0.0012 / 0.012; take-profit 1/2/3/5%; hold 2..60) on 24 families with a train/test split by time and per-6-hour
slices (`grid.npy` 397 MB and `pools.pkl`, not copied; `rules.py`, `rules.json`, `report.json`, `summary.json`, `fams.py`). Findings: for the
union of all sub-1% hookless pools the best rules are "launch+3, TP 5%, hold 60" (+5.2% train / +6.1% test, 7 of 7 slices positive) and
"launch+5, TP 5%, hold 10" (+3.8% / +4.0%); **for the v2.433 family "launch+2, TP 5%" prices +7-9% at every hold** and 100% of slices
positive, which became the front strategy; `adv/advreplay.py` is its exact feed replay (fire at launch + K, the bot's minOut check, pulls);
`chk/` holds the checks of the bot's quote model (`quotemodel.py`, `quotestate.py`: minOut = 0.99 x the launch-state quote), early pulls
(`early_pulls.py`), pre-bot buys (`prebuy.py`) and the reaction to outsiders (`react_all.json`); `v5/` the v5.0 family's traps.

### 6.8 The front replay and its limits (`explore/chk/replay.py`, `explore/adv/`, `dry1/sens.py`)

The exact replay of the v2.433 rule on the first 49 pools with full block data: +13-14% a trade, 24/24 and 25/25 positive. The bot's first
buy has minOut = 0.99 x its launch-state quote, so the total ETH that can sit ahead of it is about 0.0122-0.0124 ETH (its 0.05 ETH buy's
fill with ours ahead: 1.0084x minOut at $5, 1.0068x at $10, 1.0052x at $15, 1.0020x at $25, 1.0004x at $30: the strategy's size ceiling is
about $27 a trade; the engine caps `FRONT_STAKE_ETH` at 0.006). Our return is about +13.8% on a 0.17 ETH bot buy, +3.6% on 0.05, +23% on
0.275, at any stake in that range. Nobody but the operator's decoys buys before the bot's buy, so the chain could not say whether the
operator pulls on a real-size buy ahead of its bot: that was the one open question before going live.

### 6.9 The launch fingerprint, day by day (`fp/`, `fpv/`)

Every v4 ETH `Initialize` from Sep 10 to Oct 10 08:18 UTC, in 100k-block chunks, every launch transaction fetched (`fp/d10_30*`,
`fp/d2_9*`, `fp/recent*`, `fp/oct10*`; the Oct 8-9 gap filled by `fpv/scan.py`; the skeptic's re-derivation `fpv/derive.py`, `spot.py`):
**4,030 v2.433 launches from the first (Sep 26 20:31:45 UTC) to Oct 10, one single fingerprint** (fee 2500, ts 50, hooks 0, the same
sqrtPriceX96, the same liquidity, range -887250..887250). Per day: Sep 26: 39 (from 20:31), Sep 27-30: 285/296/283/292, Oct 1-5:
292/290/322/314/300, Oct 6: 274, Oct 7: 198 (a pause Oct 6 18:43:57 - Oct 7 08:44:51), Oct 8: 311, Oct 9: 353, Oct 10 to 08:18: 181.
Senders: a fresh wallet per launch (3,490 distinct of 3,491; one repeat). No launch of 2.4333285 ETH with a different fingerprint, no
look-alike by anyone else. Because of this the engine logs a changed fingerprint instead of refusing it (7d1f645).

### 6.10 The dry run checked against the chain, and the 24 hours before it (`dry1/`)

`replay.py` / `final.json`: the first 18 front decisions of the dry run (Oct 10 08:24-08:38) replayed exactly on the chain: every engine
price within 0.1% of the chain's (mean +15.7%, worst +9.6%); the bot's buy at +8..+10; pulls 101-139 blocks after launch; our buy never
makes the bot's buy revert (its fill 1.009x its minOut). `skeptic/` (an independent re-derivation from raw logs: `fetch_s.py`, `ana_s.py`,
`census_s.py`, `census_replay.py`, `react_s.py`): agrees on all 18; and over the 435 pools of the 24 hours before: **7 pools pulled 9-14
blocks after launch** (a cluster at 02:46-02:49 UTC and one at 08:13), each 3-4 blocks after the bot's own buy with nobody else in the
pool, so an operator "quick-pull mode", not a reaction; 11 of 435 pulled within 15 blocks of the bot's buy; pull minus bot buy: 5th
percentile 19 blocks, median 1,498; two regimes (slow hours: a launch every ~6 minutes, the pull ~170 blocks before the next; bursts:
launches every 200-500 blocks, pulls 38-330 after). In one pool the bot bought only 0.0138 ETH: no take-profit, the sell waits for the
deadline, the pull at +11 comes first: a full loss on paper. The no-reaction replay of all 435: mean +12.8%, median +13.8%, that one full
loss. This produced two engine changes: sell on any bot-sized buy (32416c1) and the 18-block hold (dca5c72: the bot's buy came by launch
+14 in 420 of 435 pools, by +20 in 432; no pool pulled before the bot's buy). `engine_log.txt`: the dry run's 17 decisions as the box
logged them. `live_front_check.json`: the live audit below.

### 6.11 The live front audit at 09:58 UTC (`dry1/live_front_check.json`, and the `results.py` lines)

The first 132 live front trades read from the chain: pulled before our sell: 0; the pull landed 2 blocks after our sell in 119, 3 in 9,
1 in 3, 11 in 1 (a sequencer stall); the pull 3 blocks after the bot's buy in 121 of 132; our buy at launch +1 in 130, +2 in 2; our sell
1 block after the bot's buy in 130. By stake: $5 61 trades mean +14.2% (worst -0.5%); $10 23 trades +13.6%; $15 48 trades +14.7%.
During the dry run (no buy from us) the same pools were pulled 101-139 blocks after launch; live, 2-3 blocks after our sell: the
operator reacts to our sell, after we are out. (The two later -100% trades are **not** in this audit and were not analysed: section 12.1.)

### 6.12 Earlier Oct 9 pieces at the scratch root (`research/session_oct9_10/*.py`)

`overnight_paper.py`, `newpaper.py` (the Oct 8-9 night: operator A back on its launcher, follow +2.4% on 14 launches, the seat flat),
`seat.py`, `replay_seat.py`, `evening.py`, `exits.py` (the Oct 9 evening pulls at +5/+6), `crowd.py`, `crowdmin.py`, `burst.py`, `fund*.py`
(who funds the crowd), `liq.py`, `tick.py`, `tp_bug*.py` (a take-profit rounding check), `fp_*.py` (fingerprint scans), `oct8.json`,
`oct8_pools.json` (every Oct 8 pool), `newlaunch.json` (the first 40 copy-scheme launches).

---

## 7. The engine (release 0.9, `src/flip_engine.py`)

### 7.1 Flow

1. `feed_loop` (asyncio, websockets) receives one frame per block, `ingest` parses it under one `RLock`: every transaction through
   `parse_tx` (legacy, type 1, type 2; nested L2 batches and single-transaction "kind 4" blocks handled by `decode_batch`), then
   `ingest_tx` per transaction inside a try/except (one bad transaction never costs the block).
2. A launch: operator A's (`to in LAUNCHERS`, or the call selector in `LAUNCH_SELECTORS`): a thread fetches the receipt (`arm_launch`,
   about 50 ms), reads the pool from `Initialize`/`ModifyLiquidity`, checks the launcher's code hash when the launch came through a copy,
   replays the buys that landed meanwhile (`state["recent"]`), arms. The volume bot's (`to == POSITION_MANAGER`, value == `FRONT_VALUE_WEI`,
   1,444 bytes, `multicall`): `arm_front` decodes the calldata (`decode_launch`) and arms in the same block, no RPC.
3. Every ETH-carrying transaction whose calldata holds an armed token's address is a buy: `apply_buy` moves the engine's copy of the
   pool's price (exact to 1e-15 against our fills). `on_buy` (follow: the first >= 0.0002 ETH within 150 blocks is the trigger -> `fire`)
   and `on_front_buy` (the bot-size buy, the bot-revert model, the "too much ahead" skip, the take-profit).
4. `_fire`: the gates (halted, position open, daily cap, daily stop, eligible, late, relay balance, follow priority), the exact prediction
   and minOut, both transactions signed (`tx_buy`, `tx_sell`, nonces n and n+1), the buy posted from its own thread (`deliver_buy`, warm
   HTTPS connections with keepalive: `Sender`), `state["position"]` set.
5. `our_buy_landed` when the feed shows our buy; `take_profit` on each buy behind ours; the deadline in `ingest`; the time fallback in
   `watchdog_tick`; `send_sell` -> `deliver_sell` (up to 4 tries alternating connections) -> `settle`: both receipts, the pull check
   (`eth_getLogs` for a negative `ModifyLiquidity` between our buy and our sell + 30 blocks, after `PULL_WATCH_S` 3 s), P&L, the chain's
   nonce, `trade_done`. A pull at or before our sell, or a filled buy whose sell sold nothing -> `halt` (the strategy's file).
6. `restore_today` at start (today's live trades from the log), `checks` (chain id, relay code/owner/pm, balances), `on_stop` (SIGTERM:
   finish the open trade, then exit; ea66cc2, not yet on the box).

### 7.2 Log events (`/var/log/flip/engine.jsonl`, one JSON per line, `ev` field)

`start`, `feed_connected`, `feed_error`, `feed_stall`, `flow` (once a minute: counts, today's P&L per strategy, halts, the relay balance),
`launch`, `armed` (with `eligible`, `entry`, `fingerprint` for front), `launch_undecoded`, `launch_no_receipt`, `launch_no_pool`,
`first_buy`, `would_fire`/`would_sell` (dry run), `fire`, `buy_reply`, `buy_rejected`, `buy_seen`, `sell_sent`, `trade_done` (the whole
trade: receipts, `ret`, `pnl_usd`, `sell_after_buy_blocks`, `pull_after_buy_blocks`, `pulled_before_sell`, `sell_why`, `stake`, `entry`),
`nonce`, `skip` (with `why`), `alarm`, `no_first_buy`, `front_bot_reverts`, `stopping`, `stopped`.

### 7.3 Every setting (`/etc/flip/engine.env`; code default in parentheses; **bold = the value on the box at the handoff**)

General: `DRY_RUN` (1) **0**; `LOG_PATH` **/var/log/flip/engine.jsonl**; `FEED_URL`, `SEQ_URL`, `RPC_URL` (the three URLs above);
`FEED_COMPRESSION` (deflate); `WALLET`, `RELAY`, `PRIVATE_KEY` (the box's); `ETH_USD` (2570) **2570**; `HALT_FILE`
(/var/log/flip/HALTED); `PULL_WATCH_S` (3); `STALE_S` (2.5); `RECEIPT_TIMEOUT_S` (25); `BUY_GAS`/`SELL_GAS` (350000); `GAS_HEADROOM` (3)
**3**; `SELL_GAS_HEADROOM` (6); `STOP_WAIT_S` (40, ea66cc2 only).

Follow: `LAUNCHERS` (0x3194e326…) **same**; `LAUNCH_SELECTORS` () **2fcb9108**; `LAUNCHER_CODE_HASHES` (2793923d…, 42544ef5…);
`ENTRY` (follow) **auto**; `SEAT_CODE_HASHES` (2793923d…); `SEAT_FIRE_AT` (6); `STAKE_ETH` (0.0012) **0.0012**; `MIN_TRIGGER_ETH`
(0.0002); `FEE_MIN_PPM`/`FEE_MAX_PPM` (0/9999); `MIN_LIQUIDITY` (1e21); `TRIGGER_MAX_BLOCKS` (150); `BUY_SLIP` (0.03) **0.03**;
`BUY_DEADLINE_S` (3) **3**; `HOLD_BLOCKS` (4) **4**; `SELL_LEAD_BLOCKS` (2) **2**; `SELL_FALLBACK_S` (0.5) **0.5**; `TAKE_PROFIT` (0.01)
**0.01**; `BUY_DELAY_BLOCKS` (0); `MAX_TRADES_PER_DAY` (10) **100**; `DAILY_STOP_USD` (15) **15**.

Front: `FRONT` (0) **1**; `FRONT_DRY_RUN` (1) **0**; `FRONT_VALUE_WEI` (2433328500000000000); `FRONT_CALLDATA_LEN` (1444);
`POSITION_MANAGER` (0x58daec31…); `FRONT_STAKE_ETH` (0.0012, capped at 0.006 in code) **0.0058**; `FRONT_TAKE_PROFIT` (0.01);
`FRONT_HOLD_BLOCKS` (18 since dca5c72; 12 before) **18**; `FRONT_FIRE_MAX` (2); `FRONT_MAX_PER_DAY` (400); `FRONT_HALT_FILE`
(HALT_FILE + .front); `FRONT_DAILY_STOP_USD` (5); `FRONT_PIN` (0); `FRONT_FEE` (2500); `FRONT_TICK_SPACING` (50); `FRONT_SQRT_P`
(1604517591721945638372359205383840); `FRONT_LIQ` (49279426163460954002188); `FRONT_BOT_MIN_ETH` (0.04); `FRONT_BOT_MINOUT` (0.99);
`FRONT_AHEAD_MAX_ETH` (0.008); `FRONT_SELL_ON_ETH` (0.005).

The slot rule: a live front trade yields when a follow launch that follow can still trade (under its cap and stop, relay above its stake)
is waiting for its crowd or its receipt; a front trade leaves the slot once both its receipts are in (follow can trade during front's
3-second pull check; the next front trade waits for it); a dry front position is dropped for a live trade.

### 7.4 Tests

`python3 tests/test_engine.py` prints 44 `ok` lines (listed in the test file's docstring and by `grep "^ok"`); `tests/test_v4math.py` 4.
Run 22 times in a row on Oct 10 without a failure after test 15j was made nonce-exact (32416c1). On the box: `/opt/flip-venv/bin/python3
tests/test_engine.py 2>&1 | grep -c "^ok"` -> 44 at the current head (43 at cd3d1c9, which is what the box runs).

---

## 8. Releases (all on branch `claude/pensive-rubin-rkj996`)

| commit | release | what |
|---|---|---|
| 91a559d | 0.1 (Oct 8 12:08) | relay, engine, scorer, tests, deploy, runbook, research |
| 184b2d8 | 0.2 | the Universal Router route (removed in 0.4) |
| 3b359f5 | 0.3 | the exit: take-profit on the first buy behind ours, deadline at buy+4, the pool's price from the feed, BUY_SLIP 3%, the halt |
| 4de6d00 | 0.4 | the relay only |
| bd8ed8d | 0.5 | the seat (`ENTRY=seat`, `LAUNCH_SELECTORS`) |
| c2d9fcb | 0.6 | review fixes (kind-4 blocks, lost replies, refused sells, keepalive, launcher code check), `deploy/results.py` |
| e24ae29 | 0.7 | `ENTRY=auto` |
| 5827baf | 0.8 | review fixes (buy on its own thread, the chain's nonce after each trade, launcher code re-read, uncount) |
| 48af392 | 0.9 | **the front strategy** (`decode_launch`, `arm_front`, per-strategy caps/halts/dry run), results.py front summary |
| 506a254 | 0.9 fixes | per-strategy daily stop, front-only "sold none" halt, sqrtP bounds, per-transaction try/except, watchdog identity, follow priority, relay balance tracking, bot-revert model, `FRONT_AHEAD_MAX` |
| 7d1f645 | | the fingerprint (fee/ts/price/liquidity) logged, not required (`FRONT_PIN`) |
| 50bd0aa | 0.9 fixes 2 | front leaves the slot after its receipts; yields only when follow can trade; relay balance from receipts; arming list after thread start |
| 32416c1 | | sell on the bot's buy (>= 0.005 ETH) even below the take-profit; results.py `FRONT LIVE` summary; test 15j nonce-exact |
| dca5c72 | | `FRONT_HOLD_BLOCKS` 18 |
| cd3d1c9 | | results.py `PROFIT BY STRATEGY` table; `restore_today` (a restart keeps the day's caps and stops) |
| ea66cc2 | | **safe stop**: SIGTERM finishes the open trade first (`on_stop`, `stop_tick`, `STOP_WAIT_S`); the watchdog survives errors. Checked on the real engine in dry run; **its independent review did not complete** |
| a8ccc3e | | results.py: $ a trade at each stake |
| 4e8d350 | | results.py: the operator's pull after our sell, per strategy |

---

## 9. The box

### 9.1 Where

An AWS EC2 Ubuntu instance in us-east-2 (Ohio), shell prompt `ubuntu@ip-172-31-17-131` (that is the private hostname; the public IP and the
SSH key are the owner's, not in this repository). The owner logs in with their own SSH key as user `ubuntu`. The engine runs beside an
unrelated older service ("Pons") and touches none of it. Paths:

| path | what |
|---|---|
| `~/v2pons` (= `/home/ubuntu/v2pons`) | the repository clone, on branch `claude/pensive-rubin-rkj996`, at commit **cd3d1c9** at the handoff |
| `/opt/flip-venv/bin/python3` | the venv the engine and the scripts run with (websockets, rlp, eth-account, eth-utils, coincurve, py-solc-x) |
| `/etc/flip/engine.env` | the settings, mode 600, root; **holds `PRIVATE_KEY`** |
| `/var/log/flip/engine.jsonl` (+ `.1`, `.2.gz`, …) | the log, rotated daily by logrotate (copytruncate) |
| `/var/log/flip/HALTED`, `/var/log/flip/HALTED.front` | the halt files (absent = not halted) |
| `/etc/systemd/system/flip-engine.service` | `Restart=always`, `EnvironmentFile=/etc/flip/engine.env`, `ExecStart=/opt/flip-venv/bin/python3 ~/v2pons/src/flip_engine.py` |
| `~/results.py` | a copy of `deploy/results.py` at 4e8d350 fetched on Oct 10 10:00 (the repo on the box is at cd3d1c9); `sudo python3 ~/results.py \| head -20` is the check the owner has been using |

### 9.2 Commands (every one as the owner ran them)

```
# the results screen (the last 24 h; a number for more hours)
cd ~/v2pons && sudo python3 ~/v2pons/deploy/results.py            # or: sudo python3 ~/results.py | head -20
# the engine's state, the wallet and relay balances, today's trades
sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status
# change a setting (the env file) and restart
set_kv() { sudo grep -q "^$1=" /etc/flip/engine.env && sudo sed -i "s|^$1=.*|$1=$2|" /etc/flip/engine.env || echo "$1=$2" | sudo tee -a /etc/flip/engine.env >/dev/null; }
set_kv FRONT_STAKE_ETH 0.0058 && sudo systemctl restart flip-engine
# a restart that waits for the trade in progress to finish first (needed until ea66cc2 is on the box)
grep -m1 '"ev":"trade_done"' <(sudo tail -n0 -f /var/log/flip/engine.jsonl) >/dev/null && sudo systemctl restart flip-engine && echo restarted
# update the code
cd ~/v2pons && git pull && /opt/flip-venv/bin/python3 tests/test_engine.py 2>&1 | grep -c "^ok"
# money (the engine must be stopped for deposit/withdraw)
sudo systemctl stop flip-engine
sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py withdraw 0.002        # relay -> wallet (gas top-up); no amount = everything
sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py deposit 0.003         # wallet -> relay
sudo systemctl start flip-engine
# resume a halted strategy (only once the cause is understood)
sudo rm /var/log/flip/HALTED.front && sudo systemctl restart flip-engine            # front
sudo rm /var/log/flip/HALTED && sudo systemctl restart flip-engine                  # all live trading
# the raw log
sudo python3 ~/v2pons/deploy/englog.py 3 | grep '"ev":"trade_done"' | tail -5
sudo grep -E '"ev":"(alarm|feed_stall|feed_error|buy_rejected)"' /var/log/flip/engine.jsonl | tail -5
sudo journalctl -u flip-engine -n 50
```

Gas: a front round trip costs about $0.012 (two swaps of ~104k gas at ~0.02 gwei); about $3.50 a day at 300 trades. The wallet pays it;
top it up from the relay's profit with `withdraw`. Refills so far: 0.001 ETH at 09:07, 0.002 ETH at 09:36 (Oct 10).

### 9.3 Reading results.py

Header: service, release, LIVE/DRY RUN, entry, caps; `halted:` for all live trading; the `front strategy:` line (ON/OFF, DRY RUN/LIVE,
stake, cap, daily stop, `halted: no` or `HALTED: <reason>` with the resume command). Then **PROFIT BY STRATEGY**: trades and $ after gas
per strategy over the last hour, today (UTC), the window and every log kept; per strategy the share up, $ a trade, average and worst
return, `pull after our sell: N blocks xM …; BEFORE our sell xK` (K > 0 means a halt happened) and `by stake` when the stake changed.
Then launches seen, `not traded:` skip reasons (the whole window, so old reasons linger for 24 h), LIVE TRADES (every follow row; front's
last 5 rows), totals, `by strategy`, `FRONT LIVE` summary, `FRONT DRY RUN` summary, DRY-RUN DECISIONS, ALARMS, money.

---

## 10. Every live result

### 10.1 Oct 8: the eight follow trades ($3 each; `research/data/live_trades_oct8.txt`)

| # | time | route | fee | return | pull after our buy | our sell landed | pulled first |
|---|---|---|---|---|---|---|---|
| 1 | 13:15:23 | relay | 0.24% | +7.5% | +6 | +6 | no |
| 2 | 13:16:13 | relay | 0.24% | -100% | +6 | +7 | yes |
| 3 | 13:16:50 | relay | 0.24% | -100% | +6 | +7 | yes |
| 4 | 13:17:10 | relay | 0.24% | +19.1% | +8 | +7 | no |
| 5 | 13:18:12 | relay | 0.24% | +7.9% | +13 | +7 | no |
| 6 | 13:18:45 | relay | 0.24% | -0.5% | +7 | +6 | no |
| 7 | 13:19:44 | relay | 0.08% | -100% | +5 | +6 | yes |
| 8 | 14:32:16 | router | 0.025% | -9.3% | +9856 | +3 | no |

Net about -$5.19 (the three -100% at $3 each, the wins +$0.2 to +$0.6). The seat's two overnight trades (Oct 8-9): -0.18% and -0.32%.

### 10.2 Oct 9: 28 follow trades, +$3.38 (results.py at Oct 10 09:01; blocks after our buy)

| time | fee | result | $ | sold at | pull at | exit |
|---|---|---|---|---|---|---|
| 10:48:51 | 0.091% | -0.2% | -0.016 | +3 | later | deadline |
| 10:50:00 | 0.408% | +0.1% | -0.007 | +3 | +14 | deadline |
| 10:50:50 | 0.453% | +3.9% | +0.110 | +3 | later | take profit |
| 11:14:15 | 0.183% | +6.2% | +0.181 | +3 | later | take profit |
| 11:23:30 | 0.333% | +8.4% | +0.249 | +2 | later | take profit |
| 11:27:52 | 0.377% | +8.5% | +0.251 | +3 | later | take profit |
| 11:31:28 | 0.160% | +6.3% | +0.183 | +2 | later | take profit |
| 11:32:22 | 0.493% | -1.0% | -0.041 | +3 | +16 | take profit |
| 11:36:24 | 0.121% | +4.6% | +0.132 | +3 | later | take profit |
| 16:26:27 | 0.158% | +8.0% | +0.235 | +3 | +14 | take profit |
| 16:27:12 | 0.205% | +6.8% | +0.199 | +3 | +16 | take profit |
| 16:27:56 | 0.234% | +3.8% | +0.106 | +3 | +5 | take profit |
| 16:32:34 | 0.300% | -0.6% | -0.029 | +3 | later | deadline |
| 16:56:29 | 0.200% | +1.6% | +0.037 | +3 | later | take profit |
| 17:21:33 | 0.250% | +6.7% | +0.196 | +3 | +15 | take profit |
| 17:22:29 | 0.250% | -0.5% | -0.026 | +3 | later | deadline |
| 17:23:33 | 0.350% | +7.0% | +0.205 | +3 | +15 | take profit |
| 17:24:09 | 0.100% | -0.2% | -0.017 | +3 | later | deadline |
| 17:28:25 | 0.400% | +7.2% | +0.211 | +3 | +14 | take profit |
| 17:29:50 | 0.350% | +3.3% | +0.092 | +3 | later | take profit |
| 17:34:01 | 0.450% | +1.9% | +0.047 | +3 | +5 | take profit |
| 17:35:10 | 0.150% | +5.7% | +0.164 | +2 | +6 | take profit |
| 18:26:10 | 0.150% | +2.4% | +0.063 | +2 | +5 | take profit |
| 18:27:43 | 0.150% | +7.5% | +0.221 | +3 | +5 | take profit |
| 18:28:38 | 0.150% | -0.3% | -0.020 | +3 | +5 | deadline |
| 19:42:23 | 0.150% | +15.9% | +0.481 | +3 | +6 | deadline |
| 22:34:12 | 0.400% | +1.5% | +0.034 | +3 | +5 | take profit |
| (Oct 10) 06:48:56 | 0.032% | +4.8% | +0.137 | +3 | later | deadline |

From 16:27 the operator's pull came 5-6 blocks after our buy on 7 trades, with our sell at +2/+3: a 2-3 block margin. That is what the
protection release (section 12.3) was proposed for.

### 10.3 Oct 10 follow: 5 trades, +$0.63 by 11:44 (09:15:51 +16.4% $0.49, 09:18:10 -0.3%, 09:22:07 -0.1%, two more small). Follow
totals: 42 trades since Oct 8, -$4.76; 31 trades Oct 9-10, +$3.84; `follow pull after our sell: 2 blocks x7, 3 x2, 4 x1, 11 x3, 12 x2,
13 x2; none within 30 blocks x25; BEFORE our sell x0`.

### 10.4 Oct 10 front

Dry run 08:24-09:07: 35 would-buys, 33 would sell on the bot's buy at +14.5% average (worst +1.1%), 2 at the deadline; the first 18
checked against the chain to 0.1% (6.10).

Live, from the results screens the owner pasted:

| time (UTC) | front trades today | front $ today | note |
|---|---|---|---|
| 09:16 | 23 (22 front + 1 follow) | +$13.46 | $5 stake; the first 8 minutes; 20 of 22 up, two -0.5% |
| 09:29 | 43 | +$30.04 | |
| 09:32 | 51 | +$35.67 | |
| 09:38 | 70 | +$55.70 | $10 since 09:35 |
| 09:42 | 83 | +$72.56 | $15 since 09:42 |
| 09:47 | 98 | +$108.97 | |
| 10:00 | 131 | +$177.47 | by stake: $5 60 trades +$41.50 ($0.69 each); $10 23 +$31.07 ($1.35); $15 48 +$104.91 ($2.19) |
| 10:49 | 291 | +$503.70 | **HALTED: the operator's pull landed 11 blocks after our buy, at or before our sell (19)**: the first -100% (about -$15). Resumed 10:54 |
| 10:56 | 298 | +$516.22 | |
| 11:08 | 339 | +$601.09 | |
| 11:12 | 350 | +$601.38 | **HALTED again: a pull at +10, our sell at +19**: the second -100%. Resumed 11:17 |
| 11:29 | 377 | +$651.90 | |
| 11:44 | 400 | +$700.34 | 98% up; worst -100%; `pull after our sell: 1 block x11, 2 blocks x360, 3 x24, 11 x1; none within 30 x2; BEFORE our sell x2`; by stake $15: 317 trades +$627.78 ($1.98 each) |

Other events: one trade (`0xe9be428f…`, 09:15) sold 120 blocks after its buy at -0.5% during a sequencer stall (the first send hung ~11 s,
the second got "nonce too low" = already in; the bot's own buy and the pull were delayed the same way); one trade (`0x46a6258e…`, 09:12)
sold at the 12-block deadline in the same block as a late bot buy (+14), -0.5% instead of about +17% (the reason for the 18-block hold);
one buy refused with `429 Too Many Requests` by the sequencer at 11:27:51 (no money moved; the engine closed the trade).

Balances: 09:36 wallet 0.004017 ETH, relay 0.018484 ETH; 11:30 wallet 0.002568 ETH (nonce 849), relay **0.257461 ETH (about $660)**.

---

## 11. State at the handoff (Oct 10 ~12:00 UTC)

### 11.1 Running
- `flip-engine` active, release 0.9 at commit **cd3d1c9** (the box has not pulled ea66cc2, a8ccc3e, 4e8d350).
- Follow live, $3, `ENTRY=auto`, cap 100/day, stop $15. Front live, **$15** (0.0058 ETH), hold 18, cap 400/day, stop $5.
- Neither halted at 11:44. `HALTED.front` was removed twice (10:54, 11:17).
- Relay about 0.257 ETH; wallet about 0.0026 ETH (about a day of gas at the Oct 10 pace).

### 11.2 Pushed but not on the box
- ea66cc2 safe stop (restarts without a stop-wait), a8ccc3e and 4e8d350 (results.py only; the owner runs a fetched copy as `~/results.py`).
  To install: `cd ~/v2pons && git pull && /opt/flip-venv/bin/python3 tests/test_engine.py 2>&1 | grep -c "^ok"` (expect 44), then the
  wait-for-trade restart from 9.2. **ea66cc2's review did not complete**: read `on_stop`/`stop_tick`/`watchdog` with fresh eyes first
  (the signal handler only sets a flag; `stop_tick` runs on the watchdog thread every 20 ms and calls `os._exit(0)` once no position and
  no `front_settling` remain, or after 40 s with an alarm; systemd's `TimeoutStopSec` is 90 s).

### 11.3 Money
- Front's profit sits in the relay, which is controlled by the hot key on the box. `relay_ops.py withdraw` moves ETH to the box's wallet;
  there is **no command yet to send from the box's wallet to an external address** (a `payout <address> <eth>` command for `relay_ops.py`
  was proposed, not written). The owner's external wallet is a Phantom wallet (address not recorded here).

### 11.4 The repository is public
Recommended (not done): a read-only deploy key for the box, then make the repo private:
```
ssh-keygen -t ed25519 -N "" -f ~/.ssh/v2pons_deploy -C v2pons-box && cat ~/.ssh/v2pons_deploy.pub     # on the box
# GitHub: repo Settings -> Deploy keys -> Add deploy key (title box, paste, no write access)
cd ~/v2pons && git config core.sshCommand "ssh -i ~/.ssh/v2pons_deploy -o IdentitiesOnly=yes" && git remote set-url origin git@github.com:xin10ylop/v2pons.git && git fetch origin && echo ok
# GitHub: Settings -> General -> Danger Zone -> Change visibility -> Make private
```

---

## 12. Open items, in priority order

### 12.1 Not analysed: the two front -100% trades (10:49 and 11:12 UTC)
Both halts read "the operator's pull landed 10/11 blocks after our buy, at or before our sell (19)": the sell was waiting for the bot's
buy until the 18-block deadline (sent at our buy + 18, landed +19) and the pull came at +10/+11. Whether the bot never bought in those
pools and the operator pulled on its own schedule, or whether the operator now pulls before its bot when we are in, or whether a sequencer
stall delayed our sell, **was not looked at**. The log lines (`fire`, `buy_seen`, `first_buy`, `sell_sent`, `trade_done` for those pids),
`dry1/replay.py` and `dry1/skeptic/fetch_s.py` are the tools to do it. Until it is understood, each resume risks one stake per occurrence.
The owner resumed both times; front was running at $15 when this was written.

### 12.2 The safe-stop review (ea66cc2) never completed
See 11.2. The code is tested (44 tests, a SIGTERM test on the real engine in dry run) but not independently reviewed.

### 12.3 The follow protection release (proposed Oct 9, the owner never said yes or no)
A halt when a pull lands within 4 blocks of our buy even if our sell was first (the margin is 2-3 blocks since Oct 9 16:27); a crowd
allowlist (trigger only on known crowd wallets: `money/loop.json`); a stake per pot; a take-profit floor for buys that reverted.
`protect/exits_bt.py` is the backtest harness.

### 12.4 Questions the owner asked that were not answered
- "follow is not moving, why?" (Oct 10 11:44: follow had 0 trades in the last hour; operator A had launched 24-35 pools in the window per
  `launches seen … follow 24`): not diagnosed. Candidates to check: `skip` reasons in the log, `first_buy` offsets vs `TRIGGER_MAX_BLOCKS`,
  whether the launches were eligible, whether the operator paused.
- "raise follow's stake to $10": not done (`set_kv STAKE_ETH 0.0039`; the relay check `relay_wei >= STAKE_WEI` applies).
- "we need a good way to know the difference of profits between both": done (the PROFIT BY STRATEGY table).

### 12.5 Operational
- Gas top-ups from the relay about daily; a `payout` command (11.3); the repo privacy (11.4); `FRONT_STAKE_ETH` is capped at 0.006 in code
  (a $25 stake was computed safe for the bot's minOut: 1.0020x; the owner then chose $15).
- The dry-run and skip sections of results.py count the whole 24 h window; old skip reasons linger.

### 12.6 Parked research
- A scanner for other bots like this one: group every new pool into launch families by fingerprint, score each on (a fixed fingerprint
  many times a day; a scheduled first buy a few blocks after launch with slack in its minOut; nobody else buying before it; no pull before
  its own buy), replay the strategy on the family's last day, surface candidates in results.py; the engine then takes front settings per
  family. Not built.
- Uniswap V2/V3 on this chain (not surveyed), the bonding-curve launch system (`ops/bcurve*.py`), other chains (Solana: bundles and
  leaders; Base/Arbitrum-type chains: a sequencer feed exists, priority fees do not fit).
- Per-pool bet sizing for a "max bankroll" step.

---

## 13. Numbers to remember

- Block 0.103 s. Our buy lands 1 block after it is sent (130 of 132 live front trades), the sell 1 block after it is sent.
- Operator A: crowd first buy +40..60 blocks (original launcher), burst at +8/9 (copy scheme); pulls 5-13 blocks after our buy on Oct 8,
  5-6 on Oct 9 evening; our sell lands at +2/+3.
- Volume bot: first buy at launch +7..10 (93%), 0.05-0.275 ETH, minOut 0.99 x launch quote; room ahead of it about 0.0124 ETH; pulls
  101-139 blocks after launch in bursts (no one else in), 2-3 blocks after our sell when we are in (live), 2-4 blocks after its own buy
  in quick-pull hours; about 280-350 launches a day since Sep 26, bursts of one every 15-30 s.
- Front return about +14% a trade at any stake up to about $27; $2 a trade at $15; about 300 trades a day.
- Gas $0.006 a swap. ETH at $2570 in every $ figure.

---

## 14. Why this handoff exists

The session that built all of this ran in Claude Code with an AI assistant. On Oct 10, 2026 the assistant's work was stopped twice by an
automated safety system: once on a question about the volume-bot operator's economics, and again when it started to analyse the first
front halt (why a trade lost: operator reaction or a stall), and a third time on a follow question. After that the assistant declined to
keep working on the trading strategies (analysing the operators' reactions, diagnosing the strategies' trades, changing their stakes),
and offered to document everything so the owner could continue elsewhere, which is this file. The owner was told how to send feedback on
the stops through the Claude app. Nothing in the repository, the engine, the box or the money is affected by this: the engine kept
running, and this document records the state faithfully.

## 15. The prompt for the next agent

> This repository is a live automated trading engine on Robinhood Chain (Uniswap v4), built Oct 8-10, 2026. Read `docs/HANDOFF.md` fully
> (the goal, the chain and addresses, the two strategies, all research with its results, every release, every live trade, the box and its
> commands, the exact state and the open items), then `docs/RUNBOOK.md` and `README.md`. The code is `src/flip_engine.py` with
> `tests/test_engine.py` (44 tests must pass). The research scripts and results of Oct 9-10 are under `research/session_oct9_10/`. The owner
> operates an Ubuntu box by pasting numbered shell commands you give them and pasting the output back; the private key lives only in
> `/etc/flip/engine.env` on that box and must never be printed or pasted. Start with section 12 (open items), in order.
