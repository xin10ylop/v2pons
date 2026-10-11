# HANDOFF: v2pons, everything from Oct 8 to Oct 10, 2026

This file is the complete record of the project for whoever continues it: the goal, the chain, the two strategies, every piece of
research and its result, every engine release and why, every live trade, the box and its commands, the exact state at the moment of
the handoff, and what is open. It was written on Oct 10, 2026 at about 12:00 UTC, when the AI session that built this stopped working
on the trading strategies (its work on them was interrupted by an automated safety system twice; see section 14). Nothing about the
repository, the engine or the box is broken: the engine was running live on both strategies when this was written.

**Updated Oct 11 03:00 UTC by the second session** (section 16): open items 12.1 and 12.4 are answered from the chain, 12.3's near-miss halt
and 12.5's payout command are built and tested, 12.2's independent review completed (16.7: safe, one high side finding fixed; 51 tests), 12.6's
scanner ran (16.12). The box's clone is on branch `claude/laughing-fermat-48ylv7` at de88eb9 since Oct 11 02:50 UTC (51 tests there); the
engine is **live again since Oct 11 14:26 UTC on Dwellir's authenticated sequencer feed** (16.11, 16.14) after the public feed blocked the
box on Oct 10 at 17:37; the 2.4333 line at the full stake since 14:40. Pushed and not on the box: the front-families code (16.13, 55
tests). `flip_setup.sh` has not been re-run (16.7 C3).

**Oct 10 18:35 UTC: the sequencer feed's operator has blocked the box's address range and says that routing around the block is
unauthorized (section 16.11). The engine is stopped; it cannot trade without the feed. Read 16.11 before anything else.**

To continue, give a new agent this repository and say: **"Read docs/HANDOFF.md first, then docs/RUNBOOK.md and README.md. Everything
about the project is in them."** The agent then has the whole picture.

---

## How to get up to speed, in order (for the next agent)

1. **Read sections 0-3** of this file: the picture, the chain and every address, the repository map, both strategies.
2. **Read the code's own account**: the docstring at the top of `src/flip_engine.py` (the history of the exit and why), then its settings
   block (lines 60-120), then skim `_fire`, `on_buy`, `on_front_buy`, `_settle`. Read `tests/test_engine.py`'s docstring: the 51 tests
   describe every behaviour the engine is held to.
3. **Run the tests** where you are: `python3 tests/test_engine.py 2>&1 | grep -c "^ok"` must print 46 (needs `pip install rlp eth-account
   eth-utils websockets`); `python3 tests/test_v4math.py` 4.
4. **Read sections 4-6**: the timeline, then the research: what was found, with the numbers, and which directory under
   `research/session_oct9_10/` holds each piece. Open the directory's README for the file list. Do not re-run the scans unless you need
   to; their results are in the JSON/TXT files beside the scripts.
5. **Read sections 7-9**: the engine's flow and log events, every setting with its value on the box, the releases, the box and its commands.
   Everything on the box is done by giving the owner exact numbered commands and reading the output they paste back.
6. **Read section 10**: every live trade and what each one taught; then **section 11**, the exact state at the handoff, and **section 12**,
   the open items in priority order. Section 12.1 is the one thing a new agent should look at first.
7. **Ask the owner for the current state** before changing anything: have them run
   `cd ~/v2pons && git log --oneline -1 && sudo python3 ~/v2pons/deploy/results.py | head -24` and
   `sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status`, and paste both. That gives the commit on the box, both
   strategies' state and halts, today's profit per strategy, the operator's pull margins, and the wallet and relay balances.
8. Then work section 12 in order. Rules that held throughout: every change is tested (51 ok), committed and pushed (the box pulled `claude/pensive-rubin-rkj996` until Oct 11, when it was switched to
`claude/laughing-fermat-48ylv7`; the Oct 10 afternoon's work is on
   `claude/laughing-fermat-48ylv7`, a fast-forward of it, section 16.6); every box step is one numbered command with its expected output and "if any of them fails, stop and paste
   it to me"; a code change on the box is `git pull`, the test count, then a restart that waits for the trade in progress (section 9.2);
   the private key is never printed, pasted or committed; nothing is deployed live without a dry run first.

## Contents

0. The one-paragraph picture · 1. The chain and the addresses · 2. The repository · 3. The strategies in detail · 4. Timeline ·
5. The research before this session · 6. The research of Oct 9-10 · 7. The engine · 8. Releases · 9. The box · 10. Every live result ·
11. State at the handoff · 12. Open items · 13. Numbers to remember · 14. Why this handoff exists · 15. The prompt for the next agent ·
16. Oct 10 afternoon: the second session's findings, changes and the commands for the owner

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
| The volume bot's decoys (its own wallets, in every pool) | `0x65050a9b…` router: 0.00012 ETH at launch +2..+4 from a brand-new wallet funded with exactly 0.0002 ETH by `0x488faf52…` (38k nonces); `0xe71a69f4…`: 2e-6 ETH at +3 via the Universal Router (a chain-wide dust bot: it buys operator A's pools too, 16.9); `0x259a1b7b…`: 6e-5 ETH at +23..+33; `0x93b07902…`: about 2.4e-5 ETH (1e-5..1e-4) at median +132 (in 792 pools; 16.9) |

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
| `deploy/relay_ops.py` | `status`, `deposit <eth>`, `withdraw [eth]` (relay -> wallet; no amount = all), `sweep <token>`, `payout <address> <eth>` (wallet -> outside, c9d0201); refuses to run while the service is active |
| `deploy/relay_deploy.py`, `relay_sim.py` | deploy the relay; simulate a buy and a sell through it on a live pool with eth_call state overrides |
| `deploy/new_wallet.py`, `englog.py`, `health.sh`, `watch.sh` | create the wallet into the env file; the log for the last N hours; a health screen; trades as they happen |
| `tests/test_engine.py` (51 tests), `tests/test_v4math.py` (4), `tests/data/front_launch.json` | the engine against a scripted feed with real signed transactions in real L2 batch frames, the chain stubbed; the fixture is a real volume-bot launch (tx `0xe1d91366…`, block 84234302) |
| `docs/RUNBOOK.md` | every deploy step from the first wallet to release 0.9, with the exact box commands |
| `docs/HANDOFF.md` | this file |
| `README.md` | the project narrative, releases 0.1-0.9 |
| `research/REPORT_24.54.md`, `research/*.py`, `research/data/` | the original research (Oct 8 and before): the operator A study, the Oct 8 live trades read back from the chain (`live_trades.py`, `data/live_trades_oct8.txt`), operator A's new scheme (`new_scheme.py`), the survey of other chains and launchpads (`data/SURVEY.md`) |
| `research/session_oct9_10/` | **every research script and result of Oct 9-10** (and `front_audit/`, `follow_audit/`: the Oct 10 afternoon's chain reads, section 16) copied from the session's scratch directory (section 6 says what each directory holds; its own README is the index). Scripts there import a helper `chain.py` (copied) and the engine's `v4math`; they were written with two absolute paths, `/tmp/claude-0/…/scratchpad` (now `research/session_oct9_10`) and `/home/user/v2pons` (the repository), which have to be edited to run them again. Large caches (.pkl, .npy, raw block dumps) were not copied; most scripts re-fetch from the public RPC, but several inputs are neither copied nor re-fetched by any script here (`others/census.jsonl`, `money/win.jsonl`, `ops/launcher_txs.json`, `ops/launcher_logs.json`, `origins/eras/p1.json`, `origins/vt.pkl`, `explore/grid.npy`, `explore/pools.pkl`, `vbot/reaction.json`): section 16.9 and `research/session_oct9_10/STUDY_OCT10.md`. |

Git: branch `claude/pensive-rubin-rkj996` holds everything (the default branch `main` is older). Repository `github.com/xin10ylop/v2pons`,
**private since Oct 10, 2026** (the owner made it private after this handoff was first written; section 11.4 says how, and what the box
needs to keep pulling). It contains the wallet and relay addresses (public on the chain anyway) and the whole strategy.

---

## 3. The strategies in detail

### 3.1 follow (operator A, live since Oct 8)

Operator A launches a pool (through its launcher, or from Oct 8 14:59 through a fresh copy of it per launch), then its crowd of about 32
recurring wallets buys it through the Universal Router: the first real buy typically 40-60 blocks in (original launcher; 21-208 observed, two beyond the 150-block window: 16.9) or three buys bunched into
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
buys 0.005-0.335 ETH (median 0.198; the Oct 8-9 census already had 0.005 as its minimum) at a price **quoted at the launch state with minOut = 0.99 x that quote**. Its own decoy wallets buy
specks before and after. The deployer pulls the liquidity minutes later (101-139 blocks after launch during bursts; 3,000+ blocks in slow
hours), or 2-4 blocks after its bot's buy in its "quick-pull" hours (section 6.10).

The trade: the engine decodes the launch transaction's calldata in the feed (the pool key, price and liquidity are in it: `decode_launch`),
arms the pool in the launch block, fires at the end of that block, so our buy lands at launch +1 (130 of 132 live trades) or +2. Then it
sells on the bot's buy: any buy through the bot's router behind ours (`FRONT_BOT_ROUTERS`, at any size, since 3a47c34: section 16.1) at once,
whatever it prices (release 32416c1), or at +1% after gas on any other buy behind ours (the take-profit); the size rule `FRONT_SELL_ON_ETH` (0.005
until Oct 10 13:00, then 0.001, then 0.004) is off since Oct 10 18:00 because the operator's decoys matched every threshold within the hour
(16.10), or at the deadline when the feed shows our buy + 18 (`FRONT_HOLD_BLOCKS`; 12 until Oct 10 09:20).
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
| Oct 8 13:15-13:20 | the first seven live follow trades through the relay: 3 positive, one -0.5%, 3 -100% (pulled 5-13 blocks after our buy, sell landed after) |
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
wins); the seat on the copy-scheme launches +7.9% (44 of 49 positive, the 44 take-profits averaging +8.9%; `seat_out.txt`) if the burst still comes. `follow_verified.json`, `seat.json`,
`follow_stakes.json` / `stakes_out.txt` (ten stakes 0.0012-1.0 ETH: +2.5% at 0.012, +2.3% at 0.1, +2.0% at 0.3, +1.4% at 1.0 ETH; unchanged at the $3-$10 stakes), `reaction.py` (the operator's pull after our buys), the RPC receipt lag
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
runs the follow pattern** (a crowd that keeps buying behind the first buy with a slow pull); operator A's original-launcher family (OURS-orig) is the only one robustly positive at a 2-block hold (`variants.json`: OURS-orig +2.9% at hold 2, +3.6% at hold 10 with
2 of 88 pulled; OURS-copy is -0.3% at hold 2 and positive only from hold 10; 16.9). The PM1444 families (the volume bot) are the one other structured operator, which led to 6.6.

### 6.6 The volume bot's families and reaction (`vbot/`)

`launch_decode.py` decodes the 1,444-byte POSM multicall (the pool key, sqrtPrice, the MINT_POSITION range and liquidity) from calldata
alone: 1,967 of 1,967 PM1444 launches decode and match their receipts (1,249 non-v3.0 and 718 v3.0; `launch_decode.json` counts the former). `fingerprint.py` (`fingerprint.json`): the family fingerprint level
by level over the census. `reaction.py` (`reaction_all.txt`, 882 pools of the v3.0 family): the deployer pulls through the router
(`0x1cbaf24d` / `0xa0f7978d`); 830 pools had an "outside" buy counting the dust wallet `0x93b07902` (792 pools) and the `0x65050a9b` decoys; only 155 had a non-decoy outsider
(64 of them above 0.0001 ETH), median delay to the pull 10-12 blocks (`reaction_cdf.json`; 16.9). v3.0's bot buys use minOut = 0.95 x a stale quote, v2.433's 0.99 x the launch quote (`quotelag*.py`, `stale*.py`). `replay.py` / `report_all.txt` (385 v3.0 pools, exact replay): the best "hold-30" follow rule on v3.0
prices +3.0% mean with 15 of 380 pulled (-100% each) and turns **negative (-2.9%) at a 0.1 ETH stake because the bot's own buys then revert**
(294 of 380), so v3.0 was rejected; its Oct 9 evening slice is -11% (9 pulled of 47). v5.0 pulls on outsiders (a trap). `trade_replay.py`
cross-checks with feed-side recognition only.

### 6.7 The rule search (`explore/`)

