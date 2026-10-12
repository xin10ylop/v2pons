# REPORT_X: our sell timing, the operator's reaction (Oct 10 vs Oct 11), and whether our address is tracked

Hand-back about 00:20 UTC on Oct 12 (an Opus analyst; the text is its report, saved by the session). All data comes from the public RPC,
read-only, with W's pacing (0.5 s between requests): about 2,970 requests in all.

What was measured, Oct 10 00:00 to Oct 11 23:11 UTC:
- every 2.433 launch (1,852) and every 3.0 launch (1,143) of the volume bot;
- every Swap and ModifyLiquidity log of those pools, to launch + 1,200 blocks;
- the transaction behind every swap to launch + 400 (47,652 transactions);
- every swap our relay made (2,495 swaps, which make 1,249 trades: 1,237 on 2.433, 1 on 3.0, 11 follow trades on operator A).

Wherever this report says "T", it means the block of the bot's first buy. Returns come from the swap amounts, before gas. Dollars use $2,570/ETH.

## The three answers

**1. Sell timing.** Measured against the bot's buy, today's sell lands one block later than yesterday's. Yesterday most sells landed at T+1
(394 of 401 trades on Oct 10 morning). Today most land at T+2 (134 of 189), and 40 land at T+1. Measured against our own buy, nothing
changed: about 9 blocks on both days, because our buy also lands one block later (+2 instead of +1). Neither the bot nor the operator caused
this. The bot's T is the same on both days (median +9). The cause is our feed: since Oct 11 13:38 the engine reads the Dwellir feed, which
shows each block about one block later than the public feed did. The cost is small: 0.15 points per trade on average, and a median of 0,
against a sell placed right behind the bot's buy.

"Selling sooner" does not exist as a way to make money. Before T, only other early buyers trade, and the price barely moves. Our tokens are
worth -0.5% at the end of our own buy's block. That is the round-trip fee: -0.5% at fee 2500, -1.0% at fee 5000. We checked every block
before T in 1,232 trades. The best one was +0.31% (Oct 10) and -0.06% (Oct 11). The profit (+12% to +16%) exists only from the bot's buy
onward. The one real "sooner" case is Oct 10 afternoon. Then 382 sells landed before T, because the engine's size rule sold on other buyers'
0.0015/0.005 ETH buys. Those 382 trades made +0.09% on average.

**2. The operator's reaction.** On both days the operator treats a pool according to whether someone bought before its bot. It does not
matter who that someone is.
- From Oct 10 00:00 until Oct 11 15:31, every pool where anyone bought 0.001 ETH or more ahead of the bot was pulled 3 blocks after the
  bot's first buy (T+3). The bot never bought a second time in those pools.
  - Our pools: 1,068 of 1,165 pulled by T+3 and 1,157 by T+10.
  - 2.433 pools fronted by others with no us: 230 of 270 by T+3 and 262 by T+10. This includes 205 pools fronted by fresh wallets while we
    were cut off.
  - Pools where nobody bought ahead were never pulled by T+10 (103 on 2.433, 788 on 3.0).
- From 15:32 Oct 11, when the fee went to 5000, nobody's pool is pulled at T+3, ours included. Since then, 0 of our 67 pools with a bot buy
  were pulled by T+10, and the bot's second buy came in 66 of them.
- The bot's first buy is not smaller in our pools: 0.165 ETH mean, against 0.149 in the other pools of the same hours.
- The "decoys" are in every pool, with or without us. They started before our first trade. They are funded in a closed loop of their own
  (details below), with no link to the bot's wallets.
- The decoy count dropped from two to one at about 20:50 UTC on Oct 11, not 21:30.
  - From 16:30 to 20:50: 33 pools had two (0x65050a9b + 0xfd1b271f), 14 had one, 6 had none.
  - From 20:50 to 23:11: 26 pools had exactly one (a fresh 0x65050a9b wallet), and one pool (22:08:46) had two.
  - The second buyer (0xb8c879dc via 0xfd1b271f) last bought at 20:49:13.

