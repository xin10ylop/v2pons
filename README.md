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

## Layout

| path | what |
|---|---|
| `contracts/FlipRelay.sol`, `FlipRelay.json`, `compile.py` | the relay: buys with its own ETH and sells everything it holds, straight through the PoolManager (no router, no approval); the sell can be signed before the buy's receipt exists. `RoundTripHarness.sol` is test-only. |
| `src/flip_engine.py` | the engine: reads the sequencer feed, arms each launch from its receipt, fires on the operator's first real-size buy, sells HOLD_BLOCKS after our buy's block; one position at a time, daily cap and stop; `DRY_RUN=1` by default |
| `src/v4math.py` | exact single-range v4 pricing (validated to 1e-13 on 60,000 real swaps) |
| `src/score.py` | prices every engine decision from the chain afterwards: paper vs live, the crowd behind us, the pull's timing |
| `deploy/flip_setup.sh` | the box: venv, `/etc/flip/engine.env`, the `flip-engine` service, the log |
| `deploy/relay_sim.py` | a buy and a sell through the relay on a live pool with no transaction (eth_call with state overrides) |
| `deploy/relay_deploy.py`, `relay_ops.py`, `englog.py` | deploy the relay, move the stake, read the log |
| `tests/` | `test_v4math.py` (the pricing), `test_engine.py` (the engine on a scripted feed: real signed transactions in real batch frames, the chain stubbed) |
| `research/` | the four analysis scripts, their data and outputs, the survey of other chains and launchpads, report section 24.54 |
| `docs/RUNBOOK.md` | from a fresh wallet to the first $3 trade, the dry run's pass criteria, the stop rules |

## The trade, exactly

1. A transaction to the launcher appears on the feed. The engine fetches its receipt (about 50 ms from Ohio) and reads the pool's
   key, initial price and liquidity from the `Initialize` and `ModifyLiquidity` events. Pools with a fee outside `FEE_MIN_PPM..FEE_MAX_PPM`
   (default: under 1%), a hook, a non-ETH pair or too little liquidity are logged and not traded.
2. The first transaction carrying the token's address with `value >= MIN_TRIGGER_ETH` (0.0002) is the operator's first buy (306 of
   312 times in the data). It must come within `TRIGGER_MAX_BLOCKS` (150) of the launch; later buys are outsiders.
3. The engine predicts the pool after that buy, signs the buy (`STAKE_ETH` at `minOut` = prediction × (1 − `BUY_SLIP`), a 3 s deadline)
   and the sell at the next nonce, and sends the buy. Our buy lands one or two blocks after the trigger block.
4. The feed shows our buy's block. The sell goes out when the feed reaches buy block + `HOLD_BLOCKS` − `SELL_LEAD_BLOCKS` (7 − 2 = 5), so
   it lands about 7 blocks (0.7 s) after the buy; the operator's reaction in this fee tier comes 10-19 blocks after an outside buy.
   A wall-clock fallback (`SELL_FALLBACK_S`) sends it anyway if the feed stalls.
5. Both receipts are read; the P&L, the landing offsets and whether a liquidity pull came inside the hold go to the log as `trade_done`.

## Reproducing the research

`research/v4_slowrug_pull.py` pulls the operator's launches from the public RPC; `research/v4_slowrug_test.py` reproduces every table
of report 24.54 from `research/data/*.json.gz`.
