# Scoping the V3 crowd line (hand-back ~17:40 UTC Oct 11)

Verdict: do not build the live path tomorrow; run the read-only forward test (analysis/W/w07_forward.py) for 24-48 h first, then build the
router path (a) for a small probe. The per-trade edge holds today but the line slowed (about 90 launches/day vs 149 in the census; none
15:06-17:19).

Mechanics: V3 factory 0x1f7d7550...2efa, PositionManager 0x73991a25...8de0d3, SwapRouter02 0xcaf681a66d020601342297493863e78c959e5cb2, WETH
0x0bd7d308.... Real buys: exactInputSingle 04e45aaf (228 B) with ETH value = amount in (the router wraps), or multicall(deadline, [...])
5ae401dc (420 B). Real sell: multicall [exactInputSingle(token -> WETH, recipient = router), unwrapWETH9], 548 B, 131k gas; the seller's
approve went at the previous nonce two blocks earlier (approve-then-sell at consecutive nonces works on this chain). eth_call on a live pool:
a 0.0058 ETH buy matched v4math to 8e-21 and the sell to the wei; without the approval the sell reverts (STF). Path (a): buy at nonce n,
approve at n+1 right after the buy, sell at n+2 built from the buy's receipt (the exit is >= 50 blocks after the buy), ~317k gas (~$0.016).
Path (b): a V3 relay (~80 lines, the pool's swap callback), presigned sell-everything, no approvals; needs solc, a harness, a review, a deploy.
(a) for the first probe, (b) for production.

Launch recognition from the feed: yes, from calldata alone: 31 of 31 recent launches decoded exactly (pool address by the standard V3 CREATE2,
price, range -887272..launch tick, liquidity from the mint of 1e27 tokens; v3dec.py). ~5% of launches have WETH as token1 (mirror or skip).
Engine: families keyed by launch value today, so C-1 and this line (both value 0) collide: a (to, selector, length) key and a V3 arming step.

Price and exit: buy_out_int, sell_out_int, sqrt_after_buy, apply_buy at fee 100 are exactly V3's math for this shape. Not covered: WETH-second
pools, value-0 WETH buys and dust, sells, take_profit (would sell too early). The exit needs no price copy: sell at the first real buy at or
after ours + 20, capped at launch + 80 (send when the feed shows +77/78); settle from the pool's Swap and Burn logs. The crowd's buys are
value-0 calls through four rotating contracts (3593564c/484 B or a0193551/49f74a5d/452 B; path WETH, fee 100, token; amount at word 9 or 8;
min-out 0 on all 199 fetched), the token off a word boundary: a shape-matching recogniser, not the wave mode's single router.

Risks: one controller (the crowd contracts hold 25 and 8 ETH pooled; C-1's router 84 ETH); if it stops when it sees us a trade costs ~-$0.02
unless the pull moves earlier (only 2 pools in 7 days had an early stranger buy >= 0.003 ETH); the cap carries the edge (today cap 70 +1.2%,
60 +0.35%, 80 +5.2%); no taxes possible (no external calls or time/origin checks in either token template); the top 10% of trades bring 71%
of the profit.

Forward test (0.0058 ETH, entry +2): 09:15-17:15 UTC 29 launches, mean +5.2%, median +0.17%, 26 wins, 0 pulled, $0.75/trade; last 3 h 6
launches, mean +9.2% (one +51.8%), median +0.04%; two more at 17:19/17:25 +0.1% each (the crowd came after the cap). Crowd's first real buy
median +84 (33-505), 0.044 ETH; earliest pull +103. About $65/day at $15 today vs C's $185; at 0.05 ETH the mean was still +5.1%.

Effort: 7-8 h common (decoding, recogniser, exit, settle, tests), (a) +4 h, (b) +6 h. Gate to build: >= 100 launches at >= +4% mean, no pull
before +80, >= 120 launches/day; then ~40 trades with (a) at 0.002-0.006 ETH; (b) to scale. Files: analysis/W/ (DETAIL.md, v3dec.py,
w05_recent.py, w07_forward.py, w08_chain_checks.py).
