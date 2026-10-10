# v2pons — the crowd-following flip on Robinhood Chain

> **Continuing this project? Read [`docs/HANDOFF.md`](docs/HANDOFF.md) first.** It is the complete record as of Oct 10, 2026.

A small live test of one idea from the fomo-memebot research (report 24.54, copied here as `research/REPORT_24.54.md`):

One operator (the launcher contract `0x3194e326`) creates about 100-170 Uniswap v4 pools a day on Robinhood Chain, each paired
with native ETH, and 2-6 seconds after each launch buys it with its own wallets (about 2,000 single-use wallets and a fleet of
50 recurring ones: 99% of the swaps on its pools) for a few minutes before its deployer removes the liquidity. It also removes
the liquidity 1.0-1.9 seconds after an outside buy of a few dollars, which is why the first seat on these pools is a trap
(everyone who took it lost). Since Oct 5 it charges almost no fee (0.01-0.5%), which opens a narrower trade:

**buy right after the operator's first real-size buy, sell 0.4-0.9 s later, before its reaction.** On the chain Oct 5-8 that
prices at +3.6% a trade (sell 4 blocks after the buy) to +6.3% (7 blocks), 83-94% of trades positive, the same at $3 and $25,
positive every day. All of the profit is the operator's own money, nobody outside has tried it, and the open question is whether
our buy changes the operator's reaction. Five to ten $3 trades answer it. That is what this repository does.

**The first six live trades (Oct 8) were all pulled on**, -$5.19 in all, through the relay. The relay calls the PoolManager itself, so in
the pool's own `Swap` event our buy was the only one with a sender other than the Universal Router, which is where every buy on these
pools comes from (99.8% of 60,496 swaps on 371 launches). Release 0.2 tried to remove that tell by sending the crowd's own transaction
from the wallet through the Universal Router. Release 0.3 found what actually decided the trades (below), and 0.4 removed the router
route again: the engine trades through the relay only.

## The eight live trades, from the losers' side (releases 0.3 and 0.4)

Read back from the chain (`research/live_trades.py`, output in `research/data/live_trades_oct8.txt`): seven through the relay
(13:15-13:20 UTC) and one through release 0.2's router route (14:32).

| # | route | fee | return | pull, blocks after our buy | our sell landed, blocks after our buy | crowd buys behind ours before the pull |
|---|---|---|---|---|---|---|
| 1 | relay | 0.24% | +7.5% | 6 | 6 (ahead of the pull in its block) | +3 |
| 2 | relay | 0.24% | **-100%** | 6 | **7** | +1, +4 |
| 3 | relay | 0.24% | **-100%** | 6 | **7** | +1 |
| 4 | relay | 0.24% | +19.1% | 8 | 7 | +1, +6 |
| 5 | relay | 0.24% | +7.9% | 13 | 7 | +1 |
| 6 | relay | 0.24% | -0.5% | 7 | 6 | none |
| 7 | relay | 0.08% | **-100%** | 5 | **6** | none |
| 8 | router | 0.025% | -9.3% | 9,856 | 3 | +3, +12, +17 |

- **One pattern decides every result: whether our sell landed before the pull.** Every -100% is a sell that landed one block after
  it; every other trade landed before it. Fee, size, timing of our buy: none of it separates the winners from the losers.
- **The pull was a reaction to us.** On the relay it came 5-13 blocks (0.5-1.3 s) after every one of our buys, and the operator
  relaunched at once (seven launches in 4.5 minutes). Its other sub-1% launches that afternoon were pulled 29 s to 17 minutes after their first buy. The
  backtest's 10-19-block reflex was too slow for this tier: the seven-block hold sat in the middle of the real one.
- **The profit is the crowd buy already on its way, and only that.** Every win came from one operator buy landing 1-3 blocks behind
  ours (twice a second one); after it the crowd stops, and trades 6 and 7 got none. Holding past that buy earns nothing and waits for
  the pull.
