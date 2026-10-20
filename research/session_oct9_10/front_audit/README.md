# front_audit: every live front trade of Oct 10 read from the chain, and the two -100% trades (HANDOFF 12.1)

Written Oct 10 ~13:00 UTC from this repository's container (the public RPC answers from it). Scripts import `../chain.py` and `src/v4math.py`
by absolute path (`/home/user/v2pons/...`), as the other Oct 9-10 scripts do.

| file | what |
|---|---|
| `step1_our_swaps.py` | every `Swap` with our relay as sender since 09:00 UTC (808 swaps, 405 trades: 401 front + 4 follow at the $3 stake), paired per pool into `our_swaps.json`; then, for every trade whose sell got nothing, the pool's whole record (`losers.json`: Initialize, every Swap and ModifyLiquidity, every transaction in the blocks launch..sell+3 with its status, reverted ones included) |
| `step2_full_audit.py` | for all 405 trades: the launch block, our buy, every buy behind ours (the bot's by its router `0x1cbaf24d`), the pull, our sell -> `full_audit.json`, the distributions below, and the counterfactual for the two losers |

Findings (the numbers are in the two JSON files):

- **The two -100% trades (10:48:55 and 11:11:55 UTC) were pools where the volume bot's first buy was 0.00495 ETH**, its smallest size, under
  the engine's `FRONT_SELL_ON_ETH` of 0.005 and under `FRONT_BOT_MIN_ETH` 0.04, so the engine neither took it for the bot's buy nor sold on it;
  the take-profit was not met (-0.1%); the sell waited for the 18-block deadline (sent at our buy + 18, landed at launch + 20) and **reverted
  out of gas** (335,520 of 350,000: a swap into a pool with no liquidity walks the tick bitmap to the price limit); the operator had pulled at
  launch + 12 / + 11, **3 blocks after its bot's buy, exactly as in 367 of the 400 pools where the bot bought**. Not a reaction to us, not a
  stall (20 blocks in 2 s). Sold on the bot's buy, each would have returned -0.10% (-0.17% after gas). Fix: `FRONT_BOT_ROUTERS` (the bot's buy
  known by its router at any size) and `FRONT_SELL_ON_ETH` 0.001 (test 18m2).
- 405 relay trades 09:08-11:39 UTC: mean +13.97%, median +16.25%, 396 up, 7 flat-to-down (-0.1% to -0.5%), 2 lost (the two above). By stake:
  $5 (0.00195) 61 trades +14.2%; $10 (0.0039) 23 +13.6%; $15 (0.0058) 317 +14.1% (315 priced), the 2 losses at $15.
- Our buy at launch + 1 in 399 of 401 front trades, + 2 in 2. The bot's first buy at + 7..10 in 369, + 11..19 in 29, + 59 once, + 130 once
  (a sequencer stall at 09:15), never in 5 (follow trades and three pools pulled with no bot buy, our sell at the deadline for -0.3..-0.5%).
- The bot's first-buy size: min 0.00495, 5th percentile 0.0248, median 0.198, 95th 0.287, max 0.335 ETH; 36 of 400 under 0.04 (0.005-0.03),
  all of those sold on the buy for +0.4% to +1.9% except the two at 0.00495. Its sizes cluster at 0.99 x a round number (0.00495, 0.02475, 0.07425).
- The pull: 2-4 blocks after the bot's buy in 400 of 400 (3 in 367); 1-3 blocks after our sell in 398 (2 in 363); before our sell in the 2 losses.
- Nobody but the operator's decoys (2e-6 ETH via the Universal Router at + 3, 0.000119 ETH from `0x65050a9b` at + 3..5) bought behind us before
  our sell in any pool; no second bot buy before our sell.
- The last relay trade of the day was at 11:39:54 UTC: front reached its 400-trade daily cap (`FRONT_MAX_PER_DAY`).
