# Analyst A: PositionManager multicall launches without the volume bot (lc:c873e135|ac9650d8), Oct 11

Scope: 21,018 pools minus 8,080 vbot pools = 12,938 pools from 2,169 wallets. 6,574 launch with value 0, 4,921 are USDG, 4,150 are batch
launches of 60-70 pools per tx. Only 1,569 are 1,444-byte ETH hook-free launches with value > 0, spread over 634 different values. The replay
reproduces every swap's price exactly before any pull for C-1, the odd-wei line and 564f; unreliable on the hooked a98b pools.

## Ranked
1. C-1, ETH (known_fp C-1): a FOLLOW line. Shape: value 0, 2,276-byte multicall (adds permitBatch), fee 100 / tick spacing 1, ETH, no hook;
   sqrt_p0 and mint L the same in 686 of 698 pools. 99.7 launches/day (72 45 97 117 131 129 107), 698 fresh wallets (nonce 2-3). The buyer:
   router 0xd6d35b56 (selector e6cb474f, 484 bytes) in 567/573 pools, 83 wallets, 563 of 573 buyers also bought in 3+ other pools; offset
   +73/+119/+205 (p10/50/90), median 0.14 ETH, zero-value calls; calldata word 2 = the amount swapped (3,746 of 3,758), word 3 = 0 (minimum
   output). Price +2.8% from the first buy, +6.5% after its 2-block burst, +27% median by 62 blocks later. The bot never comes in 17.9% of
   pools (124 of those 125 pulled, median +191). Pulls: 64% of pools, never before the bot's first buy (p10 83 blocks after); no reaction to
   outsiders: 0/32 vs baseline 21/661. Best rule: buy 2 blocks after the bot's first buy, sell 60 later: n 559 (80% of launches), mean +16.5%,
   median +10.0%, win 79%, worst -100%, 3.0% pulled before the sell; $196/day at $15, $67 at $5; by day +15.6/+27.3/+15.4/+16.5/+16.8/+17.8/
   +10.2% (last 24 h). Hold 40: +12.8% with 1.1% pulled; hold 100: +22.5% with 7.7% pulled. Front on C-1 does not work (+0.6% with a deadline
   for the 18% without a bot). Engine: small change (value 0 and 2,276 bytes do not key the front lookup; the trigger carries no ETH value;
   hold 60; trigger window >= 300 blocks). Top risk: the last day is the weakest.
2. C-1, WETH quote (27.1/day, same bot): n 154, mean +17.6%, win 79%, 3.2% pulled, $58/day; one negative day; needs WETH trading.
3. a98b, hooked (19.9/day; value 0, 2,020 bytes, fee 3000/60; a hook per pool taking a cut): one wallet buys 0.05 ETH at +46/+52/+94 through
   0x75379d5d then keeps buying; 2.6% pulled; follow replays +81% mean but the hook's cut is invisible: an upper bound; new trading path.
4. 564f, hooked WETH (17.1/day): first buy +4 through fixed routers, 0.075 ETH, +2.1%; front +3.4% ($8.6/day); hold to +300 +13.9% ($35.6/day).

## Rejected
Odd-wei ~1.6-2 ETH line (1,444 bytes, fee 100, 17/day over 18 values): no operator, first buys from 95 wallets at +291, +1.2%, $3/day. Values
9.333 and 40 ETH: real buys in 0.9% / 0%. 33.33, 4, 10, round 2 ETH: 2-3 non-fresh wallets, tiny. The vbot's token templates at other values:
037449b1 real buys in 4 of 142, aff2095f 0 of 23. The vbot's router 0x1cbaf24d appears in 0 of the 12,938 pools. 0.0012177 ETH (375 pools)
1.2% with real buys; 4e-05 ETH 0%; batch launches 0%; value-0 1,444-byte pools 4%; USDG 2.2%.

## Limits
Hook cuts invisible in events; only 6 words of each swap's calldata cached; wallets known only for each pool's first 12 swaps and first real
buy; the replay assumes nobody reacts to our trades; fixed $2,570/ETH. Scripts and outputs: analysis/A/ (follow_grid.py gives the headline).