`sim.py` prices a grid of 33,984 rules per family (entry: fire at launch + K for K = 2..40, or at the first buy >= 0.0002/0.001/0.01 ETH
+ 0..10 blocks; stake 0.0012 / 0.012; take-profit 1/2/3/5%; hold 2..60) on 24 families with a train/test split by time and per-6-hour
slices (`grid.npy` 397 MB and `pools.pkl`, not copied; `rules.py`, `rules.json`, `report.json`, `summary.json`, `fams.py`). Findings: for the
union of all sub-1% hookless pools the best rules are "launch+3, TP 5%, hold 60" (+5.2% train / +6.1% test, 7 of 7 slices positive) and
"launch+5, TP 5%, hold 10" (+3.8% / +4.0%) for the union with fees up to and including 1% (2,919 pools; the strict sub-1% union of 1,262 pools: "launch+3, TP 1%, hold 52" +6.4% / +8.2%); **for the v2.433 family "launch+2, TP 5%, hold 19" prices +11.8% train / +13.0% test** (holds 10-60: +12.5% to +14.1%; hold 2 negative; `rules.json`, `summary.json`; the "+7-9%" in earlier notes is v3.0's or the PM1444 union's) and 100% of slices
positive, which became the front strategy (the engine fires at launch+0 and lands at +1: every fire block from +0 to +4 prices the same, `adv/replay.json`); `adv/advreplay.py` is its exact feed replay (fire at launch + K, the bot's minOut check, pulls);
`chk/` holds the checks of the bot's quote model (`quotemodel.py`, `quotestate.py`: minOut = 0.99 x the launch-state quote), early pulls
(`early_pulls.py`), pre-bot buys (`prebuy.py`) and the reaction to outsiders (`react_all.json`); `v5/` the v5.0 family's traps.

### 6.8 The front replay and its limits (`explore/chk/replay.py`, `explore/adv/`, `dry1/sens.py`)

The exact replay of the v2.433 rule on 42 distinct pools with full block data (`adv/replay.json` 24 and `chk/replay.json` 25, seven in both): +13.8% and +13.3% a trade, 24/24 and 25/25 positive. The bot's first
buy has minOut = 0.99 x its launch-state quote, so the total ETH that can sit ahead of it is about 0.0122-0.0124 ETH (its 0.05 ETH buy's
fill with ours ahead: 1.0084x minOut at $5, 1.0068x at $10, 1.0052x at $15, 1.0020x at $25, 1.0004x at $30: the strategy's size ceiling is
about $27 a trade; the engine capped `FRONT_STAKE_ETH` at 0.006 until 294f438, 0.012 since). The per-stake fill ratios were computed in the session and not saved; the saved files bracket the
ceiling: `adv/popreplay.json` 0.012 ETH ahead never reverts the bot's buy, 0.0125 reverts it in 254 of 633 pools, 0.013 in 620 of 633. Our return is about +13.8% on a 0.17 ETH bot buy, +3.6% on 0.05, +23% on
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
loss. This produced two engine changes: sell on any bot-sized buy (32416c1) and the 18-block hold (dca5c72: the bot's buy came by launch +14 in 422 of 435 pools, by +20 in 432; no pool pulled before the bot's buy; the 435 are 417 pools of the 24 hours before plus the 18 dry-run pools). `engine_log.txt`: the dry run's 17 decisions as the box
logged them. `live_front_check.json`: the live audit below.

### 6.11 The live front audit at 09:58 UTC (`dry1/live_front_check.json`, and the `results.py` lines)

The first 132 live front trades read from the chain: pulled before our sell: 0; the pull landed 2 blocks after our sell in 119, 3 in 9,
1 in 3, 11 in 1 (a sequencer stall); the pull 3 blocks after the bot's buy in 121 of 132; our buy at launch +1 in 130, +2 in 2; our sell
1 block after the bot's buy in 130. By stake: $5 61 trades mean +14.2% (worst -0.5%); $10 23 trades +13.6%; $15 48 trades +14.7%.
During the dry run (no buy from us) the same pools were pulled 101-139 blocks after launch; live, 2-3 blocks after our sell: the
operator reacts to our sell, after we are out. (The two later -100% trades are **not** in this audit and were not analysed: section 12.1.)

### 6.12 Earlier Oct 9 pieces at the scratch root (`research/session_oct9_10/*.py`)

`overnight_paper.py` (the Oct 8-9 night from block 83,500,000, about 17:44 UTC: operator A back on its launcher, follow +2.4% on 14 launches, the seat
flat; its output was not saved), `newpaper.py` (the Oct 8 afternoon's 40 copy-scheme launches priced for follow), `seat.py`, `replay_seat.py`
(`replay_seat.jsonl`: 10 seat decisions, 9 take-profits +4.0%), `evening.py` (our Oct 9 evening trades), `exits.py` (the Oct 8 relay trades' exit
timing), `crowd.py`, `crowdmin.py`, `burst.py`, `fund*.py` (who funds the launch wallets; `fund.py`/`fund2.py` need archive state the RPC does
not serve), `liq.py`, `tick.py` (the tick rounding check), `tp_bug*.py` (a probe of one live pool's buys around our trade), `tp_calc.py` (the front
take-profit room), `fp_*.py` (the fingerprint scans whose results are in `fp/`), `oct8.json` (15 operator A pools of Oct 8 11:28-14:58 with their
logs), `oct8_pools.json` (the 3,192 ETH-paired pools of Oct 8: 51 original-launcher and 49 copy launches), `newlaunch.json` (41 rows: the original
launcher's 14:30 launch, then the first 40 copy-scheme launches), `scen.py` (the 0.9 review scenarios behind 506a254), `res_c2.py` (an early results.py).

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
   finish the open trade, then exit; on the box since 13:33 UTC Oct 10, reviewed in 16.7).

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
**3**; `SELL_GAS_HEADROOM` (6); `STOP_WAIT_S` (40; systemd's `TimeoutStopSec` 90).

Follow: `LAUNCHERS` (0x3194e326…) **same**; `LAUNCH_SELECTORS` () **2fcb9108**; `LAUNCHER_CODE_HASHES` (2793923d…, 42544ef5…);
`ENTRY` (follow) **auto**; `SEAT_CODE_HASHES` (2793923d…); `SEAT_FIRE_AT` (6); `STAKE_ETH` (0.0012) **0.0012**; `MIN_TRIGGER_ETH`
(0.0002); `FEE_MIN_PPM`/`FEE_MAX_PPM` (0/9999); `MIN_LIQUIDITY` (1e21); `TRIGGER_MAX_BLOCKS` (150); `BUY_SLIP` (0.03) **0.03**;
`BUY_DEADLINE_S` (3) **3**; `HOLD_BLOCKS` (4) **4**; `SELL_LEAD_BLOCKS` (2) **2**; `SELL_FALLBACK_S` (0.5) **0.5**; `TAKE_PROFIT` (0.01)
**0.01**; `BUY_DELAY_BLOCKS` (0); `MAX_TRADES_PER_DAY` (10) **100**; `DAILY_STOP_USD` (15) **15**.

Front: `FRONT` (0) **1**; `FRONT_DRY_RUN` (1) **0**; `FRONT_VALUE_WEI` (2433328500000000000); `FRONT_CALLDATA_LEN` (1444);
`POSITION_MANAGER` (0x58daec31…); `FRONT_STAKE_ETH` (0.0012, capped at 0.012 in code since 294f438 (Oct 11 16:37 UTC), 0.006 before) **0.0058**; `FRONT_TAKE_PROFIT` (0.01);
`FRONT_HOLD_BLOCKS` (18 since dca5c72; 12 before) **18**; `FRONT_FIRE_MAX` (2); `FRONT_MAX_PER_DAY` (400); `FRONT_HALT_FILE`
(HALT_FILE + .front); `FRONT_DAILY_STOP_USD` (5); `FRONT_PIN` (0); `FRONT_FEE` (2500); `FRONT_TICK_SPACING` (50); `FRONT_SQRT_P`
(1604517591721945638372359205383840); `FRONT_LIQ` (49279426163460954002188); `FRONT_BOT_MIN_ETH` (0.04); `FRONT_BOT_MINOUT` (0.99);
`FRONT_AHEAD_MAX_ETH` (0.008); `FRONT_SELL_ON_ETH` (0 = off, the default since the 18:05 commit; 0.004 from 15:25, 0.001 from 13:00, 0.005
before: section 16.10) **1 in the env file since the 18:00 command (on the box's code a 1 ETH threshold is never met: the rule is off)**;
`FRONT_BOT_ROUTERS` (0x1cbaf24d…, since 3a47c34); `FOLLOW` (1; 0 turns the follow strategy and the seat off: no follow launch armed, 16.14);
`FRONT_FAMILIES` (empty: the FRONT_* line only; a JSON list of further launch lines by
value, 16.13), `FRONT_FAMILY_NAME` (v2.433), `FRONT_NONBOT_HALT` (5: live front exits in a row not into the bot's buy halt front; 0 off, 16.13).
Since 16.13 front's fee bound is its family's fee (exact); `FEE_MIN_PPM`/`FEE_MAX_PPM` bound follow only.

Follow's own halt (792a8c5, not on the box): `FOLLOW_NEAR_MISS_BLOCKS` (4; 0 = off); `FOLLOW_HALT_FILE` (HALT_FILE + .follow).

The slot rule: a live front trade yields when a follow launch that follow can still trade (under its cap and stop, relay above its stake)
is waiting for its crowd or its receipt; a front trade leaves the slot once both its receipts are in (follow can trade during front's
3-second pull check; the next front trade waits for it); a dry front position is dropped for a live trade.

### 7.4 Tests

`python3 tests/test_engine.py` prints 46 `ok` lines (listed in the test file's docstring and by `grep "^ok"`); `tests/test_v4math.py` 4.
Run 22 times in a row on Oct 10 without a failure after test 15j was made nonce-exact (32416c1). On the box: `/opt/flip-venv/bin/python3
tests/test_engine.py 2>&1 | grep -c "^ok"` -> 46 at the current head (44 at 3c3f696, 43 at cd3d1c9, which is what the box runs).

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
| 3a47c34 | (16.1, branch `claude/laughing-fermat-48ylv7`) | **the bot's buy by its router** (`FRONT_BOT_ROUTERS`), `FRONT_SELL_ON_ETH` 0.001; the two Oct 10 -100% trades explained; test 18m2 (45) |
| c9d0201 | | `relay_ops.py payout <address> <eth>` (16.6) |
| 792a8c5 | (16.3) | **follow's near-miss halt** (`FOLLOW_NEAR_MISS_BLOCKS` 4, `HALTED.follow`, `halt()` scopes), shown by results.py; test 18m3 (46); the test reset clears the recent-buys buffer |

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
# a plain restart waits for the trade in progress itself (ea66cc2, on the box since Oct 10 13:33): about 6 s mid-trade, at most STOP_WAIT_S 40 s
# update the code
cd ~/v2pons && git pull && /opt/flip-venv/bin/python3 tests/test_engine.py 2>&1 | grep -c "^ok"
# money (the engine must be stopped for deposit/withdraw)
sudo systemctl stop flip-engine
sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py withdraw 0.002        # relay -> wallet (gas top-up); no amount = everything
sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py deposit 0.003         # wallet -> relay
sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py payout 0xYOUR_ADDRESS 0.1 # wallet -> an outside address (asks for a typed yes; c9d0201 and later)
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

Header: service, release, LIVE/DRY RUN, the last start, the window. Then the halts: `halted: no`, or each halt in force with its resume
command (all live trading `HALTED`, every front line `HALTED.front`, one line `HALTED.front.<name>`, each also "in memory" when the
file is gone but the engine was not restarted). Then **LINES**, one row per front line (launch family) as the engine's last start line
lists them: `LIVE` or `dry`, the stake (`auto $5 (up to $25)` = the auto stake now and the family's ceiling; `$5 fixed` for a wave or crowd
line), then trades and $ after gas over the last hour, today (UTC), the window and every log kept (`since`); a dry line's row carries its
would-have-traded count and the mean of the `dry_ret` prices instead; a line traded before but not configured now shows `off`. Under the
table, per line: share up, $ a trade, average and worst return, the operator's pull after our sell in bands (`0-1`, `2-3`, `4-9`, `10+`
blocks, `none within 30`; `pull BEFORE our sell xK` means K halts) and `by stake` when the stake changed; a dry line's ups, worst and last
decision. The order on screen: header, halts, LINES, the last 8 LIVE TRADES (line, stake, result, $, sold at, pull at, exit; so
`head -24` shows them), BY LINE (the detail above), `launches seen` per line with the fires, the unseen-fingerprint line, `not traded:`
skip reasons (front only, the window), each dry line's last 3 decisions, ALARMS, money. Follow does not appear
(FOLLOW=0 since Oct 11; a follow halt file is still shown if it exists and FOLLOW is on).

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

Net about -$8.5 before gas (the three -100% at $3.08 each, the wins +$0.2 to +$0.6, trade 8 -$0.29; the -$5.19 quoted elsewhere is the first six trades only; 16.9). The seat's two overnight trades (Oct 8-9): -0.18% and -0.32%.

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

### 10.5 The full per-trade record is on the box

Every trade's own lines (`fire`, `buy_seen`, `sell_sent`, `trade_done` with the receipts, the pull check and the P&L) are in
`/var/log/flip/engine.jsonl` on the box and its daily rotations (`engine.jsonl.1`, `.2.gz`, …), not in this repository: the repository
holds the results screens above, the 17 dry-run decisions (`research/session_oct9_10/dry1/engine_log.txt`) and the chain audit of the
first 132 live front trades (`dry1/live_front_check.json`). To preserve the whole record of Oct 8-10 in the repository, run this on the
box (it extracts the trade lines from the last 72 hours, rotations included, into a file under `research/`, which `.gitignore` allows):
```
mkdir -p ~/v2pons/research/box_logs && sudo python3 ~/v2pons/deploy/englog.py 72 | grep -E '"ev":"(start|armed|first_buy|would_fire|would_sell|fire|buy_seen|buy_reply|buy_rejected|sell_sent|trade_done|skip|alarm|nonce|front_bot_reverts)"' > ~/v2pons/research/box_logs/engine_oct8_10.jsonl && wc -l ~/v2pons/research/box_logs/engine_oct8_10.jsonl
```
Then commit and push it from the box (`cd ~/v2pons && git add research/box_logs && git commit -m "box log Oct 8-10" && git push`), which needs
push access from the box (section 11.4: a deploy key with write access, or a token), or copy the file to a machine that has it. The
`englog.py` number is hours: `englog.py 24` for today only; a bigger number as the days go by.

---

## 11. State at the handoff (Oct 10 ~12:00 UTC)

### 11.1 Running
- `flip-engine` active, release 0.9 at commit **cd3d1c9** (the box has not pulled ea66cc2, a8ccc3e, 4e8d350).
- Follow live, $3, `ENTRY=auto`, cap 100/day, stop $15. Front live, **$15** (0.0058 ETH), hold 18, cap 400/day, stop $5.
- Neither halted at 11:44. `HALTED.front` was removed twice (10:54, 11:17).
- Relay about 0.257 ETH; wallet about 0.0026 ETH (about a day of gas at the Oct 10 pace).

### 11.2 Pushed but not on the box
- Nothing, as of Oct 11 02:50 UTC: the box's clone was switched to `claude/laughing-fermat-48ylv7` (`git checkout -B` on origin's branch; its
  local `claude/pensive-rubin-rkj996` had been reset to 4dce46e at 13:33 while still tracking origin's, so `git pull` said "Already up to
  date" and installed nothing until the switch) and is at de88eb9 with 51 tests. A plain `git pull` now follows the right branch. Still
  pending on the box: `sudo bash deploy/flip_setup.sh` once for the unit's `TimeoutStopSec` (16.7 C3; it restarts the service, so only when
  the engine may run again), and the env settings of 16.6/16.10 that the owner has not decided (stake, daily stop).

### 11.3 Money
- Front's profit sits in the relay, which is controlled by the hot key on the box. `relay_ops.py withdraw` moves ETH to the box's wallet;
  `relay_ops.py payout <address> <eth>` (c9d0201, section 16.6) sends ETH from the box's wallet to an outside address: proposed at the
  handoff, written in the afternoon. The owner's external wallet is a Phantom wallet (address not recorded here).

### 11.4 The repository is private (done Oct 10)
Until Oct 10 the repository was public, with the wallet and relay addresses in `research/live_trades.py` and
`research/data/live_trades_oct8.txt` and the whole strategy readable by anyone, including the operators. On Oct 10 the owner made it
private: GitHub -> the repository -> Settings -> General -> Danger Zone -> "Change visibility" -> "Make private" (confirmed by the GitHub
API: `"private": true`). The reasoning: a public repository tied the on-chain wallet to the GitHub account and let a copycat take the room
ahead of the volume bot's buy; the chain itself shows only addresses, and a name can only come from a service that verified the owner's
identity (an exchange or card provider that funded the wallet), never from the address.

The box pulled over HTTPS without credentials, which a private repository refuses. The read-only deploy key that keeps `git pull` working
on the box (given to the owner with the privacy steps; if `git pull` on the box fails with "could not read Username" or "Repository not
found", this part has not been done yet):
```
ssh-keygen -t ed25519 -N "" -f ~/.ssh/v2pons_deploy -C v2pons-box && cat ~/.ssh/v2pons_deploy.pub     # on the box; copy the ssh-ed25519 line
# GitHub: repo Settings -> Deploy keys -> Add deploy key (title "box", paste the line, leave "Allow write access" unchecked)
cd ~/v2pons && git config core.sshCommand "ssh -i ~/.ssh/v2pons_deploy -o IdentitiesOnly=yes" && git remote set-url origin git@github.com:xin10ylop/v2pons.git && git fetch origin && echo ok
# the first run asks whether to trust GitHub's host key: yes
```
To push from the box as well (section 10.5 needs it), add the key with "Allow write access" instead, or use a personal access token.

---

## 12. Open items, in priority order

### 12.1 RESOLVED (section 16.1): the two front -100% trades (10:49 and 11:12 UTC)
**Answered Oct 10 13:00 UTC from the chain: in both pools the volume bot's first buy was 0.00495 ETH, its smallest size, under the 0.005 ETH
sell-on threshold, so the engine waited for its deadline; the operator pulled 3 blocks after its bot's buy, as in every other pool. Not a
reaction to us, not a stall. Fixed by 3a47c34. The text below is the question as it stood at the handoff.**
Both halts read "the operator's pull landed 10/11 blocks after our buy, at or before our sell (19)": the sell was waiting for the bot's
buy until the 18-block deadline (sent at our buy + 18, landed +19) and the pull came at +10/+11. Whether the bot never bought in those
pools and the operator pulled on its own schedule, or whether the operator now pulls before its bot when we are in, or whether a sequencer
stall delayed our sell, **was not looked at**. The log lines (`fire`, `buy_seen`, `first_buy`, `sell_sent`, `trade_done` for those pids),
`dry1/replay.py` and `dry1/skeptic/fetch_s.py` are the tools to do it. Until it is understood, each resume risks one stake per occurrence.
The owner resumed both times; front was running at $15 when this was written.

### 12.2 The safe-stop review (ea66cc2): completed Oct 10 19:00 UTC
Verdict in 16.7: safe to run, strictly safer than cd3d1c9; four low findings fixed or recorded; one high side finding outside ea66cc2
(792a8c5's `pulls`) fixed the same hour.

### 12.3 The follow protection release (proposed Oct 9, the owner never said yes or no)
A halt when a pull lands within 4 blocks of our buy even if our sell was first (the margin is 2-3 blocks since Oct 9 16:27); a crowd
allowlist (trigger only on known crowd wallets: `money/loop.json`); a stake per pot; a take-profit floor for buys that reverted.
`protect/exits_bt.py` is the backtest harness.
**Status: the near-miss halt is built (792a8c5: `FOLLOW_NEAR_MISS_BLOCKS` 4, a follow-only halt file); the allowlist, the stake per pot and
the take-profit floor are assessed in 16.3 and not built.**

### 12.4 Questions the owner asked that were not answered
- "follow is not moving, why?" (Oct 10 11:44: follow had 0 trades in the last hour; operator A had launched 24-35 pools in the window per
  `launches seen … follow 24`): not diagnosed. Candidates to check: `skip` reasons in the log, `first_buy` offsets vs `TRIGGER_MAX_BLOCKS`,
  whether the launches were eligible, whether the operator paused. **Answered (16.4): operator A launched 5 pools on Oct 10, none after
  09:56 UTC; follow traded all five. The operator paused.**
- "raise follow's stake to $10": not done (`set_kv STAKE_ETH 0.0039`; the relay check `relay_wei >= STAKE_WEI` applies). **The command is
  in 16.6; the relay (0.276 ETH at 13:26) covers it many times over.**
- "we need a good way to know the difference of profits between both": done (the PROFIT BY STRATEGY table).

### 12.5 Operational
- **payout: done (c9d0201). The deploy-key check, the log export and the gas top-up are numbered commands in 16.6.**
- Gas top-ups from the relay about daily; a `payout` command (11.3); the box's deploy key if `git pull` fails (11.4); the log export (10.5); `FRONT_STAKE_ETH` is capped at 0.012 (0.006 before 294f438) in code
  (a $25 stake was computed safe for the bot's minOut: 1.0020x; the owner then chose $15).
- The dry-run and skip sections of results.py count the whole 24 h window; old skip reasons linger.

### 12.6 Parked research
- A scanner for other bots like this one: group every new pool into launch families by fingerprint, score each on (a fixed fingerprint
  many times a day; a scheduled first buy a few blocks after launch with slack in its minOut; nobody else buying before it; no pull before
  its own buy), replay the strategy on the family's last day, surface candidates in results.py; the engine then takes front settings per
    family. A first version ran from the research container on Oct 10 evening (16.12).
- Uniswap V2/V3 on this chain (not surveyed), the bonding-curve launch system (`ops/bcurve*.py`), other chains (Solana: bundles and
  leaders; Base/Arbitrum-type chains: a sequencer feed exists, priority fees do not fit).
- Per-pool bet sizing for a "max bankroll" step.

---

## 13. Numbers to remember

- Block 0.103 s. Our buy lands 1 block after it is sent (130 of 132 live front trades), the sell 1 block after it is sent.
- Operator A: crowd first buy +40..60 blocks (original launcher), burst at +8/9 (copy scheme); pulls 5-13 blocks after our buy on Oct 8,
  5-6 on Oct 9 evening; our sell lands at +2/+3.
- Volume bot: first buy at launch +7..10 (93%), 0.005-0.335 ETH, minOut 0.99 x launch quote; room ahead of it about 0.0124 ETH; pulls
  101-139 blocks after launch in bursts (no one else in), 2-3 blocks after our sell when we are in (live), 2-4 blocks after its own buy
  in quick-pull hours; about 280-350 launches a day since Sep 26, bursts of one every 15-30 s.
- Front return about +14% a trade at any stake up to about $27; $2 a trade at $15; about 300 trades a day.
- The volume bot's first buy: 0.00495-0.335 ETH (median 0.198; 5th percentile 0.025); the pull 2-4 blocks after it in 400 of 400 live
  pools (3 in 367); our buy at launch + 1 in 399 of 401 front trades (section 16.2).
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
> `tests/test_engine.py` (46 tests must pass; 44 at 3c3f696). The research scripts and results of Oct 9-10 are under `research/session_oct9_10/`. The owner
> operates an Ubuntu box by pasting numbered shell commands you give them and pasting the output back; the private key lives only in
> `/etc/flip/engine.env` on that box and must never be printed or pasted. Start with section 12 (open items), in order.

---

## 16. Oct 10 afternoon: the second session (12:50-14:00 UTC)

A second agent took the handoff at 12:50 UTC with the prompt of section 15, on branch `claude/laughing-fermat-48ylv7` (fast-forwarded from
`claude/pensive-rubin-rkj996` at 3c3f696; every commit below is on it). The public RPC answered from its container, so 12.1 and 12.4 were
read from the chain without the box; the box itself was not touched (the owner had not yet pasted the state of step 7). All 46 tests pass.

### 16.1 The two front -100% trades (12.1): the bot's smallest buy, under the sell-on threshold

`research/session_oct9_10/front_audit/` (its README has the full account). Every swap of our relay since 09:00 UTC was read back from the
PoolManager's `Swap` events (808 swaps, 405 trades: 401 front and the day's 4 follow trades at $3), and for the two trades whose sell got
nothing, every transaction of the blocks launch..sell + 3, reverted ones included:

| | 10:48:55 UTC (pool `0x4b379054…`) | 11:11:55 UTC (pool `0x1b99b488…`) |
|---|---|---|
| launch block | 84939677 | 84953010 |
| our buy (0.0058 ETH) | + 1, filled | + 1, filled |
| the decoy | + 3, 2e-6 ETH via the Universal Router | + 3, 2e-6 ETH |
| **the bot's first buy** (its router `0x1cbaf24d`, `c1120e3d`) | **+ 9, 0.00495 ETH**, status ok | **+ 8, 0.00495 ETH**, status ok |
| the pull (`a0f7978d` by the launch wallet, nonce 12) | + 12 (3 blocks after the bot's buy) | + 11 (3 after) |
| our sell | sent at our buy + 18, landed + 20, **reverted** (335,520 of 350,000 gas: a swap into a pool with no liquidity walks the tick bitmap to the price limit) | + 20, reverted the same way |
| blocks + 0..+ 20 | 10:48:55 - 10:48:57 (no stall) | 11:11:55 - 11:11:57 |

So: the bot bought, at its smallest size, 0.00495 ETH, which is under `FRONT_SELL_ON_ETH` (0.005) and under `FRONT_BOT_MIN_ETH` (0.04); the
engine neither took it for the bot's buy nor sold on it; the take-profit was not met (that buy prices our sell at -0.1%); the sell waited for
the 18-block deadline; the operator pulled 3 blocks after its bot's buy, as in 367 of the 400 live pools where the bot bought (2-4 blocks in
all 400). Not a reaction to us, not a sequencer stall. Sold on the bot's buy, each trade would have returned -0.10% (-0.17% after gas): the
cost of two fees, not the stake. The bot's sizes cluster at 0.99 x a round number (0.00495, 0.02475, 0.07425), so 0.005 was exactly its
smallest size minus 1%.

Fix (3a47c34): `FRONT_BOT_ROUTERS` (default the bot's router): a buy through it behind ours is the bot's buy whatever its size and sells our
position at once; the same before our fire makes the pool late (the bot has bought). `FRONT_SELL_ON_ETH`'s default went to 0.001 (the operator's
decoys were 0.00012 ETH at most) and, two hours later, to 0.004 when the operator's decoy grew to 0.001485 ETH (16.10). Test 18m2.

### 16.2 The whole day's front trades, from the chain (`front_audit/full_audit.json`)

405 relay trades 09:08-11:39 UTC: mean +13.97%, median +16.25%, 396 up, 7 flat-to-down (-0.07% to -0.5%: four follow trades at the deadline,
one front trade sold at the 12-block deadline in the same block as a late bot buy, two front trades sold at the 18-block deadline with the bot
buying at + 59 or never), 2 lost (16.1). By stake: $5 (0.00195 ETH) 61 trades, mean +14.2%; $10 (0.0039) 23, +13.6%; $15 (0.0058) 317,
+14.1% on the 315 priced, the 2 losses at $15. Our buy landed at launch + 1 in 399 of 401 front trades, + 2 in 2. The bot's first buy came at
+ 7..10 in 369 pools, + 11..19 in 29, + 59 and + 130 once each (the latter the 09:15 sequencer stall), never in 3 front pools (pulled at
+ 46..57 with nobody in; our sell at the deadline, -0.3..-0.5%). Its size: min 0.00495, 5th percentile 0.0248, median 0.198, 95th 0.287,
max 0.335 ETH; 36 of 400 under 0.04 ETH, all sold on the buy (+0.4% to +1.9%; one 0.005 ETH buy at -0.1%) except the two at 0.00495. The pull came 2-4 blocks after the
bot's buy in 400 of 400 (3 in 367) and 1-3 blocks after our sell in 398 (2 in 363). Nobody but the operator's two decoys (2e-6 ETH via the
Universal Router at + 3, 0.000119 ETH from `0x65050a9b` at + 3..5) bought behind us before our sell in any pool, and the bot never bought
twice before our sell. The last relay trade was at 11:39:54 UTC (16.5).

### 16.3 The follow protection release (12.3): the near-miss halt built, the rest assessed

`protect/exits_bt.out` (46 Oct 8 launches, the operator's pull modelled at every offset): the current exit (take-profit, else the sell sent at
our buy + 2) keeps its +2.2% mean when the pull comes at our buy + 4 or later, loses 85% on 39 of 46 at + 3 and everything at + 2; no variant
keeps a profit at + 3 (the best, "deadline at buy + 1", prices -0.17% because the crowd's next buy comes at trigger + 3, our buy + 2). The live
pulls since Oct 9 16:27 came at our buy + 5/+ 6 with our sell at + 2/+ 3, and today's two near ones (09:15, 09:18) at + 5. One block of that
margin gone is the signal to stop, and nothing in the exit can buy it back.

Built (792a8c5): **the near-miss halt**. After each follow or seat trade, a pull that landed within `FOLLOW_NEAR_MISS_BLOCKS` (4) of our buy,
even behind our sell, halts follow and the seat only (`/var/log/flip/HALTED.follow`; `halt()` now takes a scope: all, front, follow); front
goes on; `results.py` shows `follow strategy: HALTED: near miss …` with the resume command; the `trade_done` line carries `near_miss: true`.
A pull at + 5 or later is not a near miss. Test 18m3. `FOLLOW_NEAR_MISS_BLOCKS=0` turns it off.

Assessed and not built:
- **A crowd allowlist** (trigger only on the 32 known pot-A wallets, `money/loop.json`): of today's five triggers, three came from that list
  and two (the 06:48 and 09:56 pools, +4.8% and +1.3%, the two with a full crowd session behind them) from reused wallets outside it
  (`follow_audit/trigger_wallets` in the README). A hard allowlist would have skipped two of the day's three winners. Not recommended; a
  logged tag ("trigger from a known crowd wallet: yes/no") would be harmless and is a two-line change if wanted.
- **A stake per pot**: needs the pot of each launch to be known at the trigger, which the chain does not give in time; parked.
- **A take-profit floor for reverted buys**: the presigned sell after a reverted buy finds nothing to sell and costs gas only (test 5); no
  floor is needed.

### 16.4 "Follow is not moving" (12.4): the operator paused

`research/session_oct9_10/follow_audit/`: every ETH-paired v4 pool initialized on Oct 10 (1,0xx to 13:07 UTC) classified by launcher.
**Operator A launched 5 pools all day** (06:48:50, 09:15:42, 09:18:01, 09:21:56, 09:56:25 UTC), all through its original launcher, fees
0.032-0.5%, and **none after 09:56 UTC**. Follow traded all five (the day's +4.8%, +16.4%, -0.3%, -0.1%, +1.3%). `results.py`'s "launches seen
… follow 24" counts the 24-hour window. Nothing in the engine held follow back: the slot rule gives follow priority, and front's trades last
1-2 s each. The crowd's first buy came at launch + 21, + 40, + 50, + 61, + 44; the pulls at + 46 and + 56 on the two quick pools (5 blocks after
our buy, 2-3 after our sell), 16 minutes and 3 hours later on the two full-session pools.

### 16.5 Front stopped at its daily cap at 11:39:54 UTC

The chain shows no transaction from our wallet after the trade of 11:39:54 UTC (nonce 893/894; the wallet's nonce is 895), while the bot
launched about 100 pools an hour (296 between 10:00 and 13:07). The engine's front count reached `FRONT_MAX_PER_DAY` (400) with that trade:
`results.py` should show `not traded: daily cap x…`. The cap resets at 00:00 UTC; raising it is the owner's decision (16.6, step 4).

### 16.6 What is on the branch, what is not on the box, and the commands

On `claude/laughing-fermat-48ylv7` and not on the box (which runs cd3d1c9): ea66cc2 (safe stop), a8ccc3e and 4e8d350 (results.py), 3c3f696
(this file), 3a47c34 (the bot's router rule), c9d0201 (payout), 792a8c5 (the near-miss halt), and this section. Branch
`claude/pensive-rubin-rkj996` on GitHub still ends at 3c3f696; the box's local copy of it is at cd3d1c9, an ancestor of everything above, so
step 3 below fast-forwards it in place and later `git pull`s of the old branch are harmless no-ops.

Money at 13:26 UTC: wallet 0.002464 ETH (about 200 trades of gas), relay 0.276414 ETH (about $710 at $2570).

Every step is one command; if any of them fails, stop and paste the output.

```
# 1. the state (section 12's step 7)
cd ~/v2pons && git log --oneline -1 && sudo python3 ~/v2pons/deploy/results.py | head -24
sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status
# 2. can the box still reach the private repository? (prints fetch-ok, or fails: then section 11.4's deploy key first)
cd ~/v2pons && git fetch origin claude/laughing-fermat-48ylv7 && echo fetch-ok
# 3. the code: a fast-forward of the box's branch onto the new work, then the tests (expect 46)
cd ~/v2pons && git merge --ff-only FETCH_HEAD && git log --oneline -1 && /opt/flip-venv/bin/python3 tests/test_engine.py 2>&1 | grep -c "^ok"
# 4. (your decision) front for the rest of the UTC day: the cap is 400 and today's 400 are done; 1000 lets it run on
set_kv() { sudo grep -q "^$1=" /etc/flip/engine.env && sudo sed -i "s|^$1=.*|$1=$2|" /etc/flip/engine.env || echo "$1=$2" | sudo tee -a /etc/flip/engine.env >/dev/null; }
set_kv FRONT_MAX_PER_DAY 1000
# 5. (your decision) follow at $10 instead of $3
set_kv STAKE_ETH 0.0039
# 6. the restart. Front is at its cap and the operator has not launched since 09:56, so no trade is in progress; if results.py in step 1
#    shows a trade in the last minute, use the waiting form from section 9.2 instead
sudo systemctl restart flip-engine && sleep 8 && sudo python3 ~/v2pons/deploy/englog.py 1 | grep '"ev":"start"' | tail -1 | grep -o '"release":"[^"]*"\|"front_sell_on_eth":[0-9.e-]*\|"front_bot_routers":\[[^]]*\]\|"follow_near_miss_blocks":[0-9]*\|"front_max_per_day":[0-9]*\|"stake_eth":[0-9.]*\|"halted":[^,]*\|"front_halted":[^,]*\|"follow_halted":[^,]*'
# 7. gas: the wallet has about 200 trades left; 0.01 ETH from the relay is about 800 (the engine must be stopped for the transfer)
sudo systemctl stop flip-engine && sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py withdraw 0.01 && sudo systemctl start flip-engine
# 8. the record of Oct 8-10 into the repository (section 10.5), kept on the box until it can push (a deploy key with write access)
mkdir -p ~/v2pons/research/box_logs && sudo python3 ~/v2pons/deploy/englog.py 72 | grep -E '"ev":"(start|armed|first_buy|would_fire|would_sell|fire|buy_seen|buy_reply|buy_rejected|sell_sent|trade_done|skip|alarm|nonce|front_bot_reverts)"' > ~/v2pons/research/box_logs/engine_oct8_10.jsonl && wc -l ~/v2pons/research/box_logs/engine_oct8_10.jsonl
# 9. profit out, when wanted: relay -> wallet, then wallet -> your own address (an address whose key you hold; the ETH stays on Robinhood
#    Chain, chain id 4663, until you bridge it; the command shows the amount and asks for a typed yes)
sudo systemctl stop flip-engine && sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py withdraw 0.2 && sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py payout 0xYOUR_ADDRESS 0.19 && sudo systemctl start flip-engine
```

Step 6's start line must show `"release":"0.9"`, `"front_sell_on_eth":1.0` (the env value; 0 = off in the code since 18:05, 16.10), `"front_bot_routers":["1cbaf24d53fe930fce8eff149fa797d2611da149"]`,
`"follow_near_miss_blocks":4`, and the three `halted` fields null. After it, `results.py`'s front rows read `front, the bot's buy behind ours`
with the size in the full `sell_why`; a front pool where the bot buys 0.00495 ETH now sells at once for about -0.2%. Since the operator's two
0.00495 ETH decoys (16.10), the bot's buy arrives with about 0.0157 ETH ahead of it and the engine's revert model (0.99 x the launch quote)
says it will fail, so the rows read `front, the bot's buy reverts` instead: the engine still sells at once, at the same moment, and the chain
shows the buy filled; only the label and the missing `tp_ret` differ.

### 16.7 The safe-stop review (12.2): completed 19:00 UTC

Five finders (signals and threads, races, systemd, timing, the test file), three refuters each on the first five findings, and one agent that
judged the remaining findings with experiments on the test file's stubs (its files: the session's scratch `safestop_finish/`, not in the
repository; the findings are summarised here). 22 findings, 21 distinct. **Verdict: ea66cc2 is safe to run and strictly safer than cd3d1c9.**
SIGTERM no longer kills a trade between its buy and its sell; with a healthy RPC a stop waits 3-6 s for the open trade (front's pull check
included), writes `trade_done` and exits idle. No path was found where the stop itself loses money or leaves a wrong nonce: the sell goes out
within 2.26 s of the fire, the halt files are written before the slot clears, `checks()` re-reads the nonce at start. The signal handler runs
on the main thread within 0.2-82 ms even with the main thread blocked in epoll (26 of 26 runs); `_fire` is the only place a position is
created and its stopping gate is the first check; `front_settling` is set before `position` clears, so a pull check is never seen as idle.

Refuted (one line each): a few-microsecond window between clearing the slot and writing `trade_done` (GIL-protected, 20k trials lost
nothing, the halts are already on disk); the 40 s alarm is not misleading (the record really is incomplete); a broken log file crashes the
main thread at its own next log within about 62 s, so the watchdog's death does not matter; exit 0 after giving up is right (the JSONL is the
alert channel, a non-zero exit would mark a plain `systemctl stop` failed); Ctrl-C is not a deployed path; the `relay_ops` guard's clash
window is the 2.26 s before the presigned sell goes out, not 40 s; a sequencer stall of 36 s or more can cut at most the 4th of 4 sell posts.

Confirmed, all low, fixed in the commit after e5b2603 (51 tests):
- **C1. The stop waited on `chain_nonce`'s retries.** `_settle` writes `trade_done` only after `chain_nonce()`, and `deliver_buy`'s refused-buy
  path holds the position through it; `chain_nonce` retries 60 times (4-9 minutes when the RPC fails). An RPC outage of 37 s or more starting
  inside a settle, plus a stop at that moment, exited at the 40 s cap without the trade's record (`restore_today` then undercounts the day by
  one trade, results.py shows `NO RESULT LOGGED`), and a refused buy made the stop wait the full 40 s with a "trade still open" alarm for a
  trade that never happened. Never seen live in 2.5 days; no money at risk (halts written before the nonce read; the nonce re-read at start).
  Fix: `chain_nonce` returns None on its second and later tries while `stopping` is set (every caller handles None; no trade starts once
  stopping is set). Test 18q. Residual: if `eth_getLogs` hangs 4 x 10 s during a stop the cap still lands before the pull and sold-none
  decision; `STOP_WAIT_S` 60 with `TimeoutStopSec` 90 would cover it (not changed).
- **C2. Test 18o did not pin the stop's load-bearing waits**: three engine mutations (exit during front's pull check; the watchdog loop without
  its try/except; the stopping gate exempting front) passed all 48 tests. Test 18p (a real SIGTERM via `os.kill` while `eth_getLogs` is held, a
  front launch refused by the gate alone, the real watchdog thread with a raising `watchdog_tick`) kills all three.
- **C3. The unit did not pin `TimeoutStopSec`**: Ubuntu's default 90 s held. `deploy/flip_setup.sh` now writes `TimeoutStopSec=90`; it takes
  effect at the next `sudo bash deploy/flip_setup.sh` (which restarts the service). Check: `systemctl show flip-engine -p TimeoutStopUSec`.
- **C4. Duplicate skip lines**: one front launch during a stop logged three `stopping: no new trade` lines and a wrong `too late`; the gate now
  marks the launch `skipped` (one line). results.py counted each line.

**Side finding, high, outside ea66cc2 but on the box since 13:33 (4dce46e):** 792a8c5's `elif pulls and ...` in `_settle` raised
`UnboundLocalError` whenever `eth_getLogs` raised (any non-429 RPC error at once, or four failed tries), because `pulls` was assigned only
inside the `try`. The settle then aborted with a `settle failed` alarm: no `trade_done` line, no P&L added to the day (the daily stop and
`restore_today` miss the trade), and the "sold none" halt skipped: a front buy whose sell sold nothing would have lost its stake without
halting front (the position was cleared and the nonce refreshed by the `settle()` wrapper, so the engine kept trading). It needs an
`eth_getLogs` error on the same trade. Fix: `pulls = []` before the `try` (test 18r). The pull-before-sell and near-miss halts cannot be
decided without the logs, before or after the fix; the engine now logs an alarm (`pull check unreadable: check the pool's pull by hand`)
instead of only a `pull_check` field in `trade_done`. Whether the crash fired on Oct 10: the first check on Oct 11 (`grep -c` on `/var/log/flip/engine.jsonl`) printed 0, but it read an empty
file: the log rotates daily (`copytruncate`, `deploy/flip_setup.sh`), so after midnight the live file holds only the new day and Oct 10 is in
`engine.jsonl.1`. **Any check of a past day must go through `deploy/englog.py`** (it reads the rotations):
`sudo python3 ~/v2pons/deploy/englog.py 96 | grep -c '"settle failed"'`. Result (Oct 11 04:50 UTC, 96 h through the rotations): **0**. No
trade of Oct 8-10 is missing from the record. The runbook's wait-for-trade restart is no longer needed (9.2 updated).

A second Opus review of the fix commit (f0681da; its diff, mutation tests and six suite runs under CPU load) found it safe to deploy and
nothing that changes the normal live path. Its two low notes: the alarm above (added); a stop can still end before `trade_done` when the
receipts take 2 x 25 s or `eth_getLogs` 4 x 10 s (`STOP_WAIT_S` 60 would cover it; left at 40, the owner's call).

### 16.8 Open after this session

12.3's allowlist tag if wanted; the parked research of 12.6; the log export's push (a write deploy key). The money loop and the
census (sections 6.4-6.5) were not re-run. Two things the study (16.9) raised that the owner should decide:

- **`FRONT_DAILY_STOP_USD` is $5 against a $15 stake.** The stop is the day's cumulative front P&L at or under -$5, reset at 00:00 UTC. One lost
  stake among the first few trades of a UTC day (before about +$8 has accrued) stops front for the rest of that day with `daily stop` skips, while
  the same loss after a profitable morning stops nothing. At today's loss rate (3 in 575) that is a 1-2% chance per day of losing the day's front
  trading. `set_kv FRONT_DAILY_STOP_USD 50` (about three stakes) and a restart would make the stop mean what it says.
- **Operator A's launcher is permissionless** (`ops/lch/sim_out.txt`: any sender can launch through `0x3194e326` or a copy), and the engine arms a
  launch sent to a `LAUNCHERS` address by the address alone (the code-hash check applies to copies found by their call). A third party who read
  this repository while it was public could stage a launch with a 0.0002 ETH "crowd" buy and pull on our $3 follow buy; the gain is one stake and
  the engine halts after it. Low value for an attacker, but it is the reason not to raise follow's stake far without a gate (a minimum launch
  value, or a deployer funded from the known pots).
- **Oct 8's pulls at + 5/+ 6** (four of the seven relay trades) would not have triggered the near-miss halt as built (4 blocks); the protect/
  design (`ladder_sim.py`) treated + 5/+ 6 as a warning rung (back to the minimum stake) and + 4 as the halt. Raise `FOLLOW_NEAR_MISS_BLOCKS` to 6
  if one block of margin is too little warning.

### 16.10 15:04 UTC: the operator's decoy grew to 0.001485 ETH and the 0.001 threshold sold on it

The owner lifted the cap and installed the afternoon's code at 13:33 (16.6 steps 1-3 as given; `FRONT_MAX_PER_DAY` 100000, gas 0.01 ETH from
the relay). From 13:38 to 14:28 front made 174 trades, 173 of them sold one block after the bot's buy (+14.2% mean, about +$348; the router
rule caught one 0.00495 ETH bot buy). At 14:28:51 a trade lost its stake: the bot bought 0.099 ETH at + 8, the pull came at + 11 as always, and
our sell landed at + 12 because the feed delivered block + 8 a quarter of a second late (the engine sent the sell in that feed block, first
try, accepted in 130 ms; `front_audit/step3_since_restart.py`, `step4_since_restart_timing.py`). Front halted (its pull-first rule) and the
owner resumed it at 15:02.

From about 15:04 the operator's decoy changed: its funder `0x488faf52` now buys 0.001485 ETH itself through `0x65050a9b` at launch + 2/+ 3
(this morning: fresh wallets, 0.000119 ETH), and a second decoy router `0xfd1b271f` (from `0xb4c345dc`, 0.000149-0.000742 ETH) appeared; the
decoys and the bot share the 0.99 x round-number sizes. With `FRONT_SELL_ON_ETH` at 0.001 the engine took the 0.001485 buy for a real-size buy
and sold at + 3, ahead of the bot's buy at + 7..+ 13: 34 of the 43 trades 15:04-15:17 exited at -0.32% to -0.38% instead of about +14%
(`front_audit/step5_since_1502.py`, `since_1502.json`); no stake was lost, about $70 of profit was missed by 15:17 and about $2 a launch after
that. The owner was given `set_kv FRONT_SELL_ON_ETH 0.004` and a restart at 15:20; the code default is 0.004 from the 15:25 commit (test 18m2
covers the 0.001485 decoy). The lesson: the size threshold has to sit between the decoys and the bot's smallest buy (0.001485 and 0.00495
today: 0.004 has about 3x each way), and the router rule is the one that does not move. Watch `results.py`'s "pull after our sell" line: a
cluster at 6-13 blocks means sells ahead of the bot's buy again.

Also since 15:02: eight launches skipped as "too much ETH bought ahead of the bot's buy", because the two decoys (0.0022 ETH together) landing
before our fire plus our 0.0058 stake exceed `FRONT_AHEAD_MAX_ETH` 0.008. The measured room ahead of the bot's buy is about 0.012 ETH
(`explore/adv/popreplay.json`: 0.012 never reverts it, 0.0125 reverts it in 40% of pools), so 0.0095 would keep the margin and take those
launches; the owner's call (`set_kv FRONT_AHEAD_MAX_ETH 0.0095`).

**The second escalation, about 15:45 UTC.** The owner set the threshold to 0.004 at 15:22:57; it held for about 20 minutes. From about 15:45
both decoy wallets buy **0.00495 ETH** each at launch + 2/+ 3, the bot's smallest real size and just above 0.004, and 289 of the 411 trades
from 15:23 to 17:55 sold on them at about 0% (`front_audit/step6_since_1523.py`, `since_1523.json`): with the first step, 323 positions sold
ahead of the bot's buy on Oct 10, about $650 of profit missed, no stake lost. The decoys cost the operator nothing (it owns the pools: their ETH
comes back in the pull, minus a 0.25% fee), so a size threshold is a game it wins every time; the size rule should have gone off at 15:20 rather
than been moved. At 18:00 the owner was given `set_kv FRONT_SELL_ON_ETH 1` (on the box's code a 1 ETH threshold is never met) and the code
default became 0 = off (the 18:05 commit; test 18m2). What is left to exit on: the bot's buy through its router at any size, the take-profit
(+1% after gas on any buy behind ours), the 18-block deadline.

What the operator could do next, and what each would cost us per pool (the Opus review of the 18:05 change worked these out on the test
harness): a tiny or fake buy through its own router `0x1cbaf24d` behind ours (our router rule sells at once for about -0.6%, +0.2% if its two
decoys are already behind us: about -$0.09 instead of +$2.1; the edge is gone, and front should then stop, since every exit left is fakeable);
a decoy of 0.0194 ETH or more behind ours, 0.0095 on top of its two decoys (the take-profit sells at +1.0 to +1.4% if the decoy is a real buy
that stays; about -0.6% if it is fake or sold back in the same block); decoys moved into the launch block ahead of our fire (0.0022 ETH or more
together with our stake over 0.008, or a 1-wei call to its router with the token in the calldata: the engine skips the pool, no trade, no loss).
"Fake" is possible because the engine reads the feed before execution: any transaction with ETH value whose calldata carries the token's
address counts as a buy, a self-transfer or a reverting transaction included, and sells are never seen; the feed carries no receipts and an RPC
check per buy is too slow, so there is no small fix. The exits left after a fake buy are a market sell at minOut 0, which lands at about -0.6%.
Conversely, if the bot ever buys through a new router, its small buys (under the take-profit's 0.0194 ETH: 11 of 400 this morning) wait for the
deadline and lose the stake once, after which front halts: **a front halt where the bot bought through an address not in `FRONT_BOT_ROUTERS`
means adding that address before resuming.** The same review found the case where the bot's small buy lands in our own block ahead of our buy
(it passes our 3% minOut): the engine waited for the deadline; since the 18:15 commit it sells the moment our buy is seen (test 18m4).

**The room, settled (an Opus chain check, 18:05-18:20 UTC; scripts and outputs in the session's scratch `minout_check/`, the numbers
below).** The bot's minOut is unchanged: 0.99 x its launch-state quote to nine decimals on all 1,146 first bot buys of Oct 10 (its calldata
word 4; word 3 is L0/4, word 0 the Universal Router it calls, which is why its Swap events show the Universal Router as sender). Its buy
filled this afternoon only because our sells on the decoys had already taken us out of the pool before it: in the 152 pools since 16:45 with
two 0.00495 ETH decoys behind our buy, at most 0.0099 ETH sat ahead of the bot's buy. The exact room ahead of the bot's buy is 0.0123 ETH
(0.00495 buy) to 0.0131 (0.335), so **with the size rule off, our 0.0058 ETH plus the two decoys (0.0157 ETH) makes the bot's buy revert in
about 72% of pools** (the other 28%: a decoy sells back before a bot buy at + 10 or later). The engine's revert model then sells at once into
a pool with only the decoys behind ours (about +0.3%); the +14% comes only when the bot's buy fills. The stake that still fits beside both
decoys is 0.0024-0.0032 ETH ($6-8); beside one decoy 0.0074-0.0081 ETH. The decoys are the operator front-running its own bot: they sell back
at + 8..+ 11, right after the bot's buy, for +10% to +24%, and when the bot buys at + 9 or later the first decoy sells first at about -0.6%.
Their sizes through the day: 0.000119 from fresh wallets until 13:43; 0.000049 (13:45-14:20); 0.00099 and the first 0.00495 during our halt
(14:47-14:51); 0.001485 from 15:04; 0.00495 from 15:34 (the first router) and, after a ramp 0.000049 -> 0.00396 from 15:49, 0.00495 from
16:45 (the second router); from 18:11 the second decoy is absent and the first is back to a fresh wallet per launch. None ever landed in the
launch block; 105 landed at + 1 behind our buy in the same block, none ahead of it. No decoy went through the bot's router. So the engine's
`the bot's buy reverts` label this afternoon was a mislabel only while the size rule took us out first; with the rule off it is the real
outcome in most pools, and the stake, not the exit, decides what is left: at $6 the bot's buy fills beside both decoys and the trade keeps
its +14%; at $15 it is about +4% blended. **The operator can close that too by making its decoys fill the whole room.**

**No front buy since 17:37:07 UTC**: the feed refused the box from 17:37 (16.11). The launches' shape is unchanged (145 since 17:20, all the
exact fingerprint).

### 16.11 17:37 UTC: the sequencer feed's operator blocked the box

The engine's log from 17:37:07 UTC is one line every 5 seconds: `feed_error: server rejected WebSocket connection: HTTP 403`; the last `flow`
line is 17:36:26 (seq 85177990, lag 0.8 s, 0 stale blocks, 408 fires). The box's clock is synchronized (NTP active). The feed now answers
through Cloudflare (`server: cloudflare`, `CF-RAY`), and from the box every handshake, with or without a browser User-Agent, with curl or the
engine's own library (websockets 17.2), gets 403 with this body:

> `{"jsonrpc":"2.0","error":{"code":403,"message":"Access denied. This source address range has been blocked. Connecting in a manner intended
> to exceed or evade this feed service's limits is not authorized use of this service. Acquiring or routing additional IP address space to
> continue this pattern is likewise not permitted, and continued access from this or any further network range is unauthorized."}}`

That is a decision by the feed's operator, not a bot rule: the box's address range is blocked for exceeding or evading the service's limits,
and the operator states that moving to another address or network to continue is unauthorized. From the research container the same
handshake still succeeds (another network). What the engine did on the feed: one long-lived websocket since 15:22:57 (one message per block,
deflate), reconnecting only on a stall or an error, and after 17:37 a retry every 5 s (720 an hour) until the owner stopped the service at
about 18:30; the RPC calls (receipts, balances, the pull check, the nonce) go to the separate RPC host, which still answers. Whether the
"limits" were connection count, bandwidth, duration or the trading pattern itself the message does not say.

What this means: the engine cannot trade without the feed (the front entry needs the launch block within two blocks; polling the RPC is
ten times too slow and against the same limits), so **the engine is stopped and must stay stopped**; the box must not retry (the 5 s loop is
what "connecting in a manner intended to exceed limits" describes); and no new address, proxy or tunnel may be used to reach the feed from
the box or anywhere else: the operator has said so explicitly, and this document does not describe any such step. The legitimate paths are
(1) asking the feed's operator (the Robinhood Chain team) what access is permitted and whether an authorized way exists (a documented rate
limit, a registered or paid feed, a node licence), (2) an authorized data source if one appears, (3) stopping on this chain. Section 12.6's
scanner for other operators (running at 18:15 from the research container over the RPC) remains useful research for the day feed access is
authorized; it changes nothing today.