- **The router trade was not pulled on** (the pull came on the operator's own schedule, 17 minutes later), which is what release 0.2
  was built to test; one trade so far. It lost 9.3% anyway: its sell was due before the buy's receipt was in, so it sold the buy's
  `minOut`, 90% of the tokens, and the other 10% stayed in the wallet and died with the pool.

Sold right after that crowd buy, by our buy + 4 at the latest, the same eight trades price at +7.2% (-0.8% if the sell lands one
block early), +7.6%, +5.5%, +5.5%, +7.5%, -0.8%, -0.5%, +0.4%: mean +4.0%, no -100%, worst -0.8% (`live_trades_oct8.txt`, section 3,
the slow landing on every trade). On the Oct 5-8 backtest the same exit prices at +3.4% a trade, 85% positive, worst -1.9%. A trade
with no crowd buy behind ours cannot be told apart before the buy; the exit makes it cost the two fees (about 0.5-0.8%), not the stake.

Releases 0.3 and 0.4 change the exit and drop the disguise:

- **Take profit:** the sell goes in the feed block of the first buy behind ours that prices the sell at `TAKE_PROFIT` (1%) after gas.
- **Deadline:** in any case it lands by our buy + `HOLD_BLOCKS` (4): sent when the feed shows our buy + 2, before the fastest pull seen
  (+5). `SELL_FALLBACK_S` 0.5.
- **The pool's price, from the feed:** the engine follows it through every buy (1e-15 from all eight real fills; the old prediction
  from the trigger alone was 4e-6 high on every one). `minOut` and the take-profit are priced on it. Buys that landed before a launch
  was armed are replayed onto it.
- **Entry:** `BUY_SLIP` 3%: a crowd buy that lands ahead of ours makes our buy revert instead of filling behind it, where nothing is
  left on its way. A stale or pre-arm first buy is recorded, so the crowd's next buy is never mistaken for the trigger.
- **Halt:** if a pull ever lands at or before our sell, or a filled buy's sell sells nothing, the engine writes
  `/var/log/flip/HALTED` and fires nothing more until the file is removed.