**3. Is our address tracked?** No sign of it. Every reaction we can measure follows behaviour (a buy ahead of the bot), not an address.
Confidence: high for the pulls and the decoys, medium-high overall. The things that would show tracking are all absent:
- the same pull hit other front-runners before our first trade ever;
- it hit them in the same hours as us, and while we were gone;
- it hit a front-runner that already used a fresh wallet for every trade;
- it stopped for us when it stopped for everyone;
- no transaction anywhere names our wallet or relay.

Rotating fresh wallets would not hide us, and it would change nothing the operator acts on:
- Our relay's owner is fixed. A fresh wallet cannot call the relay at all, so each rotation would need a new relay.
- The relay is the `sender` in every one of our Swap events.
- Every fresh wallet must be funded from somewhere. That is one hop back to us. It is exactly how we linked the "decoys'" 542 fresh wallets
  to two collector wallets in one afternoon.
- Our gas price (legacy, 0.060-0.062 gwei) is unique among 47k buyer transactions.
- The +1/+2 buy that sells at T+1/T+2 is the fingerprint the operator actually reacts to.

## 1. Our sell timing: the evidence

Our trades on 2.433, per 6-hour period (no trades Oct 10 18:00 to Oct 11 14:26: the feed block, then the restart):

| period (UTC) | trades | stake ETH (trades) | our buy at +1 / +2 / +3 | bot's T p10/50/90 | sell, blocks after our buy p10/50/90 | sell vs T: before / T+0 / T+1 / T+2 / T+3+ / no sell | return mean / median | pulled by T+3 | not pulled by T+60 | net |
|---|---|---|---|---|---|---|---|---|---|---|
| Oct 10 06-12 | 401 | 0.0058 (317), 0.0019 (61), 0.0039 (23) | 399 / 2 / 0 | 8/9/10 | 8/9/10 | 2 / 1 / 394 / 1 / 0 / 3 | +14.1% / +16.2% | 377 | 0 | +$706 |
| Oct 10 12-18 | 647 | 0.0058 (647) | 639 / 8 / 0 | 8/9/10 | 1/2/10 | 382 / 0 / 263 / 1 / 0 / 1 | +5.7% / +0.3% | 583 | 4 | +$534 |
| Oct 11 12-18 | 131 | 0.0058 (100), 0.002 (25), 0.0097 (6) | 4 / 124 / 3 | 8/10/14 | 8/9/13 | 4 / 0 / 32 / 86 / 6 / 3 | +11.6% / +13.7% | 108 | 9 | +$198 |
| Oct 11 18-24 | 58 | 0.002 (39), 0.0069 (9), 0.0021 (6) | 1 / 56 / 1 | 7/8/11 | 7/8/10 | 1 / 0 / 8 / 48 / 0 / 1 | +10.4% / +11.2% | 0 | 56 | +$48 |

Total: 1,237 trades and +$1,486 before gas. This matches the owner's ~1,240 trades and +$1,460.

The pull: on Oct 10 it came 2 blocks after our sell in 361 of the first 401 trades. On Oct 11 it came at T+3 until 15:31, and not at all
after that.

What the price did between our buy and T (1,232 trades where the bot bought after us). Our tokens were valued at the end of each block,
from the pool's state after that block's last swap:

| day | trades | value at the end of our buy's block (median) | best block before T: median / p90 / max | trades with any block before T above +0.5% | right behind the bot's buy (median) | actual sell (median) | actual minus right behind the bot (mean) |
|---|---|---|---|---|---|---|---|
| Oct 10 | 1,047 | -0.50% | -0.50% / +0.31% / +0.31% | 0 | +15.3% | +7.7% | -0.03 points |
| Oct 11 | 185 | -0.50% | -0.50% / -0.10% / -0.06% | 0 | +12.0% | +12.0% | -0.16 points |

- Between our buy and T, the only trades are other early buyers: a median of 0 ETH on Oct 10 and 0.0046 ETH on Oct 11. That is why the best
  pre-T value never passed +0.31%.
