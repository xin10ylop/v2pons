# W: what it would take to trade analyst C's V3 crowd line, and whether it is worth it (Oct 11, 17:30 UTC)

Read-only: no edits to the repository, no git changes. RPC: 158 POSTs / 924 items to the public node, one at a time with at least 0.5 s
between them and a back-off on 429. Scripts and outputs are in this directory. `rpc.py` is the polite client, `v3dec.py` the calldata
decoder an engine would need, and `wcommon.py` turns V3 logs into analyst C's compact rows.

## Addresses (all checked on chain)
- V3 factory `0x1f7d7550b1b028f7571e69a784071f0205fd2efa`. The PositionManager (NPM) `0x73991a25c818bf1f1128deaab1492d45638de0d3` uses code hash
  `0a493d1a…`. SwapRouter02 is `0xcaf681a66d020601342297493863e78c959e5cb2`. WETH is `0x0bd7d308f8e1639fab988df18a8011f41eacad73`. Both the router and the NPM
  return this factory and this WETH from `factory()`/`WETH9()` (w08).
- The pool address is CREATE2 with the standard V3 init hash `e34f199b…8b54`. It matched the census pools and 31 of 31 recent launches.

## 1. Mechanics
Real router transactions (w04_decode_shapes.out):
- Buy `0xb8a66d42…`: `exactInputSingle` `04e45aaf`, 228 B, tuple (WETH, token, 100, recipient, amountIn, minOut, 0), msg.value = amountIn. The router
  wraps the ETH (a WETH Transfer from 0x0 to the router) and pays the pool. Gas used 139,831.
- Buy with a deadline `0x2da94d15…`: `multicall(uint256 deadline, bytes[])` `5ae401dc` wrapping the same call, 420 B, with value. Gas used 149,114. No
  `wrapETH` or `refundETH` is needed when value == amountIn.
- Sell `0x0d346c25…`: `multicall` `ac9650d8`, 548 B, made of [exactInputSingle(token, WETH, 100, recipient 0x…02 = the router, amountIn, minOut, 0),
  `unwrapWETH9(minOut, seller)` `49404b7c`]. Gas used 130,704. The seller is a bot at nonce 27,611. Its nonce 27,610 was `approve(router)` on the
  same token, 2 blocks earlier. A second sell by the same bot showed the same pattern, so approve then sell at consecutive nonces is already
  done on this chain (w16).
- eth_call tests on a live line pool (w08):
  - Buy: 0.0058 ETH through the router returned 113,298,261,232,140,161,466,122 tokens. v4math's single-range prediction differs from that by
    8e-21 relative.
  - Sell: selling those tokens with the allowance set by state override returned exactly `sell_out_int`. Without the allowance the sell reverts
    with `STF`, so the approve is required.
  - The round trip predicted after our own buy is −0.020% (two fees of 100 ppm).
- (a) Router path, three transactions:
  - Nonce n, buy (value = stake).
  - Nonce n+1, `approve(router, max)`, sent right after the buy. It is about 46k gas.
  - Nonce n+2, sell. The sell must name an exact amountIn, so it is built from the buy's receipt rather than presigned. That is fine here
    because the exit comes at least 50 blocks after the buy.
  - The approve could go in the same block as the sell. Nitro sequences one sender's consecutive nonces in order, the same thing the engine
    relies on for its presigned sell. Sending it early is better, and the engine should check the approve's receipt before sending the sell.
  - Gas is about 317k in all, roughly $0.016 at 0.02 gwei. Today's two-transaction trade costs about $0.015.
- (b) FlipRelayV3, about 80 lines:
  - `pool.swap` with `uniswapV3SwapCallback`. The pool comes from CREATE2 and is held in transient storage, and the callback checks it.
  - WETH is wrapped and unwrapped inside the contract. The sell covers the whole balance, so it can be presigned at n+1 as today. There is no
    approval, and gas is lower.
  - It needs solc (py-solc-x is not in this container), an eth_call harness like relay_sim.py, a review and a deploy from the box.
- For a first probe, (a) is faster and adds no new on-chain code. (b) is the path for production.

## 2. Recognising launches in the feed (v3dec.py, w06)
- The launch is a value-0 `multicall` `ac9650d8` of 836 B to the NPM, containing exactly:
  - `createAndInitializePoolIfNecessary` `13ead562`(token0, token1, fee, sqrtP), 132 B;
  - `mint` `88316456` (MintParams: tickLower −887272, tickUpper = launch tick, amount0 0, amount1 1e27, recipient = the launch wallet), 356 B;
  - `refundETH` `12210e8a`.
- Decoded from calldata alone and checked against the receipts' Initialize and Mint: 31 of 31 exact for pool, sqrtP, range and L.
  - L is LiquidityAmounts(amount1) computed with an exact TickMath port.
  - The launch sqrtP is exactly sqrtAt(hi), so the range serves a buy from the top tick inclusive. This is C-1's arm_front rule.
- Three examples:
  - `0x2b412e07…` (85718462), `0x628da404…` (85721479) and `0xfcb91764…` (85722949): hi 193379, L 63,246,764,568,802,612,649,417.
  - Over 8 h there were 4 (hi, L) variants, so pin the shape rather than the price.