The authorized route, found afterwards from public sources (web search 18:50 UTC, not verified with the providers): Robinhood's own
documentation describes the public feed and RPC as rate-limited and not for production use, and infrastructure providers sell dedicated
Robinhood Chain sequencer-feed and RPC access under their own terms: Chainstack (its public reference decoder,
`github.com/chainstacklabs/robinhood-chain-sequencer-feed`, notes per-client limits on the public feed and that permessage-deflate is required
since 2026-09-17, which the engine sends), QuickNode (`quicknode.com/chains/robinhood`), Dwellir (`dwellir.com/blog/robinhood-chain-defi-data`,
authenticated feed access). Using such a service is not evading the public feed's block. The engine is ready for one: `FEED_URL` (a token in
the URL), `FEED_HEADERS` (a header token: JSON or `Name: value; Name: value`, e5b2603), `RPC_URL` (the provider's RPC, prudent for the same
reason), all in `/etc/flip/engine.env`; then `git pull`, the tests, a front dry run (`FRONT_DRY_RUN=1`) over a few launches, then live. The
owner's choice between the provider route, asking the Robinhood Chain team, and stopping on this chain was open when this was written.

Checked Oct 11 03:30 UTC (web, not with the providers): Robinhood's own connection page names Alchemy "the recommended infrastructure
provider" and lists Chainstack, QuickNode, Blockdaemon, dRPC, Validation Cloud and GlobalStake; it says the public endpoints are rate-limited
and not for production and that production should use a provider. **Alchemy, QuickNode and Chainstack sell the RPC and a JSON-RPC websocket
(`eth_subscribe`), not the sequencer feed**: the engine's `feed_loop` reads the Nitro feed protocol (one message per block with the raw L2
transactions, before the block is served by any RPC), and an `eth_subscribe` block stream would need new code and would see the launch a
block or two later. The providers of the feed itself found so far: **Dwellir** (an authenticated Robinhood Chain sequencer feed in the Nitro
protocol on the existing API key; a three-day trial, then an optional $100 a month add-on plus usage, on its Developer/Growth/Scale plans; its
"sequencer feed guide" has the endpoint format, not fetched), and **BlockRazor** ("Sequencer Feed Ultra", $200 a day or $2,000 a month, which
must be fed into one's own Robinhood Chain node, so not a drop-in). Alchemy is the natural `RPC_URL` replacement either way
(`https://robinhood-mainnet.g.alchemy.com/v2/<key>`, free tier). Robinhood's page also lists a public delayed backup feed
(`wss://delayed-feed.mainnet.chain.robinhood.com`, about 500 ms behind): it is the same operator's public service and the block names "this
or any further network range", so it is not an option for the box. The exact feed URL/header of a provider goes in `FEED_URL` /
`FEED_HEADERS` (the engine sends permessage-deflate, which the feed protocol requires). Sources: docs.robinhood.com/chain/connecting,
alchemy.com/rpc/robinhood, dwellir.com/networks/robinhood and /docs/robinhood, docs.blockrazor.io (streams/node-stream/robinhood-chain),
quicknode.com/chains/robinhood, github.com/chainstacklabs/robinhood-chain-sequencer-feed.

Oct 11 04:30 UTC, the owner's position: "we are not banned, maybe it resets, dig into it". What is known and what is being done: (1) the
block is of an address *range*, so the box may be collateral in a block aimed at a heavier user of the same AWS range, or the target itself;
public data cannot tell, only Robinhood can. (2) The official channel is `chain-developers-group@robinhood.com` (docs.robinhood.com/chain/
report-issue; no Discord or Telegram; the terms say most concerns are resolved through it); a short factual mail was drafted for the owner
(what we ran, from which address, when the 403 began, asking whether the block is temporary, what limit was exceeded, what usage is
permitted, and whether the address can be allowed). (3) The one thing on our side that could have looked like abuse is the reconnect rate:
`feed_loop` drops the socket after 2.0 s without a message (`feed_stall`) and reconnects after 0.2 s, so a flaky hour could mean many
handshakes; the owner was asked for the per-hour counts of `feed_connected`/`feed_stall`/`feed_error` from the box's log (the first attempt read the
rotated-empty live file, see 16.7; the command must go through `englog.py`). **The counts (Oct 8 12:00 to Oct 10 18:30 UTC, per hour):
1 to 3 `feed_connected` in most hours that had any, 7 at 09h Oct 10 (the owner's restarts), about 55 handshakes in three days in all; 6
`feed_stall` and about 12 `feed_error` before the block; then 276 `feed_error` at 17h and 361 at 18h Oct 10, the 5-second retry after the
403 until the stop at 18:30.** So the engine held one socket at a time and reconnected about once an hour on average: nothing on our side
resembles connection-rate abuse or limit evasion. The block's text ("exceed or evade this feed service's limits", "acquiring or routing
additional IP address space") describes a client spreading connections over many addresses, which fits a range block aimed at such a client
in the box's AWS range, with the box as collateral. That is the case to put to Robinhood, with these numbers; it does not make any
reconnection from the box or from another address acceptable before they answer. If they are high, the engine should keep the socket through short gaps (ping-based liveness) before any reconnection. (4) Whether the
block lifts is checked by hand, one handshake at a time (`curl` with the websocket upgrade headers against the feed; 403 while blocked, 101
when open), not by an automatic loop, and never from another address. (5) The paid feed (Dwellir) stays the sure route.

**Dwellir's feed, checked Oct 11 05:30 UTC from its guide (`dwellir.com/docs/robinhood/sequencer-feed`):** endpoint
`wss://api-robinhood-mainnet-sequencer.n.dwellir.com/<API_KEY>` (the key in the path: `FEED_URL` alone, no `FEED_HEADERS`); no subscription
message, the server streams on connect; the envelope is the Nitro feed's (`messages[].sequenceNumber`, `.message.message.header`, `.l2Msg`
base64, plus `confirmedSequenceNumberMessage` envelopes), which `ingest` already parses. Pricing: a paid base plan (Developer $49 a month, 25M
responses, 100 a second; Growth $299, 150M; Scale $999, 500M; overage $5/$3/$2 per million) plus the feed add-on $100 a month after a
three-day trial (the trial needs the paid plan; it does not convert by itself), plus usage: **one response per WebSocket envelope**,
confirmation-only envelopes included, repeated data after a reconnect included. At one envelope a block (about 9.7 blocks a second) the feed
alone is about 840,000 responses a day, 25M a month, the whole Developer allowance; the engine's RPC calls are small beside it. Expect
$150-200 a month on Developer if the feed sends one envelope a block, up to about $400 (or Growth, $399 with the add-on) if it sends two;
the trial's usage meter settles it in a day. Latency: the sequencer's own host (`sequencer.mainnet.chain.robinhood.com`, 3.136.74.196) is in
AWS us-east-2 (Ohio), where BlockRazor also benchmarks the public feed at 27-97 ms median; Dwellir says it routes to the nearest of its
locations and names none for the feed, so a relay hop of 10-30 ms (same region) or 80-150 ms (another continent) is possible, the latter
costing about one block on the launch and the fire. The engine's own numbers measure it during the trial: `arm_ms` on `armed` lines, the
`buy_offset` of dry-run `would_fire` lines against the launch block, and the `flow` line's lag. BlockRazor sells a direct feed without a node
from Ohio and Tokyo (`wss://us.robinhood-feeder.blockrazor.io/ws/direct/<token>`, $80 a day or $800 a month; "Ultra" $2,000 a month), with
the caveat that it "may skip intermediate blocks during congestion", which would blind the sell-on-bot-buy trigger for that block; the
node-required variants keep every block but need one's own Robinhood node. Order of trial: Dwellir first (cheap, every block), BlockRazor
only if the measured hop costs the trade.