- On Oct 11, selling at T+1 or at T+2 costs the same: 0.16 and 0.15 points on average, 0.00 at the median.
- Oct 10 12:00-18:00: the 382 sells before T made +0.09% on average. The 263 sells at T+1 made +13.8%.
- The one 3.0 trade (the probe at 15:48 Oct 11) bought at +13 with 0.002 ETH. The pool was pulled at +22, 9 blocks later. The bot never
  bought. Result: -100%.

## 2. The operator's reaction, Oct 10 vs Oct 11: the evidence

Pools by window and by who bought 0.001 ETH or more ahead of the bot's first buy. The line is 2.433 unless the row says 3.0. Pulls count to
launch + 1,200 blocks.

| window (UTC) | ahead of the bot | pools | pulled by T+3 | by T+10 | bot's 2nd buy |
|---|---|---|---|---|---|
| Oct 10 00:00-09:08, before our first trade | others, small buys only (under 0.001) | 189 | 5 | 9 | 163 |
| same, 3.0 | others via the Universal Router (0x9f3b9a44 0.003, 0x9a128676 0.00015) | 10 | 6 | 10 | 0 |
| Oct 10 09:08-11:40 | us (at +1) | 401 | 377 | 400 | 0 |
| Oct 10 13:38-17:37 | us | 646 | 583 | 640 | 5 |
| same | others (0x65050a9b), no us | 10 | 10 | 10 | 0 |
| Oct 10 17:37-19:28, our feed cut | others: 0x65050a9b fresh wallets | 205 | 176 | 198 | 4 |
| same | others: 0x65050a9b recurring wallets | 55 | 44 | 54 | 1 |
| Oct 10 19:28 to Oct 11 11:39 | **the 2.433 line paused for 16.2 h** (it started 1 h 51 min after our last trade, while only others fronted) | | | | |
| Oct 11 00:00-14:26, 3.0 | others: 0x8cf143dd and 0x7ae81404 via 0x65050a9b (238 of these 253 pools had a bot buy) | 253 | 201 | 230 | 8 |
| Oct 11 11:39-14:26 | nobody, or small buys | 34 | 0 | 0 | 34 |
| Oct 11 14:26-15:32 (fee 2500) | us (at +2) | 118 | 108 | 116 | 0 |
| Oct 11 15:32-16:07 (fee 5000, our engine refused it) | others: 1 pool with a 0.00495 buy, 6 with small buys | 7 | 0 | 0 | 1 |
| Oct 11 16:07-17:00 | us (0.0058 / 0.0097) | 13 (10 with a bot buy) | 0 | 0 | 10 |
| Oct 11 16:52-17:58, our engine dry | others (fresh 0x65050a9b plus 0xfd1b271f) | 8 | 0 | 0 | 7 |
| Oct 11 17:58-23:11 | us (0.002 / auto) | 58 (57 with a bot buy) | 0 | 0 | 56 |
| both days, all windows | nobody ahead | 2.433: 103, 3.0: 788 | 0 | 0 | all but 2 |

**The same timing and size, the same hours** (Oct 10 14:00-17:59, the hours when both we and others fronted):
- our pools with no other big buyer: 196. Pulled by T+3: 92%. By T+10: 100%. Bot's second buy: 0.
- others' pools without us: 68. All were buys of 0.004-0.006 ETH, and 60 of them sold at T-1..T+2, which is our behaviour. Pulled by T+3:
  79%. By T+10: 94%. Bot's second buy: 4.
- The pull came at the same distance after the first early buy: a median of 11 blocks for us and 10 for them.

Our pools were not pulled faster or more often in any way that matters. The extra block for the others comes from their buy landing at +2/+3
where ours landed at +1.

**Our sell did not cause the pull; the early buy did.** On Oct 10 afternoon, 382 of our pools had our sell come before T (we had already
left at about 0%). They were still pulled by T+3 in 336 (88%). The pools where we sold at T+1 were pulled by T+3 in 246 of 264 (93%).

**The 3.0 trap pull is the same for everyone** (Oct 11 afternoon; the bot never bought in any of these pools):