- 5% of the census launches have WETH as token1 (`qs` 1). Mirror the math or skip them; skipping costs $9/day.
- The engine today: `ingest_tx` only treats `to == POSITION_MANAGER` (v4), and families are keyed by launch value, so C-1 and this line
  (both value 0) would collide. Needed:
  - a family key of (to, selector, length);
  - `decode_launch_v3`;
  - an arming step that keeps the pool address instead of the pool id.

## 3. Price and exit
- What works: `v4math.buy_out_int`, `sell_out_int`, `sqrt_after_buy` and `apply_buy` with fee 100. These are V3 qs-0 math; the swapper pays
  exactly the tier, with no protocol add-on.
- What does not:
  - qs 1 pools.
  - Value-0 WETH router buys and the 0x570759db dust at +1, which are invisible to the price copy.
  - The `a0193551` crowd call through 0x80114879: it swaps 99% of its calldata amount (72 of 72) and keeps 1%.
  - Sells: the engine never applies them, and the crowd also sells (6,248 swaps through the UR in 8 h in these pools).
  - `take_profit`: it would sell into the first crowd buy. Waiting 10 blocks after that buy instead of 20 costs 12% of the profit.
  - `round_trip_gas_wei` assumes 250k gas.
- The rule needs no price copy. It sells at min(first real buy at or after ours + 20, launch + 80), and settle reads receipts: the pool's Swap
  log and Burn logs with amount > 0 on the pool address.
- Trigger: crowd buys are value-0 calls, which `ingest_tx` drops unless `to` is in WAVE_ROUTERS, and the wave mode handles one router per
  family. In 199 of 199 fetched crowd buys:
  - the call shape is (`3593564c`, 484 B) or (`a0193551`/`49f74a5d`, 452 B);
  - amountIn is at word 9 or 8, and min-out at the next word is 0;
  - the path is WETH‖000064‖token, not word-aligned;
  - recipient = the sender, gas limit 500,000.
- The crowd also sells through the same shape, so the path direction is the buy flag.
- The crowd contracts rotate, with one active at a time: 0x80114879 09:15–09:56, 0x71a7629f 10:26–11:43, 0x84021dc2 13:43, 0xd26c8cfc 14:30–17:25.
  They come in two code sizes, and every one has its own code hash. So the recogniser must match the call shape, not addresses.
- In the census, 855 of 906 first real buys are crowd-shaped. A crowd-only trigger gives +8.41% against +8.49% when any buy triggers (w10).

## 4. Risks
- The crowd is one controller:
  - Its ETH is pooled in the contracts: 0xd26c8cfc holds 25.1 ETH, 0xfc7241d4 8.0 ETH and C-1's router 83.7 ETH (w13). The calls are signed by
    EOAs at nonces around 2,000.
  - The contract in use changes every hour or so.
- If it stops when it sees us, our sell at +80 returns −0.02% minus gas, about −$0.02 a trade. The real loss would come from an earlier pull.
- Blind spot: in 7 days only 2 pools had a stranger buy of 0.003 ETH or more in blocks 0–10. Strangers of 0.001 ETH or more (318 pools)
  changed neither the crowd (0.42 against 0.37 by +80) nor the pulls (18% against 14% by +150) (w12).
- The cap carries the edge:
  - Census: cap 70 $135/day, cap 60 $96/day.
  - Today: cap 70 +1.2%, cap 60 +0.35%.
  - The earliest pull with no crowd was at +83 (census); today the earliest pull was at +103. Send the sell when the feed shows +77 or +78,
    and halt on a pull before our sell.
- Taxes: none are possible. 27 of 29 tokens use the 1,764-byte census template; 2 are a 5,048-byte OZ ERC20. Neither has CALL, ORIGIN,
  TIMESTAMP or NUMBER; the hits sit in revert strings (w09).
- Concentration: the top 10% of trades bring 71% of the profit.

## 5. Forward test (w07; my pipeline equals the census replay on 23 of 23 overlapping pools, w15)

| window | launches | mean | median | win | pulled before sell | $/trade at $15 |
|---|---|---|---|---|---|---|
| 09:15–17:15 UTC | 29 | +5.19% | +0.17% | 26/29 | 0 | $0.75 |
| last 3 h | 6 | +9.15% (one +51.8%) | +0.04% | 4/6 | 0 | $1.34 |
| 17:19, 17:25 | 2 | +0.09%, +0.16% (crowd at +124, +154) | | | | |

- First real buy: median +84 (range 33–505), median size 0.044 ETH, all from crowd contracts except 2 (0xf0b7eaaf). Pulls: earliest +103,
  median about +1,040.
- Rate: about 90 a day against 149 in the census. There were none 12:00–13:10 or 15:06–17:19.
- At 0.05 ETH the mean was still +5.1%: the crowd's min-out is 0, so the stake can grow.

## 6. Effort
- Common to both paths, about 7–8 h:
  - decode and arm: 2 h;
  - crowd recogniser: 1 h;
  - exit rule: 1 h;
  - V3 settle and pull check: 1 h;
  - tests: 2–3 h, using a real V3 launch and crowd transactions in L2 frames, the exit schedule and settle on real receipts.
- (a) adds 4 h: the three-transaction nonce flow, the sell from the receipt, the approve check and a wallet-funded stake.
- (b) adds 6 h: the contract, an eth_call harness, a review, the deploy and the transaction builders.