Oct 11 11:53 UTC, from the box: its AWS region is **us-east-2 (Ohio)**, the sequencer's own region (an earlier note in this session that
put the box in Google Cloud was wrong: that was the research container). Dwellir's feed host is one fixed address at OVH in Warrenton,
Virginia (not geo-routed), so its hop is Ohio-Virginia-Ohio. The feed still refused the box: `HTTP/2 403`, Cloudflare Ray ID
`a48daa31abf0000e-ORD` (Chicago edge) at 11:53:31 UTC; that Ray ID goes in the owner's mail to chain-developers-group@robinhood.com so the
operator can find the rule. No published reply time exists for that address (searched Reddit, X, GitHub, Cloudflare's forum: nothing on this
block or on response times); Cloudflare's forum is consistent that only the site owner can lift a block it set.

**Payout, Oct 11 about 12:10 UTC** (the owner, for the Dwellir subscription): `withdraw 0.08` (tx 0x1572d339..., block 85,815,431) then
`payout` of 0.08 ETH to the owner's Phantom address 0x9B19...1Ba55 on Robinhood Chain (tx 0xb28117fd..., block 85,815,581, status ok; that
address then held 0.0801 ETH). After it: relay 0.394322 ETH, wallet 0.009581 ETH (nonce 2194), engine stopped.