| buyer | router | buys | pools | pulled | blocks from the buy to the pull |
|---|---|---|---|---|---|
| 0x7ae81404 | 0x65050a9b | 0.00297 at +1/+2 | 4 | 4 | 5-7 |
| 0x8c009ea5 | 0x7ebacc35 | 0.002 at +4..+6 | 22 | 22 | 3-6 in 18; 17-23 in 4 |
| us | relay | 0.002 at +13 | 1 | 1 | 9 |

### The "decoys": who they are, when they started, how they are funded

Throughout this report, "0x65050a9b" and "0xfd1b271f" are the two routers the decoy buyers call. The two contracts are twins: 752 bytes
each, differing only in an embedded 20-byte admin address. Each has its own admin owner: 0x0c628d65 for 0x65050a9b (nonce 3,025) and
0x04a802fe for 0xfd1b271f (nonce 1). Each router keeps 1% of the buy: a transaction value of 0.005 ETH shows up as a 0.00495 swap. That is
why the sizes look like the bot's "0.99 x round" sizes.

| what | first seen | last seen | wallets | buys ahead of the bot |
|---|---|---|---|---|
| tiny buys, fresh wallets via 0x65050a9b, 2.433 | Oct 10 04:34 (0.000129) | Oct 10 09:28 | 197 | 197 |
| tiny buys, recurring wallets via both routers (0x488faf52, 0xb002e8a0, 0xf05d0e3f...), 2.433 | Oct 10 01:33 | Oct 10 16:03 | 6 | 262 |
| 0.00099-0.00495, recurring 0x488faf52 / 0x544ef435 / 0xe322fc6d via 0x65050a9b, 2.433 | Oct 10 14:51 | Oct 10 17:58 | 3 | 479 |
| 0.0012-0.00495, 0xb4c345dc via 0xfd1b271f, 2.433 | Oct 10 16:03 | Oct 10 19:28 | 1 | 391 |
| 0.00495, a fresh wallet per pool via 0x65050a9b, 2.433 | Oct 10 18:11 (we were already cut off) | Oct 10 19:28 (the line paused) | 205 | 205 |
| 0.00297-0.00495, 0x8cf143dd / 0x7ae81404 via 0x65050a9b, **3.0** (a line we never traded) | Oct 11 02:39 | Oct 11 13:18 | 2 | 253 |
| 0.000495, fresh wallets via 0x65050a9b, 2.433 | Oct 11 15:11 | Oct 11 15:17 | 20 | 20 |
| 0.0046-0.0053 (randomised after about 19:00), fresh wallets via 0x65050a9b, 2.433 | Oct 11 15:18 | Oct 11 23:10 (still going) | 118 | 118 |
| 0.00495, 0xb8c879dc via 0xfd1b271f, 2.433 | Oct 11 16:34 | Oct 11 20:49 | 1 | 33 |

- **They are in every pool, not only ours.** They started 4.5 hours before our first trade. While we were cut off (Oct 10 17:37-19:28) they
  bought in 260 of the 262 pools without us. In our dry hour (Oct 11 16:52-17:58) they bought in 8 of 11 pools. They fronted the 3.0 line,
  which we never traded.
- **They do not react to our buy.**
  - On Oct 10, 860 of their buys landed after our buy: 106 in the same block and 754 in later blocks. None landed before us.
  - On Oct 11, when our buy moved to +2, 27 landed before ours (9 of them in the same block) and 155 after (47 in the same block).
  - They fire on the launch, as we do.
- **How many:** 542 fresh (nonce 0/1) wallets and 17 recurring ones over the two days. Of the fresh wallets, 402 were on Oct 10 (197 tiny,
  205 at 0.00495) and 138 on Oct 11 (20 at 0.000495, 118 at 0.0046-0.0053).
