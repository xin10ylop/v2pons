# v2pons — the crowd-following flip on Robinhood Chain

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
pools comes from (99.8% of 60,496 swaps on 371 launches). Release 0.2 removed that tell: the engine sends the crowd's own transaction
from the wallet (`ROUTE=router`), byte for byte the shape of theirs, and sells the way the operator's fleet sells.

## The eight live trades, from the losers' side (release 0.3)

Read back from the chain (`research/live_trades.py`, output in `research/data/live_trades_oct8.txt`): seven through the relay
(13:15-13:20 UTC) and the first through the router (14:32).

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

Release 0.3 changes the exit, not the route:

- **Take profit:** the sell goes in the feed block of the first buy behind ours that prices the sell at `TAKE_PROFIT` (1%) after gas.
- **Deadline:** in any case it lands by our buy + `HOLD_BLOCKS` (4): sent when the feed shows our buy + 2, before the fastest pull seen
  (+5). `SELL_FALLBACK_S` 0.5.
- **The exact sell amount:** the engine follows the pool's price through every buy on the feed (1e-15 from all eight real fills; the
  old prediction from the trigger alone was 4e-6 high on every one), so a router sell due before the receipt sells that count less
  0.1% (`SELL_AMOUNT_MARGIN`), not `minOut`. Buys that landed before a launch was armed are replayed onto it.
- **Entry:** `BUY_SLIP` 3%: a crowd buy that lands ahead of ours makes our buy revert instead of filling behind it, where nothing is
  left on its way. A stale or pre-arm first buy is recorded, so the crowd's next buy is never mistaken for the trigger.
- **Halt:** if a pull ever lands at or before our sell, or a filled buy's sell sells nothing, the engine writes
  `/var/log/flip/HALTED` and fires nothing more until the file is removed.
- `BUY_DELAY_BLOCKS` (default 0) is there for one open reading: the four trades whose buy landed two blocks after the trigger all had
  the crowd's next buy right behind them; of the three that landed one block after it, two had none. Seven trades do not settle it.

## Layout

| path | what |
|---|---|
| `src/ur.py` | the crowd's calldata: the Universal Router `execute` for a buy and a sell (V4_SWAP: SWAP_EXACT_IN_SINGLE, SETTLE_ALL, TAKE_ALL), the fleet's two approvals; reproduces two real transactions byte for byte (`tests/test_ur.py`) |
| `src/flip_engine.py` | the engine: reads the sequencer feed, arms each launch from its receipt, follows each pool's price through every buy, fires on the operator's first real-size buy, sells on the first buy behind ours worth `TAKE_PROFIT` or by our buy + `HOLD_BLOCKS`; halts itself if the pull ever beats the sell; one position at a time, daily cap and stop; `DRY_RUN=1` by default; `ROUTE=router` (the crowd's path) or `relay` |
| `contracts/FlipRelay.sol`, `FlipRelay.json`, `compile.py` | the relay (`ROUTE=relay`): buys with its own ETH and sells everything it holds, straight through the PoolManager (no router, no approval). `RoundTripHarness.sol` and `RouterRoundTrip.sol` are test-only. |
| `src/v4math.py` | exact single-range v4 pricing (validated to 1e-13 on 60,000 real swaps) |
| `src/score.py` | prices every engine decision from the chain afterwards with the engine's exit: paper vs live, the crowd behind us, the pull against our sell |
| `deploy/flip_setup.sh` | the box: venv, `/etc/flip/engine.env`, the `flip-engine` service, the log |
| `deploy/router_sim.py`, `relay_sim.py` | a buy and a sell through the router (or the relay) on a live pool with no transaction (eth_call with state overrides) |
| `deploy/relay_deploy.py`, `relay_ops.py`, `englog.py`, `health.sh` | deploy the relay, move the stake, sell a token left in the wallet (`dump`), read the log |
| `tests/` | `test_v4math.py` (the pricing), `test_ur.py` (the router bytes against the chain), `test_engine.py` (the engine on a scripted feed, both routes: real signed transactions in real batch frames, the chain stubbed) |
| `research/` | the analysis scripts, their data and outputs, the survey of other chains and launchpads, report section 24.54; `live_trades.py` reads the live trades back from the chain (`data/live_trades_oct8.txt`) |
| `docs/RUNBOOK.md` | from a fresh wallet to the first $3 trade, the dry run's pass criteria, the router test, the stop rules |

## The trade, exactly

1. A transaction to the launcher appears on the feed. The engine fetches its receipt (about 50 ms from Ohio) and reads the pool's
   key, initial price and liquidity from the `Initialize` and `ModifyLiquidity` events. Pools with a fee outside `FEE_MIN_PPM..FEE_MAX_PPM`
   (default: under 1%), a hook, a non-ETH pair or too little liquidity are logged and not traded.
2. Every transaction carrying the token's address with ETH as its value is a buy and moves the engine's copy of the pool's price. The
   first with `value >= MIN_TRIGGER_ETH` (0.0002) is the operator's first buy (306 of 312 times in the data). It must come within
   `TRIGGER_MAX_BLOCKS` (150) of the launch; later buys are outsiders.
3. The engine prices our buy on the pool as the feed shows it and signs it: `STAKE_ETH` at `minOut` = prediction × (1 − `BUY_SLIP`, 3%), a 3 s deadline
   (`BUY_DEADLINE_S=0` for the crowd's own 2^256-1). On the router route the buy is the crowd's transaction from the wallet: type 2, to the
   Universal Router, the stake as the value, their calldata, their gas limit and tip. Right behind it go the fleet's two approvals at the
   next two nonces (the token to Permit2, Permit2 to the router). On the relay route the buy goes to the relay and the sell is signed at
   once at the next nonce. Our buy lands one or two blocks after the trigger block.
4. When our buy shows in the feed, the engine knows the tokens it got (the pool as the feed showed it at that point). Each buy behind
   ours is priced at once: the first that makes the sell worth `TAKE_PROFIT` (1%) after gas sends the sell. Otherwise the sell goes when
   the feed reaches buy block + `HOLD_BLOCKS` − `SELL_LEAD_BLOCKS` (4 − 2), so it lands by our buy + 4; the operator pulled 5-13 blocks
   after each of our relay buys. On the router route the sell (the fleet's transaction, at the fourth nonce) carries the receipt's exact
   amount, or, if it is due before the receipt, the feed's count less `SELL_AMOUNT_MARGIN` (0.1%); the leftover is reported for
   `relay_ops.py dump`. A wall-clock fallback (`SELL_FALLBACK_S`, 0.5 s after the buy was sent) sends it anyway if the feed stalls; a
   reverted buy sends no sell.
5. All receipts are read; three seconds later the pool's liquidity events. The P&L (the approvals' gas included), the landing
   offsets, the sell's reason and amount source, the pull's block after our buy and whether it landed before our sell go to the log as
   `trade_done`. A pull before our sell, or a filled buy whose sell sold nothing, halts live trading (`/var/log/flip/HALTED`).

## Reproducing the research

`research/v4_slowrug_pull.py` pulls the operator's launches from the public RPC; `research/v4_slowrug_test.py` reproduces every table
of report 24.54 from `research/data/*.json.gz`.