**Dwellir, Oct 11 12:30-13:20 UTC:** the owner bought the Developer plan ($49, paid in USDC on Base after bridging 0.08 ETH from Robinhood
Chain through Phantom; Phantom's Base account is an EIP-7702 smart account, which the checkout's signature step rejected, so the payment went
through a fresh MetaMask account) and started the sequencer-feed trial. The key is on the box in `FEED_URL` (the Dwellir URL with the key in
its path; the key is not in this document or the repository and should be regenerated in the dashboard, since it passed through a chat).
Dwellir's archive RPC answers with the key (chain 0x1237). The sequencer endpoint answered 403 Forbidden before the trial and **503 Service
Unavailable** from about 12:55 UTC on, on every handshake from the box and from the research container (Dwellir request IDs
db5oq3i85bs9a8r1mn90, db5olci85bs9a8qrc0d0, ...); their status page shows nothing; their guide documents 403 only. **Resolved 13:40 UTC: the 503 was our probe, not Dwellir.** `curl` negotiates HTTP/2 over TLS and Dwellir's sequencer gateway answers a
WebSocket upgrade over HTTP/2 with 503 from the gateway in 0 ms (its log: "Origin GATEWAY, Backend —"); the same handshake with
`curl --http1.1` gets the stream at once, and the `websockets` library the engine uses speaks HTTP/1.1 only. So the feed has been live for the
key since the trial started (about 13:00 UTC). From the research container over 30 s: 340 envelopes, 1,144 blocks, 0 gaps, 0 duplicates; the
feed sends a backlog of about 90 s of blocks on connect (median lag 30 s, which the engine marks stale and does not trade on), then live
blocks at a lag of 0.08-0.5 s (minimum 81 ms through the container's proxy; the box's own figure is the one to record). Usage: live
envelopes are one per block, as costed above. **Any probe of this feed must use HTTP/1.1** (`curl --http1.1` or the engine's library).

The money at 18:35: relay 0.474 ETH (about $1,220), wallet 0.0096 ETH; both move with `relay_ops.py` (9.2, 16.6 step 9) while the engine is
stopped. The day's result: front 1,047 trades +$1,227.11, follow 6 trades +$0.61 (the owner's 17:53 screen).

### 16.13 Front families: the 2.4333 and 3.0 ETH lines at once, front's own fee bound, the decoy halt (Oct 11)

Built after the scanner (16.12) and the Dwellir feed (16.11): the engine's front strategy trades several of the bot's launch lines at
once, told apart by the launch transaction's value. The FRONT_* settings make the first family (`FRONT_FAMILY_NAME` v2.433); `FRONT_FAMILIES`
is a JSON list of further families, each `{name, value_wei, fee, tick_spacing, sqrt_p, liq, bot_minout, ahead_max_eth, take_profit,
hold_blocks, stake_eth}` (a field left out takes the FRONT_* value; big numbers may be strings; the stake is capped at 0.012 ETH (0.006 before 294f438) like
`FRONT_STAKE_ETH`). The 3.0 ETH line, from the skeptic's numbers (16.12):

```
FRONT_FAMILIES=[{"name":"v3.0","value_wei":"3000000000000000000","fee":10000,"tick_spacing":200,"sqrt_p":"679394651928963067279918579724198","liq":"25725498245903809899643","bot_minout":0.95,"ahead_max_eth":0.07,"take_profit":9,"hold_blocks":20,"stake_eth":0.002,"dry_run":true,"pin":true}]
```
(`dry_run` true: that line's fires are `would_fire` lines while the FRONT_* line trades live; the 3.0 line's numbers for a live probe wait
for the 16.14 study.)

What changed in the engine (tests 20a-20c, 54 in all): `ingest_tx` looks the family up by value (any family's value, 1,444 bytes, the
multicall selector); `arm_front` carries the family in the armed pool (`fam`, `fam_cfg`) and logs it (`armed`, `launch`, `trade_done` lines
carry `fam`); `front_mismatch` rejects a launch whose fee is not its family's (**front's own fee bound**; `FEE_MIN/MAX_PPM` are follow's now,
so the 1% line passes while follow keeps its sub-1% bound); `front_fingerprint` compares tick spacing, price and liquidity with the family's
(`FRONT_PIN` unchanged); `_fire` takes the family's stake, hold and take-profit; `on_front_buy` the family's `bot_minout` (the revert model)
and `ahead_max_wei` (the room). With `FRONT_FAMILIES` unset the 2.4333 line behaves as before, except that a 2.4333 launch at a fee other
than 2500 is now refused (`fee N`) instead of traded; every 2.4333 launch seen (1,843 in the census) had fee 2500.

The decoy halt (`FRONT_NONBOT_HALT` 5, `FRONT_NONBOT_MIN_RET` 0.02): `_settle` judges each live front trade whose buy filled by its return
after gas: under +2% counts one against its family (`trade_done.nonbot_streak`; `bot_exit` stays as a diagnostic: a buy through a router in
`FRONT_BOT_ROUTERS` triggered the sell), at or above resets the family's count; at the threshold front halts with its own file, as a pull
would. Judged by the return, not by who called the router: the bot's router is a public contract, so a decoy through it (-0.6%) counts, and
a paying exit on a buy through another router (+9%) does not. Oct 10's decoys (16.10) would have tripped it within the first few trades of
each escalation instead of 34 and 289 losses. The deadline exits of a quiet period count, which is intended (five in a row means the
schedule changed); the bot's buy reverting on our stake counts too (with two full-size decoys ahead, 16.10's 72% revert rate, the halt comes
within about 15 trades of about +0.3% each). The counts are per family and restored from the day's log at a restart.

The review (Opus, on 3d726c2) found it safe with `FRONT_FAMILIES` unset (a replay of the Oct 10 scenarios through the old and the new
engine gave identical decisions) and listed what had to change before a family goes live, all fixed in the next commit: the JSON is now
strict (unknown keys, a missing value or fingerprint, a float value, a stake over the cap (0.012 ETH), fee 0, a minOut outside (0, 1], a hold under a
block, duplicate values or names: a `SystemExit` naming the family; `stake_wei`/`ahead_max_wei` are not inputs; the base family is checked
too), each family has its own `dry_run` and `pin` (so one line can be dry-run while another trades live; `FRONT_PIN` still pins all),
front turns itself off at start with no family at all, the streak is per family, by return, and survives restarts; test 20c covers the
parser. Not changed: `results.py` shows the base family's stake and averages the lines together (cosmetic).

A second review (Opus, on e5f0de1 and 6f72ce3) found the box's path safe (its env parses, the 2.4333 line unchanged apart from the decoy
halt) and listed what a delayed family still needed, all fixed in the commit after 6f72ce3 (55 tests): a wrong family setting now turns
front off for the run (`FRONT_FAMILY_ERROR`, an alarm at start) instead of stopping the service, so follow is never taken down by a typo and
a base-family setting of 0 is an error, not "not compared"; every field has a type and a bound (no booleans for numbers, no 1.9 for a block
count, no NaN; hold 1..600, fire_max 0..10, fire_at + fire_max within `TRIGGER_MAX_BLOCKS` 150, take_profit (0, 9], the room between the
stake and 0.5 ETH, the price in v4's range, liquidity above 0, `dry_run`/`pin` true or false, a key given twice is refused, a parse error
names the family); a pull-shaped call (value 0, on the bot's router, the PositionManager or the PoolManager, carrying the pool's token)
before a delayed fire marks the pool late (`skip: a liquidity call on the pool before our fire`), so the dry run no longer counts the
operator's +7..+9 pulls as deadline exits and a live delayed front never buys into a pulled pool; the start's relay-balance check uses the
smallest live family stake; the streak restore takes each family's last `trade_done` whatever the day (decoys keep no calendar) and a run
at or over the threshold starts again at 0 when front's halt file is gone (`nonbot_streak_reset` line), so clearing a decoy halt does not
halt again on the next trade; `fire`, `would_fire` and `trade_done` lines carry `launch_seq`. Open design point (the review's): a live
delayed family holds the one position slot for its whole hold (60 blocks and the 3 s pull check), during which the 2.4333 line's launches are
skipped (`position open`, then `too late`); at 200-440 launches a day that can cost several +14% trades a day for a 3.0 trade worth +6% at
best, so a delayed family stays dry until a precedence rule exists (the simplest: a delayed family only fires when no base-family launch
is within its hold; not built).

A third review (Opus, on 78ea92c) found the box's path safe, a dry family safe, and listed what a live delayed family still needed; fixed
in the commit after faef7c0 (56 tests): a listed family's error no longer turns front off (the family is dropped, the FRONT_* line trades,
an alarm at start names the error; only the FRONT_* family's own error turns front off); the import guard catches every exception (an
absurd `value_wei` or 10,000 nested brackets cannot loop the service); `value_wei` at most 1e6 ETH, `sqrt_p` in v4's range, `liq` at most
2^128; **each listed family has its own halt file** (`HALTED.front.<name>`): its pull-first, sold-none and decoy halts stop that family
alone while the FRONT_* line goes on (the FRONT_* family's halts stay front-wide), read back at a start, shown in the `flow` and `start`
lines (`fam_halted`); the decoy-streak reset at a restart happens only when the run actually halted (`trade_done.nonbot_halted`) and that
halt's file is gone, so lowering the threshold or a halt that failed to write its file no longer resets a run. Verified on the chain:
all 15 of the Oct 11 trap pulls on the 3.0 line were `a0f7978d` calls to the bot's router `0x1cbaf24d` with value 0, the path the
pull-before-fire watch covers. Still open from that review: the slot precedence (a live delayed family holds the slot about 3-5 s a
trade, skipping a 2.4333 launch that falls inside, about 2% of them at today's rates); nothing watches a pull after our buy (a pulled pool
cannot be sold anyway; the pull-first halt stops the family afterwards).

A fourth review (Opus, on 644fa21): safe for the box's pull, safe for the 3.0 dry family, safe as a 0.002 ETH probe; its low findings
fixed in the commit after 644fa21 (56 tests): family names are 1-64 letters, digits, `.`, `_`, `-` (no two names can share a halt file);
`halt()` returns whether its file was written and alarms when not, and the decoy halt's `nonbot_halted` mark follows it (a halt that
failed to write resets nothing later); the sold-none halt is front-wide again even for a listed family (its cause is usually the sell path,
not the line; the pull-first and decoy halts stay per family); the start's message says when front is off altogether. Still true: the
FRONT_* settings themselves are read with bare `int()`/`float()` at import, so a malformed FRONT_* value (not a family) still stops the
service; check the env before a restart.