- **How they are funded.** A collector wallet sends exactly 0.006 ETH to a fresh wallet. In one example the collector was 0x544ef435 and it
  paid 0x0adacbd8 3,309 blocks (5.5 min) before that wallet's buy, one block after the previous fresh wallet had emptied itself. The fresh
  wallet then does four things: buy (nonce 0), approve (nonce 1), sell at T+0..T+2 (nonce 2), and send its whole balance on (nonce 3,
  0.0058-0.0091 ETH).
  - Of the 341 that sold within 400 blocks, 337 sweeps were found: 287 went to 0x544ef435, 23 to 0xe322fc6d, 4 to 0x488faf52 and 1 to
    0xc522af57.
  - The other 22 went straight to the next fresh wallet, in three chains of 7, 8 and 10 wallets on Oct 11 16:22-18:41.
  - Each wallet ends with about 2.1e-6 ETH and a nonce of 3 or 4.
- **No shared funder with the bot** was found:
  - none of the 557 wallets that call the two routers is one of the bot's 141 buyer wallets or one of its 2,848 launch wallets;
  - no bot wallet ever calls the two routers;
  - the router admins' owners appear in none of the 47,652 pool transactions;
  - gas settings differ. The bot uses a tip of 0.024 gwei. 0x65050a9b's callers use a 0.002 gwei tip at 0.022 gwei. 0xfd1b271f's callers
    use a 0 tip at 0.020 gwei.
- **Two to one.** See answer 2: two per pool until 20:49, one per pool from 20:55, with one exception. That exception (22:08:46) had two
  0.00495 buys plus our 0.0069. The bot's buy never came, the pool was pulled at +41, and our trade made -0.6%. Our auto stake rose from
  0.002 to 0.0068 at 21:38.
- **Who they most likely are: other front-runners, not the operator** (medium confidence). Four points support this:
  - They profit from the bot. They sell into its buy at T+0..T+2 for +10% to +14% median on Oct 10 and +5% to +10% on Oct 11, and the
    profit flows back to their collectors.
  - The operator pulled their pools at T+3 exactly as it pulled ours, before our first trade and while we were gone.
  - The operator paused the 2.433 line for 16 h after 1 h 51 min in which only they fronted it.
  - The operator changed the 3.0 schedule at 04:22 Oct 11 after only 0x8cf143dd had fronted that line.

  Two facts fit both readings. On Oct 10 their sizes jumped to just above our engine's thresholds (0.001485, then 0.00495). On Oct 11 two of
  them at 0.005 each fill the room. A competitor that wants the bot's whole buy for itself would do the same. A link further up, beyond the
  collectors, cannot be excluded: the public node keeps state for only about 6,000 blocks and has no trace API.

## 3. Is our address tracked? The evidence

Against tracking:
1. The T+3 pull existed before we traded. 19 pools fronted by six other wallets (four buyer groups) were pulled by T+10 on Oct 10
   00:57-08:14, and 11 of them by T+3.
2. In the same hours and at the same size and behaviour, others were pulled like us: 94% vs 100% by T+10.
3. When we were gone (Oct 10 17:37-19:28), the pulls went on: 198 of 205 pools fronted by fresh-wallet buyers were pulled by T+10, and then
   the whole line paused. **Rotating a fresh wallet on every trade did not protect that front-runner**: same pull, same rate. Its router
   address stayed fixed, as our relay would.
4. On 3.0, our probe was pulled 9 blocks after our buy. Two other buyers, on two other routers, were pulled 3-7 blocks after theirs.
5. Since 15:32 Oct 11 nobody's pool is pulled at T+3. Ours are not: 0 of 67. The bot's second buy came in 66. A tracker would have kept
   ours as the pulled ones.
6. The decoys are present without us, in the same share. They land before our buy as often as our later feed allows. They fire on the launch.
7. No transaction names us:
   - Transfer logs over the two days: our relay only received tokens from, and sent them to, the PoolManager (1,249 and 1,244 transfers).
     Our wallet had none.
   - 0 swaps and 0 liquidity calls by others carry our wallet or relay in their calldata.
   - 0 transactions by others to or carrying our addresses in all 1,500 blocks around 124 sampled trades (every 10th trade), reverted
     transactions included.