- **The relay only (0.4):** the exit has to work whether or not the operator sees us, and on the relay it does (all seven relay
  trades repriced above). The relay's sell is signed with the buy and sells everything the relay holds, so it can go the moment it is
  due. The router's sell needed two approvals first (on trade 8 they landed one and two blocks after the buy) and an exact amount
  (trade 8's -9.3%). Its one advantage, the missing pull on trade 8, is one trade, and the exit does not need it.
- `BUY_DELAY_BLOCKS` (default 0) is there for one open reading: the four trades whose buy landed two blocks after the trigger all had
  the crowd's next buy right behind them; of the three that landed one block after it, two had none. Seven trades do not settle it.

## The operator's new scheme, and the seat (release 0.5)

From Oct 8 14:59, about half an hour after our last trade, the operator changed two things (`research/new_scheme.py`, output in
`research/data/new_scheme_oct8.txt`):

- **A fresh launcher per launch.** Each launch is a newly deployed copy of the launcher (the same 6,984 bytes), called with the same
  function (`0x2fcb9108`). An engine watching the old address sees nothing: 40 launches by 16:45, about one every 1-3 minutes.
- **The crowd in one burst.** Its first three buys (0.01-0.11 ETH each, about 0.18 ETH together, three fresh wallets) land in one block
  8-9 blocks after the launch (30 of 42 at +9, 7 at +8), then almost nothing until a scheduled pull 40 s or 2.5 minutes later. There is
  no buy left to follow: the follow trade prices at -0.5% on all 40 launches, and no other launch family shows the old pattern.

What is left is the seat ahead of the burst: our buy landing one or two blocks before it, sold on it. On paper, if the operator still
sends its burst after seeing our buy, that is +9.0% a trade at $3, 40 of 40 positive, worst +6.6% (+5.8% at $0.39, +9.3% at $12.85).
That "if" is the whole question. A live trade answers it: the old scheme's first-seat outsiders got nothing (report 24.54), but the
chain-wide dust tester that buys every launch at +3-5 gets the burst every time, and the old crowd buy one block behind ours always
came (trades 2-5), while the one two blocks behind was cancelled (trades 6 and 7).

`ENTRY=seat` with `LAUNCH_SELECTORS=2fcb9108`: the engine arms a launch by its call, fires when the feed shows launch + `SEAT_FIRE_AT`
(6), so our buy lands at +7 or +8; the burst behind it is the take-profit, and the deadline and the halt are unchanged. A burst that
lands first makes the pool late (no trade); one in our own block makes our buy revert (3% slip). Replayed on the real blocks of the
last ten launches, the engine took the burst on nine and sold the tenth (burst at +13) at the deadline. Both settings are off by
default; `ENTRY=follow` is the old entry.

Overnight Oct 8-9 the operator went back to its original launcher and its old crowd (first buy 40-60 blocks in, then a buy every few
blocks), where the seat sold flat (two live trades, -0.18% and -0.32%, both out before the pull). `ENTRY=auto` (release 0.7) takes the
seat on a per-launch launcher copy and the follow on the original launcher. Release 0.8 carries the review's fixes: the buy is sent from
its own thread, the nonce is the chain's after every trade, a launcher's code is read again at the launch's block, and a buy that
never went in does not count against the daily cap.

Release 0.9 adds a second strategy, `FRONT`: ahead of a volume bot's scheduled first buy on its 2.4333285 ETH PositionManager launches (about 330 a
day, +13% a trade in an exact replay), armed from the launch transaction in the feed, with its own dry-run switch, daily cap and halt. A census of
every v4 ETH pool since Oct 8 found no other operator running the follow pattern, and the volume bot's other families pull on outsiders.
An independent review of 0.9 before its first run made the two strategies independent in everything but the one position slot: each
has its own daily stop and its own halts, a front-only problem (the relay short of the front stake, a bad setting) turns front off and
leaves follow running, follow has the slot first (front waits while a follow launch that follow can trade waits for its crowd, and a
front trade leaves the slot as soon as both its receipts are in, before its 3-second pull check), and no front launch, however malformed, can cost follow a block. A front launch is
known by its value and calldata; a change in its fee tier (within sub-1%), tick spacing, launch price or liquidity (identical on every
launch seen) is traded and flagged in results.py (`FRONT_PIN=1` skips such launches instead). At most 0.008 ETH may sit ahead of the bot's
buy with ours, and a bot buy that would fail its 99% minOut is not counted as a take-profit. On Oct 10 afternoon (HANDOFF section 16) the bot's
buy became known by its router at any size (its two 0.00495 ETH buys were the day's two -100% trades: the engine had waited for its deadline),
follow got its own near-miss halt (a pull within 4 blocks of our buy, even behind our sell, stops follow, not front), and `relay_ops.py` a
`payout` command.

## Layout

| path | what |
|---|---|
| `src/flip_engine.py` | the engine: reads the sequencer feed, arms each launch from its receipt, follows each pool's price through every buy, fires on the operator's first real-size buy, sells on the first buy behind ours worth `TAKE_PROFIT` or by our buy + `HOLD_BLOCKS`; halts itself if the pull ever beats the sell; one position at a time, daily cap and stop; `DRY_RUN=1` by default |
| `contracts/FlipRelay.sol`, `FlipRelay.json`, `compile.py` | the relay: buys with its own ETH and sells everything it holds, straight through the PoolManager (no router, no approval); the sell can be signed before the buy's receipt exists. `RoundTripHarness.sol` is test-only. |
| `src/v4math.py` | exact single-range v4 pricing (validated to 1e-13 on 60,000 real swaps) |
| `src/score.py` | prices every engine decision from the chain afterwards with the engine's exit: paper vs live, the crowd behind us, the pull against our sell |
| `deploy/flip_setup.sh` | the box: venv, `/etc/flip/engine.env`, the `flip-engine` service, the log |
| `deploy/relay_sim.py` | a buy and a sell through the relay on a live pool with no transaction (eth_call with state overrides) |
| `deploy/results.py` | **the results in one screen**: `sudo python3 ~/v2pons/deploy/results.py` (state, launches, every trade, totals, money) |
| `deploy/relay_deploy.py`, `relay_ops.py`, `englog.py`, `health.sh`, `watch.sh` | deploy the relay, move the stake, read the log, watch the trades as they happen |
| `tests/` | `test_v4math.py` (the pricing), `test_engine.py` (the engine on a scripted feed: real signed transactions in real batch frames, the chain stubbed) |
| `research/` | the analysis scripts, their data and outputs, the survey of other chains and launchpads, report section 24.54; `live_trades.py` reads the live trades back from the chain (`data/live_trades_oct8.txt`), `new_scheme.py` the operator's scheme from 14:59 (`data/new_scheme_oct8.txt`) |
| `docs/RUNBOOK.md` | from a fresh wallet to the first $3 trade, the dry run's pass criteria, the exit (4b), the stop rules |
| `docs/HANDOFF.md` | **start here to continue the project**: the goal, the chain and every address, both strategies, all the research of Oct 8-10 and its results, every release, every live trade, the box and its commands, the state at the Oct 10 handoff and the open items |
| `research/session_oct9_10/` | every research script and result of Oct 9-10 (operator A's money loop and origins, the census of every v4 operator, the volume bot's families and reaction, the rule search, the front replay, the fingerprint history, the dry-run check, the protection backtest), indexed by its README; `front_audit/` and `follow_audit/` are the Oct 10 afternoon's reads of the chain (every live front trade; operator A's day) |