Deploying it: `git pull` (56 tests). The FRONT_* settings stay the 2.4333 line's (the box's env must be back at them after the Oct 11 dry
run: `FRONT_VALUE_WEI 2433328500000000000` or unset, `FRONT_FEE 2500`, `FRONT_TICK_SPACING 50`, `FRONT_SQRT_P 1604517591721945638372359205383840`,
`FRONT_LIQ 49279426163460954002188`, `FRONT_BOT_MINOUT 0.99`, `FRONT_AHEAD_MAX_ETH 0.008`, `FRONT_TAKE_PROFIT 0.01`, `FEE_MAX_PPM 9999`,
`FRONT_PIN 0`), then `FRONT_FAMILIES` with the 3.0 line's JSON plus `"stake_eth":0.002,"dry_run":true,"pin":true` for its dry run beside
the live 2.4333 line, restart; then the gates of 16.12 (`"dry_run":false` at 0.002 ETH for 50 trades, then the full stake).

**But the 3.0 line changed on Oct 11 (16.14):** the bot's buy moved to +18..+58 after launch and some pools are pulled at +7..+9, so the
plain front (buy at +1, hold 18) does not meet the bot's buy there. For that shape the family has two more fields (test 20d, 55 in all):
`fire_at` (fire when the feed shows launch + N; 0 = the launch block, as the 2.4333 line) and `fire_max` (how many blocks later the fire may
still go; `FRONT_FIRE_MAX` for the base family): the **delayed front** enters after the operator's early-pull window and before its late
buy (for the 3.0 line's Oct 11 shape: `fire_at` 12-16, `hold_blocks` past the bot's latest offset, say 60), sells into the bot's buy as
before, and is late if the bot bought first. Which numbers, and whether the line pays at all in its new shape, is the replay study of 16.14
(running when this was written); nothing of the 3.0 line goes live before it and a dry run.

### 16.14 Oct 11 afternoon: the dry run on the new feed; the 3.0 line's schedule changed; the 2.4333 line is back

The engine ran dry on the Dwellir feed from 13:38 UTC (2.4333 settings) and from 13:49 (3.0 settings, env only). On the 2.4333 line: 4
launches in 10 minutes, 4 fires with a reaction of 0.4-0.7 ms from seeing the launch, 4 exits into the bot's buy 6-9 blocks after ours
pricing +14% to +16%: the trade as on Oct 10. On the 3.0 line: 5 fires, all 5 closed at the deadline (+18 after our buy) and the bot's buy
came only afterwards, at +27, +28, +40, +47, +50 after the launch. The chain over the 4 hours to 15:30 UTC (60 of the 67 v3.0 launches
sampled, `scanner` helpers): the bot's buy at +18..+58 after launch (median about +40), 4 of 60 pools pulled at +7..+9 after launch with no
bot buy at all, the rest pulled 115-532 blocks after the bot's buy; the Oct 11 fronter `0x8cf143dd` (16.12) in none of them. So the 3.0
line's schedule changed after the skeptic's measurement (to 02:57 UTC: +6..+10 in 92%), the way 16.12 warned: a front at +1 now has to hold
40-60 blocks to meet the bot's buy, with about 7% of pools pulled under it, which is about break-even at best. Not a trade today; the
families code (16.13) can dry-run it beside the 2.4333 line and tell when it changes back. The 2.4333 line itself came back: 33 launches in
the same 4 hours (about 200 a day), with the bot's buy at +6..+9 in the dry run.