8. The bot's first buy is not smaller in our pools (mean 0.165 vs 0.149 ETH).

For tracking: nothing we could find. The only difference is our 92% vs their 79% pulled by T+3. That is one block of timing, and it is
explained by our buy landing a block earlier. The pull came the same 10-11 blocks after the first early buy for both.

**What rotating wallets every 10 trades would and would not change.**

What it would not change:
- **The relay is the identity, not the wallet.** The relay is the `sender` topic of every Swap event we make. One `eth_getLogs` filter finds
  all 2,495 of our swaps, and x01 did exactly that. It is also the `to` of every one of our transactions. Its `owner` is `immutable` (the
  deployer), and `buy`/`sell` revert for anyone else. A fresh wallet cannot use it at all. Rotating means deploying a new relay from each new
  wallet (about 5.2 kB of code each time), or rewriting the relay with an allow-list.
- **Funding is one hop.** Every fresh wallet needs gas and the stake from our wallet or relay. The other front-runner's 542 fresh wallets were
  linked to two collectors with about 340 block reads, because each was paid 0.006 ETH by a collector and swept back to one. Linking ours
  would be just as easy.
- **The gas fingerprint stays.** Our transactions are legacy type at 0.060-0.062 gwei: 1,227 of 1,238 buys. No other buyer among the 47,652
  transactions uses that price.
- **The behaviour stays.** A buy at +1/+2 of 0.002-0.01 ETH, sold at T+1/T+2, is what the operator reacted to, from anyone.

What it would change: only a filter on our wallet address, and there is no sign that such a filter exists.

On this chain, the operator does not need addresses: it reacts to the order flow in its own pool. Our recommendation: do not build the
rotation. It costs a deploy and new funding plumbing per rotation, and it hides nothing that is used against us.

## Method and limits

- The bot's buy is a swap whose transaction calls 0x1cbaf24d with c1120e3d (141 wallets). The pull is the first ModifyLiquidity with negative
  liquidity. Every one of the 2,133 pulls was sent by the pool's own launch wallet through 0x1cbaf24d with a0f7978d.
- "Ahead of the bot" uses chain order (block, log index). The sentinel 0xe71a69f4 and buys under 0.00003 ETH are ignored. "Fresh" means nonce
  0 or 1 at the buy.
- Reverted transactions leave no logs. A bot buy that reverted shows as "no bot buy".
- Transactions were read only to launch + 400. The 200 tiny fresh wallets of Oct 10 sold later than that, so their sweeps were not traced.
- The funding trace uses block reads only. The node keeps about 6,000 blocks of state and has no traces, so anything upstream of the
  collectors is unseen.
- Time windows come from the chain. Our on/off times come from HANDOFF 16.5-16.17 and are approximate within a minute or two.

## Files (research/session_oct11/lines/analysis/X/)

| file | what it does |
|---|---|
| `rpc.py` | W's paced client; adds getTransactionCount and getStorageAt |
| `xcommon.py` | shared constants |
| `x01_fetch.py` | fetch with stage caches (`x01_*.json`, `txcache.jsonl` is 82 MB; not committed) |
| `x02_parse.py` | builds `x02_pools.pkl` (33 MB, not committed) and `x02_trades.json` |
| `x03_our_trades.py` | question 1 |
| `x04_classify.py` | buyers ahead of T |
| `x06_groups.py` | buyer groups and their own sells |
| `x10_matched.py` | the same-hours comparison |
| `x11_tables.py` | the report's tables |
| `x12_extra.py` | pull vs first buy, 3.0 trap, wallet counts, bot size |
| `x13_windows.py` | the window table |
| `x14_misc.py` | routers, collectors, the pre-us pulls, decoy first/last, gas |
| `x05_us_checks.py` | transfers, calldata, sampled blocks |
| `x07_funding_live.py` | live state-window funding search |
| `x08_trace_fresh.py` | one fresh wallet's whole life, plus a backward scan for its funding |
| `x09_decoy_chain.py` | every fresh wallet's sweep (`x09_chain.json`) |

Each script has a matching `.out` file.
