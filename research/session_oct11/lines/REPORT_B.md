# Analyst B: v4 pools outside the volume-bot multicall, Oct 11

Scope: 20,512 pools (11,385 outside c873e135|ac9650d8 plus templates 16afd61e, cb79985d, 58d59320, c0b7d400, a98b3b9e, 97c7ba1b). The replay
reproduces the real price paths (median error ~1e-23 per swap, validate.txt). "Core" = a family's most common shape.

## Ranked (q = 0.0058 ETH)
1. C-1 core (c873e135|ac9650d8#cb79985d, ETH, fee 100, ts 1, no hook): 99.7 launches/day (107 in the last 24 h); launch price and liquidity the
   same in 98%; operator's buy in 82%, offset 73/119/205, median 0.14 ETH, +2.8%; 99% through router 0xd6d35b56 (zero-value) from 83 wallets
   each in a median of 59 pools. Follow, 60-block hold: n 573, mean +16.8%, median +10.0%, win 79%, worst -100%, pulled before sell 2.8%;
   $205/day ($70 at q 0.002); every day between +10% and +27%; the last 24 h $134. Alternative: fire at +71 and sell into the router's buy:
   +7.4% mean. Engine: key the family by length and fee instead of value; decode the zero-value router call as the trigger (decode_launch read
   453 of 453 launches). Top risk: pools pulled within 100 blocks of an outsider buy at twice the expected rate (8 of 37 vs 3.9) [the verifier
   found 4 of those 8 "outsiders" are the bot's own router wallets and 2 in pools the bot never bought].
2. a98b3b9e hooked core (ETH, fee 3000, ts 60, a new hook per pool): 16.7/day irregular; multicall 2,020 bytes value 0; operator's buy in 99%
   at 46/52/90, exactly 0.05 ETH in 87%, wallet 0x9e8f558b through zero-value router 0x75379d5d; then a scheduled pump: x1.01 at +40, x1.73 at
   +62, x2.34 at +100; 3% pulled. Follow 60: n 116, mean +83%, median +71%, win 97%, worst -1%, 0% pulled, $206/day; every day +67..+178%.
   Engine: small change plus hook support. Top risk: a hook tax or a blocked sell is invisible; all 11,989 sells went through the Universal
   Router; reaction to outsiders untested.
3. C-2's hooked sibling (template 4e451d1a via PoolManager.initialize, 196 bytes): 12.7/day; liquidity minted ~42 blocks later; crowd buys from
   111/116/188, 12.3 ETH within 60 blocks; follow 60: n 82, mean +435%, win 90%. Looks like a honeypot: all 47,505 sells through the Universal
   Router, and our relay's simulated sell reverted on 3 of 3 hooked pools in the first census. Do not trade until a sell simulation passes.
4. 58d59320 via 0xeb7c0347 (WETH, dynamic fee, one shared hook): 66.6/day, never pulled (0 of 486); front (buy +2, sell into the first real
   buy, at most +413): n 466, mean +8.9%, median -0.1%, win 24%, $88/day, positive every day. A lottery; WETH buys carry no ETH value.

## Rejected
Operator A 42544ef5 (553): 24 of our 43 live follow trades were pulled 5-16 blocks after our buy; of 491 other pools none was pulled within 22
blocks of the first real buy. Operator A 2793923d (124): no launch after Oct 8. C-2 hookless core (684): 5 of 5 early-outsider pools pulled
within 166 blocks vs 0.5 expected; follow 60 +4.2%. f07d1c53 (102): all within 75 minutes on Oct 10. Template 65daaea0 / 0x0000ffff (210) and
contract-creation launches (105): the buy inside the launch tx lifts the price +84% / +453%, then nobody buys; follow -1.1% / -0.6%. Too few
first real buys: 16afd61e 8,101 launches 2.7%; 7fde822e launchpads 1,461 0.3%; 58d59320 via EntryPoint 1,396 0.5%; cd37624e 564 0%;
724433a2 438 0.9%; 2dfcf583 340 0.9% (nothing since Oct 6); c3cd7006 285 9%. 99e0b5e8 (268): first buy at +1; c0b7d400 via initializePool
(132): -1%; d4e7eae4 (116): ~$9/day; 51faa3f1 (86): median -0.1%. 122 of the 163 families with >= 10 launches have a first real buy in under
5% of launches.

## Limits
Pool math only (no hooks); no sell simulation; reaction to our own trade tested only for operator A; crowd buys are zero-value router calls
in every cached transaction; events cover 3,000 blocks; 245 C-1 launch inputs and all f07d1c53 inputs not cached; one a98b3b9e token so coarse
that a 0.002 ETH buy gives -100%. Scripts s01-s17, replay.py, common.py and outputs in analysis/B/.