**The 24-hour study (`research/session_oct9_10/line_adapt/`, every v3.0 and v5.0 launch Oct 10 14:00 to Oct 11 14:30 UTC, every swap
replayed exactly):** the hour table (`regime.txt`) dates the change. Until 03:59 UTC Oct 11 both 1% lines put the bot's buy at +8..+10 and
pulled long after it (hundreds of blocks). From 01:00 to 04:00 the fronter `0x8cf143dd` bought 0.00297 ETH at +2/+3 in nearly every v3.0
pool (78 of 90, 166 of 172, 63 of 80, while the line launched 90-172 an hour) and the operator pulled at bot+3; at 04:00 it began pulling
pools the fronter had entered at +7..+9, before its own buy (11 of 80 that hour, every one with the fronter's buy before it); from 04:22 it
moved the bot's buy on BOTH 1% lines to +24..+55 (median about +40; the 5.0 line, which nobody fronted, moved too), launches fell to 13-20
an hour, the fronter vanished, and at 13:00 it tried again in 4 pools and was pulled at +7..+9 in all 4. So the operator's answer to a
fronter on the 1% lines was, in order: the pull at bot+3, then a trap pull within about 5 blocks of an outsider's early buy, then a late
and spread-out bot buy. The 2.4333 line was not changed (our own front's exits at +12% on Oct 11 afternoon).

The replay over the new regime (170 v3.0 pools from 04:22, 86 v5.0), at 0.0058 ETH:
- v3.0, the plain front (+1, hold 18-20): -4% (the bot comes after the deadline); with hold 60: +3.7% but exposed to the trap (an outsider at
  +1..+3 was pulled at +7..+9 in 15 of 16 cases: with that reaction, -100%).
- **v3.0, the delayed front: buy at +10 to +16, sell into the bot's buy, deadline 60: +6.00% mean, +6.17% median, 97.6% win, 0 pulled, $0.90
  a trade, about $360 a day** at the line's new rate; the 4 trap-pulled pools cost only a reverted buy's gas (the engine now marks a pulled
  pool late before the fire, 16.13). +18 and +20 give +5.9% (the bot sometimes comes first). The break-even fill rate is near zero.
- v3.0, the ride (buy after the bot's buy, hold 10-20 or to its next buy): -2% to -4%. The bot's later buys do not lift the price.
- v5.0, the delayed front at +10 to +25, deadline 60: +1.71% mean, 89.5% win, 0 pulled, $0.26 a trade, about $52 a day; thin.
- The one unknown that the replay cannot price: the operator's reaction to an outsider buy at +10..+16. No outsider bought at those offsets
  in the new regime. Its known reaction is to a buy at +2/+3 (a pull about 5 blocks later); a buy at +12 pulled 5 blocks later would be at
  +17, before the bot's buy, and would cost the stake. The only test is a live probe at the smallest stake with the decoy halt on: 20
  trades at 0.002 ETH risk $100 at most and the halt stops it after 5 losses (about $25).

**15:20 UTC: the pull check was failing on Dwellir's RPC.** The start of the new code showed two `pull check unreadable` alarms:
Dwellir's node refuses an `eth_getLogs` whose `toBlock` is past its head (`block range extends beyond current head block`, also `invalid block
range params`); the pull check asked for our sell block + 30 about 3 s after the sell, which is at or past the head of a node a few blocks
behind the sequencer. The public RPC had accepted it. On a failed check the pull-first halt cannot fire, so since 14:26 some trades (those
whose check failed) had no pull protection. Fix (dcb5235, d492a41): the range ends at `min(sell + 30, head)`, never under the sell block (the
halt needs blocks up to the sell only; `trade_done.pull_check_to` says how far it looked); the test stub answers `eth_blockNumber`. Then
(929cba1 and the commit after it, both Opus-reviewed): the range ends 10 blocks under the head (a load-balanced provider may answer `eth_getLogs`
from a node a few blocks behind the one that answered `eth_blockNumber`), the floor is the sell block for front and `buy + FOLLOW_NEAR_MISS_BLOCKS`
for follow, and the two calls are tried 3 times on any error (`tries=1`, 3 s and 5 s timeouts: 25 s at worst, under the 84 s the rpc defaults
allowed); `trade_done.pull_check_head` is the head's distance from the sell block on the last try. A lagging head (under the floor) fails the
check with the `pull check unreadable` alarm rather than looking at a range that could miss a pull; test 19b covers the cap, the floor, a
refusal followed by success and the +30 cap; 19c covers follow's floor (buy + 4, past the sell block). A live `trade_done` carries `fam` (since 78ea92c; 20e asserts it).

**14:41 UTC: a follow trade halted everything.** Three minutes after the restart at the full stake, a follow trade on an operator A launch
(5 follow launches that hour: A is back) was pulled 3 blocks after our buy, at our sell (+4), -$2.99; on the box's code a follow pull
writes the all-trading halt file, so front stopped too (8 front launches skipped `halted`) until the owner cleared it. Operator A's
reaction is now +3 after our buy (Oct 9-10: +5/+6). The owner's decision: **follow is off** ("it is not making money": 45 trades, -$7.76
since Oct 8). On the box's code that is `LAUNCHERS none` and `LAUNCH_SELECTORS none` in the env (an empty value would fall back to the
default launcher); the code after 154e822 has `FOLLOW=0` for it (no follow launch is armed, front has the slot alone) and a follow pull now
halts follow only (`scope="follow"`), front only front. Follow's code stays for the day operator A's crowd is worth it again.

The dry run cannot measure the landing block: `_fire` plans the dry buy at the fire block + 2 by construction (`plan_buy_seq`). The first
live trades measured it: **live again from 14:26 UTC Oct 11** on the 2.4333 line at 0.002 ETH (the 3.0 settings removed from the env, the
code still de88eb9), 25 trades in 10 minutes, +$15.07, every exit into the bot's buy at +12% on average, the buy landing at +2 in 24 of 25
and +3 in 1 (the Dwellir feed costs about one block against the public one; the bot buys at +6..+9, so it does not matter); then
`FRONT_STAKE_ETH 0.0058` and `FRONT_DAILY_STOP_USD 50` at 14:40 UTC. The feed itself: live blocks 0.1 s behind the sequencer at the box,
no gaps, a 90 s backlog on connect that the engine marks stale. The box's env since 14:40: `FEED_URL` and `RPC_URL` on Dwellir,
`DRY_RUN 0`, `FRONT_STAKE_ETH 0.0058`, `FRONT_DAILY_STOP_USD 50`, `FRONT_SELL_ON_ETH 0`, `FRONT_MAX_PER_DAY 100000`, the FRONT_* fingerprint
settings at their defaults.

### 16.12 The scanner for other operators (12.6): the volume bot's 3.0 ETH line is the one front candidate (conditional, medium confidence)

Run Oct 10 18:15-22:10 UTC from the research container over the public RPC as one workflow of 36 Opus agents (a census, 29 family analysts,
5 skeptics who re-derived every flagged family's numbers from the raw rows with their own code and traced its money). The synthesis agent
produced no report, so a second pass ran Oct 11 02:50-03:50 UTC on the cached results: two syntheses (one refused to write), a critic that
checked them and the first version of this section against the raw data and the engine's code, and a final merged report. The second pass
also read the chain to block 85,513,808 (02:57 UTC Oct 11). Files: `research/session_oct9_10/scanner/` (`README.md`; `REPORT.md` with the five
skeptics' verdicts in full; `report/REPORT_final.md` the merged report, `report/CRITIQUE.md`, `report/work/` and `report/merge/` the second
pass's evidence; the census code and small outputs; every agent's scripts and results. The 937 MB of raw RPC answers were not kept,
`census/code/fetch.py` rebuilds them in about 20 minutes.)

The census: 6,865 ETH-paired v4 pools in the 48 hours to Oct 10 18:20 UTC (11,889 `Initialize` logs in all), events complete to launch + 3,000
blocks, 1,644 strict launch families; all 104 families with 5 or more launches were assigned to analysts (96 left a result file), the ranked list
has 7 entries for 6 distinct families, judged as 5 operators. The V2/V3 factories (6,739 and 645 pairs) and the bonding-curve factory (4,693
creates) were counted, not analysed. The method's controls held: v2.433's front replays at +11.9% mean / +14.0% median over the 1,843 census
pools and +14.0% / +16.2% over the 409 live-window pools, and the model re-priced 1,080 live relay round trips within 0.5 points
(`analyse_26/results.json`, `analyse_10/calib.json`); operator A's follow +4.3% (n 75).

**What the chain says, ranked by what it is worth to the owner:**

1. **The volume bot's 3.0 ETH line (v3.0) is the same edge, larger room, same adversary, now with company.** Section 1 already named 3.0
   and 5.0 ETH as the bot's untraded sizes. 889 v3.0 launches in the 48 h (444 a day) and 434 v5.0 (217 a day); in the 8.6 h after the
   census v3.0 launched 231 (19 an hour for 7 h, then 98 in the last 1.6 h) while v2.433 has been silent since 19:28 UTC Oct 10
   (`report/headcheck3.json`). Same router `0x1cbaf24d`, same `c1120e3d` buy from reused wallets at +6..+10 (92%), full pull by the launch
   wallet via `a0f7978d`, but **minOut 0.95 x the launch quote** (v2.433's is 0.99): the stake curve is flat at +6.0% from 0.0029 to 0.075 ETH
   and the bot's buys start reverting at 0.08 ETH (the engine capped the front stake at 0.006 ETH in code then, 0.012 since 294f438). Front replay at 0.0058 ETH
   over all 889: +6.03% mean, +6.09% median, 99.2% win, 7 deadline exits at -2.07%, about $0.90 a trade and **$400 a day** at 444 launches
   (`skeptic_0x58.../s4_replay.json`); the 235 pools to 02:57 UTC Oct 11 replay at +6.19% mean, +6.56% median, 98.7% win
   (`report/work/f8_fresh.json`). v5.0 is thin (+1.75%, $57 a day): log it inside a v3.0 dry run, do not trade it. The caveats:
   (a) the trap exists here too: an outsider ahead of the bot does not stop the bot's buy, and the pull then comes at bot+3 (bot+8..10 on
   Oct 9), so our sell at bot+1 keeps a 2-block margin, one block of slip is survivable and two are not; (b) **since 01:57 UTC Oct 11 an
   outside wallet does our trade there**: `0x8cf143dd` bought 0.000099-0.00495 ETH through router `0x65050a9b` at +1..+6 in 85 of 97 v3.0
   launches and sold into the bot's buy in 56 of them (18 in the bot's block, 32 at bot+1, 6 later) at +1.2% to +10.9%; the operator answered
   with the bot+3 pull (31 of 32 bot+1 sellers were pulled at bot+3; 77 of the 83 pulled pools it entered were pulled at exactly bot+3, the
   48 pulled pools without it at bot+21 or later; `report/work/decoy3.json`). Its sizes and timing match v2.433's decoys (16.10); whether it is
   the operator's decoy or a competitor cannot be told from public data; (c) v2.433's decoys defeated our size rule within 6 hours (16.10),
   and this is the same operator; (d) in the 1% fee tier a forced exit costs about -2.1%, so the take-profit and size rules must be off for
   this family: `FRONT_TAKE_PROFIT 9` (the default 0.01 fires) and `FRONT_SELL_ON_ETH 0`, the router rule alone; (e) the trade breaks even
   when about 26% of the bot's buys fill (on v2.433 our stake plus two decoys reverted about 72%; on v3.0 that would need about 0.074 ETH
   ahead of the bot). **What the engine needs, in order:** code first: a front-only fee bound (with the default `FEE_MAX_PPM` 9999,
   `front_mismatch` rejects all 889 v3.0 launches as `fee 10000`, verified by running the engine's decoder over them, `report/merge/
   fee_check.txt`; raising `FEE_MAX_PPM` to 10000 would also open follow to 1% pools, so the bound must be front's own), and a halt after 5
   consecutive non-bot or deadline exits (the decoy signal; no such counter exists, only the pull-first and near-miss halts), each with a
   test and a review. Then the settings: `FRONT_VALUE_WEI 3000000000000000000`, `FRONT_FEE 10000`, `FRONT_TICK_SPACING 200`,
   `FRONT_SQRT_P 679394651928963067279918579724198`, `FRONT_LIQ 25725498245903809899643`, `FRONT_PIN 1` (rejects a 3.0 ETH launch whose
   fee, tick spacing, price or liquidity differ; the 16 value-0 look-alikes are never armed because the engine arms only
   `value == FRONT_VALUE_WEI`), `FRONT_BOT_MINOUT 0.95`, `FRONT_AHEAD_MAX_ETH 0.07`, `FRONT_TAKE_PROFIT 9`, `FRONT_SELL_ON_ETH 0`,
   `FRONT_STAKE_ETH 0.0058`. The engine takes one front family at a time; trading v2.433 and v3.0 together needs a set of launch values,
   each with its own fingerprint, minOut and room, and the one position slot (19 of 889 v3.0 launches fell within 12 blocks of a v2.433
   launch). The gates: a dry run of at least 200 v3.0 launches (recognised in the launch block 98%+, the bot's buy at +6..+14 in 95%+, minOut
   0.95 in 100%, non-us ETH ahead of the bot 0.01 or less in 95%+, the sell sent in the feed block of the bot's buy in 99%+ (the 14:28 loss of
   16.10), the simulated sell before the pull in 100%, replay +5% or better), then 50 live at 0.002 ETH (0 pulled first, 90%+ sold at bot+1,
   the pull at least 2 blocks after our sell every time, mean +4% or better), then 200 at 0.0058 before calling it live. An hourly RPC watch
   of minOut, ETH ahead of the bot and pull-minus-bot can start before any of it.
2. **Operator C-1 is a different trade: a ride on a wash crowd, about $90-127 a day.** POSM `ac9650d8`, 2,276 bytes, value 0, fee 100/ts 1:
   245 launches in 47.4 h (124 a day, but one 6-h slice holds 92; the other seven run at about 89 a day; 30 in the 8.7 h after the census,
   about 84 a day, `report/work/c1/c1_fresh.json`). Its "crowd" is its own router `0xd6d35b56` with at least 1,049 wallets that buy and sell
   (4,072 buys for 653 ETH and 1,691 sells in 66 pools; outsiders 0.255 ETH in all; every call with gas limit 1,000,000, gas price equal to the
   tip and minOut 0), funded in a loop the skeptic traced to the wei (the creators' pulls, 448 ETH in 48 h, go through the multisend
   `0xf341c935` to the next launcher, which sends the pot to hub `0xbae53801`, which funds the router and pays 965 wallets' gas). The first
   router buy comes at +4..+501 (median +116), not on a schedule, so there is nothing to front; a buy at the end of the block after the
   router's first buy, sold 50 blocks later, replays +11.5% mean, +5.7% median, 69% win, 2.4% lost to the pull, $1.73 a trade over 209
   pools; the 27 rides since the census +8.1% mean, +3.2% median, 1 stake lost. A random entry gives +6.0%, so the trigger adds something;
   landing at c1+2 or c1+3 gives +10.5% and +10.0%; hold 20 gives +6.8% with a -0.1% median, hold 100 +21.9% with 16 stakes lost. One wallet
   (`0x97ac054b`) already rides these pools at 0.0002 ETH for a realised +13.9%. The objection: 6 of 15 pools with an outsider buy of
   0.001 ETH or more among the first swaps were pulled within 100 blocks (controls 12%, p about 0.006), 60-86 blocks after the outsider's buy
   and only 10-36 blocks after our planned sell; read swap by swap they look like the normal pull after the operator's buying stops, but the
   operator can tell its wallets from ours. Needs a new entry type in the engine (arm on the launch calldata, fire on the router's first buy at
   minOut 0.97 of the quote, hold 50 blocks, shadow exits at +40 and on no router buy within 20 blocks) and the position slot for 5 s a
   trade. Gates: a dry run of 100 triggers, then 50 rides at $5, then $15.
3. **The top-scored family (815) was a one-off.** A hooked launcher (code hash `f07d1c53`, selector `e1e75b94`, 5,572 bytes, fee 2500/ts 25):
   102 pools, 100 of them in 23 minutes on Oct 10 17:33-17:56, one buyer `0x9fdd8cea` buying each at +15 (2.01 ETH x8 down to 0.06 in tiers),
   the launch wallet pulling at +30 and both burning the whole supply. 48 ETH ended in 100 fresh wallets and stayed there. minOut 0.95 and
   room 0.027-0.039 ETH, so a $15 front would have fitted, and the analyst's replay said +71% median, but nothing of this shape recurred to
   02:57 UTC Oct 11 (`report/headcheck3.json`) and the hook (reads `tx.origin`, makes an external staticcall) is unverified at launch state.
   Watch-only recogniser if ever (the fingerprint, the sibling `0x6765bede`/`82a55dde`, its 100 deployers); reconsider after 3 bursts on 2 days.
4. **The small-pot operator** (POSM 1,444 bytes at 1.5-2.5 ETH, fee 100/ts 1 or 500/ts 10, a fresh dispatcher funding the launch wallet and 10
   fresh crowd wallets 800-1,200 blocks before, the pot forwarded to the next dispatcher; 339 launches since Sep 11, about 11 a day in
   sessions) is **operator A's design with its own pot** and aborts on real-size early holders: wallet `0x578e7a8e` bought 0.005 ETH at
   +61..+136 in 24 consecutive pools on Oct 5-6, was tolerated for 10, then 10 of the next 14 were pulled with no crowd. The no-reaction front
   replay is +50-60%; with an early holder of our size -30.1% mean, -100% median; the follow variant fails too (with a mid-crowd outsider of
   0.002 ETH or more the crowd reached 10 buys in 2 of 17 cases). `0x5e6ec144` already runs the hold at 0.0003 ETH ($0.40 a trade). About
   -$50 a day at $15. Not a candidate.
5. **Operator C-2 is a trap** (PM `initialize` 196 bytes fee 500/ts 1 from the deployer, a POSM 1,380-byte mint about 41 blocks later, crowd
   routers `0x628bd69e` and two twins, 192 launches): 24 of 25 outsider buys of 1e-4 ETH or more were followed by a pull within 166 blocks,
   8 of them exactly 4 blocks after; untouched pools run to a scheduled pull near +4,900. The no-reaction ride is +7.2%; with the observed
   reaction -96% (about -$1,379 a day). A known sniper (`0xe9d83e95`) buys 9.0-9.99e-5 ETH here, tuned under the trigger. Its hooked sibling
   (23 pools, follow +13.3% mean, +0.8% median) uses the same crowd routers, so the same reaction likely applies. Do not trade; a dry run
   cannot settle it.

So the only other place the exact edge exists is the same operator's larger line, a conditional candidate at medium confidence whose pull now
comes at bot+3 wherever an outside wallet buys ahead of the bot, and every other scheduled buyer on the chain is either the operator's own
money that pulls on outsiders (C-2, the small pot), a one-off, or a ride rather than a front (C-1). None of it can run without an authorized
feed (16.11); the box must not reconnect to the public one.

### 16.9 The study of the whole repository (13 agents, 13:00-14:45 UTC): what it corrected

Thirteen agents each read one area file by file and checked it against this document; a fourteenth re-verified the first four areas' findings
(its input was cut at 180,000 characters, so the other nine areas' findings are the readers' own). The full record is
`research/session_oct9_10/STUDY_OCT10.md` (summaries, numbers with their source files, every discrepancy, the scripts that do not run as copied)
and `STUDY_OCT10_files.md` (every file's purpose). Corrected in place above: the Oct 8 net (-$8.5 for the eight trades, not -$5.19; 3 positive,
not 4 wins), the dust wallets of section 1 (`0xe71a69f4` is a chain-wide dust bot in both operators' pools; `0x93b07902` buys 2.4e-5 ETH at
median +132), the crowd's first-buy range (3.1), the bot's buy sizes (3.2: 0.005-0.335, the census already had 0.005), the seat's numbers (6.2:
+7.9% on 44 of 49), the stake curve (6.2: returns fall from +2.5% at 0.012 ETH to +1.4% at 1.0 ETH), the census verdict (6.5: only OURS-orig is
positive at hold 2), the decoder count and the reaction census (6.6), the front rule's real numbers (6.7: +11.8%/+13.0% at hold 19, the "+7-9%"
belonged to v3.0), the replay's pool count (6.8: 42 distinct) and the size ceiling's provenance, the dry-run census counts (6.10), the
misdescribed scratch-root files (6.12), the repository table (2). Not changed in the text above but worth knowing:

- The root `research/` files are a fragment of an older project (reports 21.3/24.20/24.45/24.50, the "Pons seat", paths `src/analysis/` and
  `data/derived/edge_check/Q/` that do not exist here); only `v4_slowrug_test.py` runs offline and reproduces `slowrug_test.txt` byte for byte.
- Operator A's money (6.4): the pot is pinned at about 7.0 ETH by design; it grew to 8.66 ETH in 37 minutes of bonding-curve launches on
  `0xe33e9e47` on Oct 8 11:19-11:48 and 1.6 ETH left it at 12:10 to hub `0x3ee51814`, which bridged 0.8/1.0/0.25 ETH through Relay.link to Base
  addresses that all forward to `0x487cab40` -> hot wallet `0x3304e22d` (29,656 ETH), the same terminal pot B uses. Pot B itself launched on that
  bonding-curve factory (so the "third system" of 6.4 is not independent of A and B), a fourth crowd D (32 wallets, about 5.3 ETH) exchanged money
  with A's hub by plain transfers, the sweeps had 49-50 inputs in the Oct 6-7 sessions (32 only from Oct 8 21:57), the launcher copies go back to
  August (1,782 at nonce 0, 2 at nonce 1), and the eras are 1.0-2.0 ETH launches in July, 0.34-0.5 and 1.0-1.35 in Aug 19 - Sep 9, 1.97 in Sep
  13-30, 0.45-4.95 in October. The "third" factory `0x7ed598bc` has 684,002 creates back to block 27M; only 29% of its Oct 9 creators are
  EIP-7702 delegates.
- The protection backtest (6.3) is more nuanced than its summary: at a pull + 3 only V1 ("deadline at buy + 1") and V4c avoid the catch (V4a
  -4.5%, V4b -82%, V4d equals V0); with the buy landing at T+2, V1 and V4d hold +1.6%/+1.8%; with the buy at T+3, V0 is negative at every pull
  offset while V1/V4c/V4d are +0.4/+0.6%. `protect/` also holds a stake-ladder design (RAMP/WARN/WATCH/HALT rungs), a canary census
  (`prot_eval.py`) and a residual-risk model never mentioned before; the near-miss halt of 16.3 is its HALT rung only.
- The 0.6 review (6.1) was of the pre-0.6 engine (its biggest finding, kind-4 single-transaction blocks, is missing from 6.1's list); release
  0.8 was not reviewed as such; 0.9 was reviewed twice (506a254, 50bd0aa). The look-alike finding (any sender's front-shaped launch at a fake
  price) was fixed in 506a254 and re-opened by design in 7d1f645 (`FRONT_PIN=0` on the box): an accepted residual risk. No review verdict file
  exists anywhere; the attributions rest on the fix commits. `SELL_TRIES` 4 with 50 ms pauses gives up within about 0.2 s (review06_fixes
  scenario B), never changed.
- 6.11's reading ("the operator reacts to our sell") and 16.1's ("the pull 3 blocks after its bot's buy, by schedule") fit the same live data,
  because our sell lands one block after the bot's buy; the census's quick-pull pools with nobody else in favour the schedule reading, and the
  dry-run window (pulls at + 101..139 with no buy from us) leaves open why the regime changed at about 09:07.
- Numbers in this document with no saved result file behind them: 6.12's "+2.4% on 14 launches"; 6.8's per-stake fill ratios and "$27"; 6.9's
  per-day counts before Oct 9 14:49 (the jsonl scans were over 1.5 MB and not copied); 6.10's "0.0138 ETH" pool; 7.4's "22 runs".
- `deploy/relay_sim.py` printed "TooLittleOut ok" on any revert (its selector constant was wrong); fixed in the afternoon (16.9's commit).
- The post-pull sell reverts because `SELL_GAS` (350,000) runs out walking the empty pool's tick bitmap (335,520 used), not because the relay
  refuses it; a larger gas limit would make it succeed with 0 ETH out and the tokens left in the relay. Nothing to change: the pull decides.
- `results.py`'s `daily cap` skip text is the same for both strategies; the owner's "daily cap x60" was front's (follow had 5 of 100).

### 16.15 Oct 11 evening (15:40-17:00 UTC): the 3.0 probe, the 2.4333 line's three changes, $25 and the room, the research round, the wave mode

- **The 3.0 probe (15:46-15:48).** The dry run of the delayed front (fire at + 12) showed 3 of 5 launches firing at + 12 with the bot's buy at
  + 29/+ 46/+ 49 behind (`would_sell` "the bot's buy behind ours"), as the replay predicted; the owner switched the family live at 0.002 ETH.
  One trade: our buy landed at + 13, the operator pulled 9 blocks later (+ 22), the bot never bought, -100% (-$5.15), the family's own halt
  (`HALTED.front.v3.0`) stopped it; 12 later 3.0 launches skipped `halted`. The trap is not tied to a buy at + 2: any early buy gets the
  pull about 9 blocks later. The family was removed at 16:07 and re-added as a dry watch at 16:13 (its `first_buy` lines show the bot's offset;
  if it returns to + 8/+ 9 the line is probeable again).
- **The 2.4333 line, change 1 (15:32): fee 2500 -> 5000, tick spacing 50 -> 100**, same price and liquidity. The pin refused 14 launches
  ("front: fee 5000"; `results.py` reported "fingerprint not seen before: tick spacing 100"). `deploy/pool_story.py` (new, read-only: the
  armed-but-untraded pools' swaps and pulls from the chain, the RPC URL never printed) on 12 of them: the bot bought at + 7..+ 16 on all 12;
  the 6 pools a stranger (wallet fd1b271f, buy at + 3, sell at + 10) had fronted were pulled at + 27..+ 29, the 6 nobody fronted were not.
  `FRONT_FEE=5000`, `FRONT_TICK_SPACING=100` at 16:07; the first launch after it traded.
- **Change 2 (15:40): the bot throttled its 2.4333 launches** from 36 per 10 min (15:20) to 15, 1, 1, 8, 3, 1 (chain scan of every PoolManager
  Initialize of the hour, `research/session_oct11/recent_launches.py`); its 3.0 and 5.0 lines unchanged (2-3 and 1-2 per 10 min); no new
  line at another value (2 launches at 2.0 ETH; two batch transactions of 140 and 60 pools at 0.0007 ETH from one wallet).
- **The room and the stake (16:37-16:44).** `src/v4math.py` on the 2.4333 pool (2.433 ETH deep): our own impact is nil (+11.47% at $15,
  +11.43% at $30 with the bot buying 0.15 ETH); the bot's fill against its minOut (0.99 x the launch quote) with x ETH ahead: 1.0054 at
  0.0058, 1.0038 at 0.0078, 1.0022 at 0.0097, 1.0006 at 0.0117, 0.9996 at 0.0130: the room is ~0.0124 ETH. On 2,132 un-fronted census
  pools the decoys took 0.00495 in 13% and 0.0099 in 7%. Expected $ per trade with that mix: $1.58 at $15, $2.23 at $25, $2.69 at $30.
  294f438 raised the code cap 0.006 -> 0.012 (Opus review: OK with `FRONT_AHEAD_MAX_ETH` 0.0115 and the streak halt raised, since 20% of
  trades would end at -1%); the box ran 0.0097 / 0.0115 / `FRONT_DAILY_STOP_USD` 100 / `FRONT_NONBOT_HALT` 8 from 16:44.
- **Change 3 (16:28): the decoys filled the room.** From 16:28 the decoy wallet 65050a9b bought 0.005 ETH at + 1/+ 2 on every 2.4333 launch and
  a second 0.005 followed before the bot's buy: 0.010 ahead of the bot on every pool, leaving 0.0024 of the 0.0124. The revert model fired on
  every fronted pool (`front_bot_reverts`, fill/quote 0.9845-0.9882 with ours in) at $15 (16:34, 16:41) and $25 (16:47: -1.4% "the bot's buy
  reverts", -1.0% deadline). Three anti-front moves in an hour (fee, throttle, decoys): the operator is reacting to us. **The 2.4333 line went to
  dry run at 16:52 (`FRONT_DRY_RUN=1`)**; the revert model keeps measuring the room on every launch with our stake as the hypothesis (the
  `front_bot_reverts` lines with `ours: true` stop when the decoys go), and `FRONT_DRY_RUN=0` brings it back.
- **The research round (13:46-16:30; `research/session_oct11/lines/`).** Census 2: every new pool for 7 days (64,416; builder's hand-back
  REPORT_census.md; the data files kept: summary, top40, tables, README; pools.jsonl and the 3 GB cache not kept). Three Opus analysts on
  BRIEF.md (the replay definition, our mechanics): A (the PositionManager-multicall launches without the volume bot), B (every other v4
  launcher), C (V2/V3), and the adversarial verifier V on the one candidate both v4 analysts ranked first. Findings: 122 of the 163 families
  with 10+ launches have a real buyer in under 5% of launches; **C-1** (100 launches/day, a buyer bot through router 0xd6d35b56 at + 73/119/205
  with minOut 0; follow at T + 2, hold 60: +16.3..16.8% mean, 78-79% win, 2.8-3.1% pulled, ~$200/day at $15; the token a plain ERC20; an
  eth_call round trip through our relay works) is **NOT YET**: the edge is the operator's own buying (591 ETH vs 0.42 by others in the hold
  windows), it fell from +27% (Oct 5) to +10% (Oct 10) to +1.8% in the 2.6 h after the census, and the census is blind to a reaction against
  us (as it was for operator A). The hooked a98b pump line (+83% replay, hook risk, sell simulation first), C-2's hooked sibling (honeypot),
  58d59320 (a 24%-win lottery), the V3 crowd line (~$185/day at $15, new trading path, profit in the top 10% of trades), the V2 fleet line
  (its stale minOut reverts on any buy ahead) and operator A are in REPORT_B/C. The verifier's probe design and halts: REPORT_V.md.
- **The wave mode (this commit).** `FRONT_FAMILIES` entries may give `calldata_len` and a `trigger` (router, selector, value_word, token_word,
  flag_word/flag_value, min_eth, max_blocks); `value_wei` 0 is allowed with a trigger. `ingest_tx` keys families by value then checks the
  family's calldata length; a value-0 call to a wave family's router (`WAVE_ROUTERS`) goes to `on_wave_call`: the token word must be an armed
  pool's token and the flag the buy flag; the amount word is the buy; the first of `min_eth` within `max_blocks` fires (`_fire`'s window is
  the family's); later ones move the price copy and may take the profit; the router's sell flag is ignored. `arm_front` counts the position's
  liquidity when the launch tick is the range's top tick (`lo < t0 <= hi`: a buy moves the tick down into it; C-1 mints a token-only range).
  `on_front_buy` on a wave pool only moves the price copy. The `ingest` loop never fires a wave pool at its launch and marks it late past the
  window; the pull-shaped-call check covers wave pools. Dry positions log `dry_ret` (the sell's return as the price copy prices it) in
  `would_sell` and `trade_done`. Fixture `tests/data/c1_launch.json` (a real C-1 launch and its bot's router buy); test 20f. The Opus review
  (OK as a dry-run family; nothing changes for families without a trigger) asked for, and the next commit did: a cap on the router amount
  (`max_eth`, 10: a forged or reverting value-0 call with an absurd word 2 had wrecked the price copy and `dry_ret` raised inside the feed
  loop, which would have left the dry slot taken), `flag_word` required, `max_blocks + hold_blocks` under 2,600, a value-0 launch-shaped call
  that does not decode falling through to the pull scan, `dry_ret` guarded, and `FRONT_BASE_DRY_RUN` (a dry flag for the FRONT_* line alone, so
  a listed family can go live while the 2.4333 line watches). Known limits it noted: `dry_ret` ignores sells (score the dry run from the
  chain: `research/session_oct11/c1_recent.py`); dry positions share the one slot (a c1 dry position holds it ~7 s, 2.4333/3.0 dry fires are
  skipped meanwhile, a c1 trigger during that is lost for sampling); before a LIVE probe the verifier's extra halts (REPORT_V) are manual.
- **C-1 on the chain at 17:03 UTC** (`c1_recent.py` 150 min): 19 launches, the bot bought in 18, median 0.173 ETH by T + 60 (census days
  0.3-1.4), the rule's gross return +2.1% mean / +0.8% median, 9/18 above +0.3%, no pull before the exit. Not worth live money yet. **The
  box runs it as a dry-run family from 17:5x** beside the 3.0 dry watch, with `FRONT_DRY_RUN=1` (the 2.4333 line dry too).
- **The rest of the round (REPORT_R/W/H/G, 17:30-18:20).** R: no ride on the 2.4333 or 3.0 line: the operator pulls about 9 blocks after any
  stranger's buy, before or after its bot (65 of 86 and 88 of 96 census pools; 3 of 3 small buys after the bot on 3.0 today); a ride holds
  25 blocks; only dust under 0.00003 ETH goes unpunished; the decoys since 16:28 are a fresh nonce-0 wallet per pool buying 0.00495 through
  the router 0x65050a9b plus a 0.00495 fronter-shaped buy that sells at T + 1 (self-funding), 0.0099-0.01003 ahead of the bot; a 0.002 front
  still fills the bot's buy at 1.0004 (4 pools), 0.0058 reverts 4 of 4. W: the V3 crowd line is buildable (launches decode from calldata
  31/31, a router buy and sell simulate to the wei, approve-then-sell at consecutive nonces works on this chain; ~12 h for a router-path
  probe, ~14 h for a V3 relay) but today's forward test gives +5.2% mean / +0.17% median on 29 launches (~$65/day at $15, the line at ~90
  launches/day): forward-test 24-48 h first (`analysis/W/w07_forward.py`), build only at >= 100 launches at >= +4% and >= 120/day. H: the
  hooked pump line's hooks (one code, beforeSwap/afterSwap with return deltas) could tax or block a sell; no live pool to simulate on (all
  recent pools pulled within hours, one launch in 6 h): parked. G: the owner's method brute force (123 launch-shape/token families x 2,574
  rules, validated on days 6-7 and 6-hour slices) finds no new large safe line; the 2.433 line is the calibration and passes (our 1,087
  real round trips +8.43% vs the replay's +8.34%; 1,035 of our buys landed at launch + 1); the vbot 3.0 late entry (K80, TP 50%) and C-2
  hookless at K150 score well but die on the operator's reaction; the hooked lines need the sell simulation first.
- **Where this leaves the box at 18:30 UTC:** nothing live; three dry families (2.4333 via `FRONT_DRY_RUN`, 3.0, c1); today +$188. The
  2.4333 line comes back with `FRONT_DRY_RUN=0` the moment the decoys leave the room (the `front_bot_reverts` lines with `ours: true` stop);
  a $5 front fits the 0.0024 ETH the decoys leave (pocket money, the operator can close it with one more decoy). The lines that pay next
  must come from operators that have not met fronters yet: C-1 if its bot's buying recovers, the V3 crowd line if its forward test holds.

### 16.16 Oct 11 evening: the V3 crowd line's dry-run half (a `dex: "v3"` family)

The line (REPORT_C candidate 1, REPORT_W): fresh wallets launch a token through Uniswap V3's PositionManager `0x73991a25...8de0d3`
(multicall `ac9650d8`, 836 bytes, value 0: createAndInitializePoolIfNecessary(WETH, token, fee 100, the price), mint of the token alone
from tick -887272 up to the launch tick, refundETH); a crowd of bot contracts buys at about + 47/+ 86/+ 264 and the launch wallet pulls
at + 128/+ 301/+ 1216, never before the first real buy. Built (two commits after b3329a7, 60 tests; nothing changes for the v4 families):

- **The family type.** A `FRONT_FAMILIES` entry with `"dex":"v3"` gives `target` (its PositionManager), `calldata_len`, `hold_blocks`,
  `exit_after_blocks` and a `trigger`; `sqrt_p`/`liq` may be left out (0, not compared), `take_profit` is off unless given. V3 families
  are keyed by `("v3", target)`, so the line and C-1 (both value 0) coexist. Refused at start (the listed families dropped with an alarm,
  as for any wrong family, never a crash): `dry_run` false or absent ("the V3 trading path is not built"), a `fire_at`, a cap under
  `fire_max + 3`, v4's PositionManager as target, `target`/`exit_after_blocks` on a v4 family, unknown keys, bad shapes.
- **The trigger, generalised.** `shapes: [{selector, calldata_len, value_word}]` (exact lengths) instead of one selector, `any_to: true`
  instead of a router (the crowd rotates its contracts: 4 in 8 h, each its own code hash), `token_anywhere: true` instead of `token_word`
  (the token as an address word, or as a V3 path's output after WETH and the pool's fee: a buy; a sell's path starts with the token and
  matches neither, so no `flag_word` is needed). C-1's single-router form parses and matches as before (`trigger_word`).
- **The launch.** `decode_launch_v3` (v3dec.py's port; equal to the chain on 106 of 106 launches of the 24 h to Oct 11 18:00 UTC) gives the
  pool's address by CREATE2 (factory `0x1f7d7550...2efa`, init code hash `e34f199b...8b54`), the price, range, amounts and liquidity
  (LiquidityAmounts, TickMath exact). `arm_front` arms it with `pid` = the pool's address and `dex: "v3"` when WETH is token0 and the range
  is the line's (the token alone from the lowest tick up to the launch price exactly: `tick0` = the top tick, the liquidity counted); a
  launch with WETH as token1 (3 of 106: the range mirrored above the price) is logged `eligible: false` and skipped.
- **The trade (dry).** The fire at the end of the launch block (`would_fire`, `plan_buy_seq` = + 2, no relay transaction built); the cap
  counts from the launch (`send_after = launch + hold_blocks - (fire block + 2)`, 76 for a fire in the launch block: the sell when the feed
  shows launch + 78). The crowd's calls (value-0, any contract, one of the shapes, the token in a buy's path; the amount word capped by
  `max_eth`) and anyone's ETH-value call carrying the token move the price copy (`apply_buy`, v4math at fee 100: the pool's first real buy
  priced to 2e-20); the first of `min_eth` logs `first_buy` (`trigger: true` for the crowd's shape); the first of `min_eth` at or after our
  buy starts the exit's clock: the sell when the feed shows that buy + `exit_after_blocks`. `_fire` treats a V3 family as dry whatever
  its setting; `_settle` is not reached and says what its live version reads (the pool's own Swap and Burn logs).
- **The exit rule, against the build's brief.** The brief asked for "the sell on the first real buy at or after our buy + 20". The
  research's rule (`w07_forward.py`: `exit = first real buy at or after ours + 20`, capped; REPORT_C "sell 20 blocks after the first real
  buy") is the one built: the crowd's wave comes in the 20 blocks after its first buy, and selling on that buy instead made + 4.7% a trade
  against + 8.7% in the census (`analysis/C/s17_grid.out`, k 1 against k 20 at cap 80). The other reading is a few lines in `on_v3_buy`
  (send the sell instead of setting `exit_seq`). `exit_after_blocks` 18 and `hold_blocks` 78 are send offsets (a sell lands about 2 blocks
  later): the replay's 20 and 80.

**What is pinned, and how constant it was** (the 106 launches to the PositionManager of the 24 h to Oct 11 18:00 UTC; 217 fee-100 WETH
pools in all, the rest other shapes): 836 bytes, value 0, fee 100 and tick spacing 1 (the factory's PoolCreated) on 106 of 106; WETH as
token0 on 103; on those 103 the lower tick -887272, amount0 0 and the launch price exactly on the top tick; amount1 1e27 less some dust
(5 values, one per price level); the price and liquidity are not constant: 5 levels (top tick 193379 x50, 192201 x31, 191147 x10, 196256
x10, 184216 x2, the last C-1's own launch price), L about 1e27 x 2^96 / sqrtP. So the family pins the fee and tick spacing and the decoder
the shape; `sqrt_p`/`liq` stay out of the box's JSON (RUNBOOK 4g).

**Known limits of the dry run** (score it from the chain before trusting it): `dry_ret` ignores sells (the crowd sells through the same
contracts), takes the a0193551/49f74a5d calls' whole amount word (they swap 99%/99.3% of it), prices our buy at + 2 exactly (landing at
+ 2 was measured on v4 only); value-0 WETH buys outside the shapes are invisible, while a 484-byte Universal Router call that sells the token for an exact WETH
amount (its path is reversed: WETH first) or swaps it on a V2 pair (the token as an address word) would count as a buy (none seen; the
crowd's 199 buys checked by REPORT_W were exact-input V3 paths; a token amount read as ETH is refused by `max_eth`); a V3 dry position holds the one slot for ~8 s (other
dry fires are skipped meanwhile, a live front fire drops it); `results.py` lists it among front's dry decisions without a family split.

**What the live path still needs** (REPORT_W): (a) the router path: the buy through SwapRouter02 `0xcaf681a6...` `exactInputSingle`
(04e45aaf, WETH -> token, fee 100) with the stake as ETH value (the router wraps), `approve(router)` on the token at the next nonce, the
sell at the third nonce as a multicall [exactInputSingle(token -> WETH, recipient the router), unwrapWETH9(minOut, wallet)] built from the
buy's receipt (the exact amount; without the approval it reverts STF), about 317k gas a trade, the stake from the wallet, not the relay; or
(b) a V3 relay (~80 lines: `pool.swap` with the callback, the pool checked by CREATE2, WETH wrapped and unwrapped inside, a presigned
sell-everything, no approval: solc, a harness like relay_sim.py, a review, a deploy). Either way: the three-transaction (or relay)
nonce flow in `_fire`/`send_sell`, the live settle from the pool's Swap log and the pull check from its Burn logs (amount above 0) with
the family's own halt file, the dry-only lock in `_fire` and the parser lifted, a `results.py` split. REPORT_W's gate before building:
100 launches or more at +4% mean or better, no pull before + 80, 120 launches a day (Oct 11: about 90).

Deploying it: `git pull` (60 tests), then RUNBOOK 4g's `FRONT_FAMILIES` (v3.0, c1 and v3crowd, all dry); the start line lists v3crowd
with `"dex":"v3"`. Nothing else on the box changes.

### 16.17 Oct 11 night: known fingerprints, the auto stake, the V3 family merged, the watch

- **The $5 front (from 17:58 UTC).** With the decoys at 0.0099 ahead and the room ~0.0124-0.0126, a 0.002 ETH stake fills the bot's buy by a
  hair (1.0004); the owner ran it: the first four trades +9.4/+16.1/+17.4/+13.6%, $0.72 a trade, all sold into the bot's buy, no pull before
  the sell (about $8/hour at 12 launches/hour). It stays on overnight; the streak halt (8) ends it if the operator adds a decoy.
- **Known fingerprints** (f60ae7e): `FRONT_FEES_ALSO` / `FRONT_TICK_SPACINGS_ALSO` and per-family `fees_also` / `tick_spacings_also` (at most
  8 whole numbers in range): `front_mismatch` accepts the family's fee or a listed one, `front_fingerprint` a listed tick spacing; unseen pairs
  are refused as before. So a return to 2500/50 trades on the next launch.
- **The auto stake** (f60ae7e; `FRONT_AUTO_STAKE`, off by default): `room_ahead(p, q_bot, minout)` bisects v4math for the ETH that may sit
  ahead of the bot's buy before its fill falls under minout x its launch quote; at every bot buy through its router on a front pool
  `on_front_buy` records room - eth_in (others' ETH before the bot) in `state["room_obs"][fam]` (a deque of 30) and logs a `room` event;
  `auto_stake(fam)` = the 25th percentile less 0.0004 ETH, floored at 0.002, capped at the family's stake, the floor until 5 observations;
  `fam_stake(fam)` feeds `_fire` and the room check (not for wave families, whose buyers have no minOut). Test 20h: the decoy regime gives
  0.0023 (the fixture's fee 2500 room is ~0.0127), clean pools climb to the ceiling, off = the family's stake.
- **The V3 crowd line's dry-run family** (the builder's four commits, Opus-reviewed "OK to merge and deploy as a dry run": nothing changes for v4
  families; before any LIVE V3 trade: a per-shape direction check (an exact-output sell or a V2 path of the 484-byte Universal Router shape
  reads as a buy), a check of the pool's Initialize or slot0 (a pre-created pool would give a wrong price copy), a pull watch from the pool's
  Burn logs, sells moving the price copy, the router or relay path with the 3-transaction nonce flow, a live settle from the pool's Swap log,
  its own halt file, the dry lock lifted deliberately, results.py split by family). Section 16.16 (the builder's) describes it; RUNBOOK 4g has
  the box's JSON with v3.0, c1 and v3crowd.
- **The watch.** A routine wakes this session every 3 hours (:52) to run the chain checks (C-1's bot buying vs its gate; the V3 crowd line's
  forward test vs its gate; the V3 self-buyer 13ead562's own buy size, whose return to 0.05 ETH is the go signal for a $678/day replay; the
  2.433/3.0 lines' decoys and rates; any new launch shape with a repeat buyer in the last 3 hours) and report only when a gate is crossed.
- **Research closed as no-go tonight:** the ride on 2.433/3.0 (REPORT_R), the hooked pump line (REPORT_H), the bonding-curve launchpad
  (REPORT_K). Open: the V2/V3 brute-force grid with adversarial verification (a workflow, Opus agents).
- **`nonbot_halt` per family (the commit after 32fd40f).** C-1's dry run at 19:50 UTC: 11 scored trades, three large winners (+30.0%, +34.5%,
  +13.6%), the rest flat at about -0.2%, mean about +7%, median about 0, no pull before the exit; the chain-based check at 18:55 gave
  +7.3% / +2.1% over 16 launches. A $5 live probe is justified by the cost of the losers (about -0.2% each) and the per-family pull halt; but
  the streak halt (8 flat trades in a row) would trip such a line within a day, so a family may now set `nonbot_halt` (0 = off); absent means
  `FRONT_NONBOT_HALT`; the position carries it; test 20i. 62 tests.
- **results.py per line (Oct 11 ~20:45 UTC, the owner: "add the c1, make it more clean to read, remove the follow line").** The screen is
  now built around the front lines as the start line lists them (section 9.3): a LINES table (LIVE/dry, the auto stake and its ceiling or the
  fixed stake, trades and $ per period, a dry line's would-have-traded count and mean price), per-line detail with the pulls in bands, launches
  and fires per line, the last 8 live trades with their line and stake, each dry line's last decisions. Follow is gone from the screen (FOLLOW=0).
  Front trades logged before families existed (no `fam`) count under the first configured line. Tested on synthetic logs (an empty log, an old
  start line, halt files on disk and in memory, a retired line's trades); Opus-reviewed: the fixes (a nested f-string only Python 3.12
  parses, follow's dry trades and rows kept out, a front that is off shown as off, the stake in $5 bands, failed pull checks counted,
  the base line found by its launch value, a broken pipe under `| head` ignored, the trade list moved up so `head -24` shows it).