## The trade, exactly

1. A transaction to the launcher appears on the feed. The engine fetches its receipt (about 50 ms from Ohio) and reads the pool's
   key, initial price and liquidity from the `Initialize` and `ModifyLiquidity` events. Pools with a fee outside `FEE_MIN_PPM..FEE_MAX_PPM`
   (default: under 1%), a hook, a non-ETH pair or too little liquidity are logged and not traded.
2. Every transaction carrying the token's address with ETH as its value is a buy and moves the engine's copy of the pool's price. The
   first with `value >= MIN_TRIGGER_ETH` (0.0002) is the operator's first buy (306 of 312 times in the data). It must come within
   `TRIGGER_MAX_BLOCKS` (150) of the launch; later buys are outsiders.
3. The engine prices our buy on the pool as the feed shows it and signs it to the relay: `STAKE_ETH` at `minOut` = prediction × (1 −
   `BUY_SLIP`, 3%), a 3 s deadline; the sell is signed at once at the next nonce. Our buy lands one or two blocks after the trigger block.
4. When our buy shows in the feed, the engine knows the tokens it got (the pool as the feed showed it at that point). Each buy behind
   ours is priced at once: the first that makes the sell worth `TAKE_PROFIT` (1%) after gas sends the sell. Otherwise the sell goes when
   the feed reaches buy block + `HOLD_BLOCKS` − `SELL_LEAD_BLOCKS` (4 − 2), so it lands by our buy + 4; the operator pulled 5-13 blocks
   after each of our relay buys. A wall-clock fallback (`SELL_FALLBACK_S`, 0.5 s after the buy was sent) sends it anyway if the feed
   stalls. After a reverted buy the sell finds nothing to sell and reverts too (gas only).
5. Both receipts are read; three seconds later the pool's liquidity events. The P&L, the landing offsets, the sell's reason, the
   pull's block after our buy and whether it landed before our sell go to the log as
   `trade_done`. A pull before our sell, or a filled buy whose sell sold nothing, halts live trading (`/var/log/flip/HALTED`).

## Reproducing the research

`research/v4_slowrug_pull.py` pulls the operator's launches from the public RPC; `research/v4_slowrug_test.py` reproduces every table
of report 24.54 from `research/data/*.json.gz`.
