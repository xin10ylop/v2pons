# Analyst A: PositionManager multicall launches (lc `c873e135…|ac9650d8`) without the volume bot

Scope (`extract.py`, `spectrum.py`): 21,018 pools in the launcher family (quote pairs excluded). Removed 8,080 vbot pools (`known_fp` vbot-v2.433/v3.0/v5.0, or a launch value of exactly 2.4333285, 3.0 or 5.0 ETH). That leaves **12,938 pools from 2,169 launch wallets**. The brief's "~7,900 wallets" counted the vbot's fresh wallets. Of these 12,938: 6,574 launched with value 0, 4,921 are USDG, and 4,150 are batch launches (0.000735, 0.00063 or 0.000525 ETH, 54,500/46,788-byte calldata, 60-70 pools per tx). 1,728 use the 1,444-byte shape, and 1,569 of those are ETH, hook-free, with value > 0, spread over 634 distinct values.
Replay (`replay.py`): integer v4 math as in `src/v4math.py`, for both currency orders. Re-simulating every swap without our trade reproduces every event's sqrtPrice to within 1e-6 before the first pull in C-1, odd2 and 564f, all C-1 pools included (`checks.py`). Day 6 = the last 24 h (Oct 10 13:52 to Oct 11 13:52). $/day = mean $ per trade x launches/day x tradable share, at $15 (q = 0.0058) unless noted.

## 1. Ranked candidates

### #1 C-1 line, ETH: follow its buyer bot (small engine change)
- **Shape**: POSM multicall, 2,276 bytes (initializePool + permitBatch `002a3e3a` + modifyLiquidities), **msg.value 0**, fee 100 / tick spacing 1, ETH, no hook. sqrt_p0 792280926924313289846529216293289 and mint L 100000088127620690885293 in 686 of 698 pools (6 variants overall). Single position [tick0-1,071,488, tick0]. Census `known_fp` C-1 on all 698.
- **Size**: 698 launches, 99.7/day (per day 72 45 97 117 131 129 107), from 698 distinct fresh wallets (launch nonce 2-3).
- **The buyer ("operator")**: the first real buy goes through the contract `0xd6d35b56…` (selector e6cb474f, 484 bytes) in 567/573 pools. 83 distinct EOAs, and 563/573 of these wallets bought in >= 3 pools.
  - Offset p10/50/90: +73/+119/+205. Median size 0.14 ETH.
  - Missing in 125/698 (17.9%) of pools. 124 of those 125 are pulled, at +93/+191/+358.
  - The router's txs carry **no ETH value**. In 3,746/3,758 of them, calldata word 2 equals the swap's ETH amount, and word 3 is 0 in 3,758/3,758 (probably min-out = 0, so our buy cannot make theirs revert). Our q ahead cuts their output by 0.115%.
  - Price impact: the first buy moves the price +2.8% median. The burst (its block and the next) gives +6.2/+6.5%, and the price is +27% (median) by frb+62. A median of 7 buys and 0.62 ETH come in the 62 blocks after it (`c1_wave.py`).
- **Pulls**: 64% of pools are pulled, at +146/+349/+1974, by the launch wallet through POSM `dd46508f`. None comes before the first real buy; pull minus frb p10 is 83. Reaction to outsiders: 0/32 against a baseline of 21/661 (nf). Pools with an outsider buy after the frb: 0/146 were pulled by frb+62, against 22/582 without one (`c1_reaction.py`, ETH+WETH).
- **Best rule: follow** (trigger = the first buy via 0xd6d35b56; a rule of "first buy >= 0.02 ETH" gives the same), buy at trigger+2, sell at +60 (`follow_grid.py`):
  - **n 559 (80% of launches), mean +16.5%, median +10.0%, win 79%, worst -100%, pulled before sell 3.0%, $2.45/trade, $196/day.** At q = 0.002: +16.2%, $67/day.
  - Per day: +15.6 / +27.3 / +15.4 / +16.5 / +16.8 / +17.8 / **+10.2% (last 24 h, n 85, pulled 3.5%)**.
  - Hold 40: +12.8%, pulled 1.1%. Hold 100: +22.5%, pulled 7.7%. Take-profit exits do worse, because they cut the wave short.
- **Front on C-1 (rejected)**: buying at +2 and selling into the bot's buy makes +13.3% (98% win), but only on the 82% of pools the bot comes to. With a deadline to cover the rest (a+206) it drops to +0.55%, with 9.5% pulled and days 2-3 negative. The best of the deadline/take-profit grid is +5%, with 7% pulled and days 2/3/5 near 0 (`tp_grid.out`). Nothing seen by +40 predicts whether the bot will come (`c1_signal.py`).
- **Engine support: small engine change.**
  - Front cannot key it: `value_wei` must be > 0, and the calldata is not 1,444 bytes.
  - Follow needs three things: POSM in LAUNCHERS with FEE_MIN/MAX_PPM = 100; a trigger that reads the bot's buy (its tx value is 0, so `on_buy` sees nothing; decode word 2, or key on to == 0xd6d35b56); and settings HOLD_BLOCKS 60, TRIGGER_MAX_BLOCKS >= 300, MAX_TRADES_PER_DAY ~80.
- **Top risk**: the last 24 h is the weakest day. The operator pulls 64% of pools (p10 is 83 blocks after the bot), so a longer hold or a slower bot turns into -100%s. The bot could also change its router.

### #2 C-1 line, WETH quote (same bot)
- **Shape and size**: same shape (170 of 190 pools share the same sqrt/L), 27.1/day.
- **Rule** (follow d2/H60): n 154, mean +17.6%, median +10.4%, win 79%, pulled 3.2%, $58/day.
- **Per day**: +7.8 / +18.9 / +22.7 / +28.6 / +24.2 / **-6.4** / +13.0.
- **Engine support**: the #1 changes plus WETH trading.

### #3 a98b line (hooked; new trading path; replay is an upper bound)
- **Shape**: value 0, 2,020 bytes, fee 3000/60, ETH. Each pool has its own hook (117 distinct) with BEFORE_SWAP_RETURNS_DELTA and AFTER_SWAP_RETURNS_DELTA set.
- **Size**: 139 launches, 19.9/day (34 34 8 10 9 34 10).
- **Buyer**: one EOA, `0x9e8f558b`, through `0x75379d5d` (3593564c, 1,540 bytes). It buys a fixed 0.05 ETH at +46/+52/+94 (price +1.24%), then keeps buying 0.2-0.3 ETH. Pools see about 200 buys and 80 sells each; 2.6% are pulled.
- **Replay**: follow d2/H60 gives +81% mean, 97% win, every day positive. But the hook's take is invisible in the Swap events, so the real figure is lower by an unknown amount.

### #4 564f line (hooked WETH)
- **Shape**: value 0, 2,276 bytes, fee 100/1, WETH, with an AFTER_SWAP_RETURNS_DELTA hook per pool.
- **Size**: 17.1/day.
- **Buyer**: the first real buy comes at +4/+4/+131, through fixed UR-like contracts (0x80e49ed1 / 0x7feb3ecb / 0xa0332fd6, 836 bytes). Median 0.075 ETH, price +2.1%. No pulls.
- **Replay**: front a2 selling at frb+1 gives +3.4% ($8.6/day); front a2 b300 gives +13.9% ($35.6/day), both stable by day. The hook is invisible to the replay, and the pool needs a new trading path.

## 2. Lines examined and rejected
- **"Odd-wei ~1.6-2 ETH" line** (1,444 bytes, fee 100/1 in 114 of 121 pools, fresh wallets, 17.3/day in total, spread over 18 exact values; sqrt/L is constant within 17 of them). It has the shape we trade today, but there is no operator: the first real buy comes at +86/+291/+539 from 95 different wallets in 116 pools, almost all through the Universal Router. Front with a deadline: +1.2%, $3/day. Follow: +0.05%.
- **Values the engine notes as other vbot lines**: 9.333 ETH (111), 40 ETH (110), 33.33 ETH (16), 4 ETH (12), 10 ETH (6), round 2 ETH (32). Each comes from 2-3 non-fresh wallets, with fee ~1% at odd ppm. Real buys in 0.9% / 0% / 0% / 17% / 50% / 28% of pools, never through 0x1cbaf24d. 9.333 and 40 ETH are 39% / 51% pulled, at +1133 / +1156.
- **The vbot's token skeletons at other values**: 037449b1 has 142 non-vbot pools (mostly value 0 / USDG; 4 ETH x5, 16 x2, 10 x1), with real buys in 4/142. aff2095f has 23 non-vbot pools, with real buys in 0.
- **The vbot's router 0x1cbaf24d**: appears in 0 of 12,938 non-vbot pools.
- **0.0012177 ETH** (375 pools, 2 wallets with nonce ~63k): real buys in 1.2% / 0%. **4e-05 ETH** (161 pools): 0. **The batch values** (4,150 pools): 0.
- **Value-0 1,444-byte ETH pools** (fee 1%: 51; fee 0.3%: 25): real buys in 4% / 4%.
- **USDG/USDG2** (5,151 pools): 2.2% have a real buy, from 98 different wallets. **The 124 repeat-launch wallets** (9,520 pools): none has real buys in 20% or more.

## 3. Data limits
- **Hooked pools (#3, #4)**: the hook's swap deltas do not appear in the events, so their replays overstate returns and cannot see whether selling is blocked.
- **Router calldata**: only 6 words of each swap tx's calldata are cached. That C-1 word 3 is the min-out is inferred from the layout, not from an ABI, and I could not confirm the token address is in the router's calldata.
- **Who bought**: EOAs and routers are known only for the first 12 swaps and the first real buy. Later wave buys are counted from the events, without their senders.
- **Replay assumptions**: others' swaps are re-applied unchanged (no reverts, no reaction to us). A pull at or before the sell counts as -100%.
- **Window**: 7 days, with launch times interpolated to about 1 s. ETH is fixed at $2,570.

## Detail tables (every group with >= 15 launches; `groups.py`, `groups_value.py`, `tables.py`)
### Exact launch shape (value wei, calldata len, fee, tick spacing, sqrt_p0, mint L, quote, hook-free): every group with >= 15 launches

| key | n | per day d0..d6 | wallets | nonce p10/50/90 | fresh (nonce<=3) | any buy | frb | frb off p10/50/90 | frb ETH p10/50/90 | frb top fingerprint (n) | frb EOAs | frb repeat (>=3 pools) / also in lc fam | pulled | pull off p10/50/90 | pull<frb | pull via | early-outsider reaction nf | baseline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 wei, 2276 B, 100/1, sqrt 79228092.., L 10000008.., ETH, no hook | 686 | 70 39 96 117 130 127 107 | 686 | 2/2/3 | 0.999 | 1.0 | 0.818 | 74/118/204 | 0.0297/0.14/0.32 | 0xd6d35b56:e6cb474f:484 (555) | 81 | 552 / 560 | 0.646 | 146/349/1949.4 | 0 | 0x58daec31:dd46508f (443) | 0/29 | 20/652 |
| 0 wei, 2276 B, 100/1, sqrt 79228092.., L 10000008.., WETH, no hook | 171 | 31 10 37 26 35 19 13 | 171 | 2/2/2 | 1.0 | 1.0 | 0.807 | 68/109.5/238 | 0.0292/0.1487/0.5066 | 0xd6d35b56:e6cb474f:484 (136) | 43 | 133 / 135 | 0.719 | 129.4/391/1903.2 | 0 | 0x58daec31:dd46508f (123) | 0/21 | 6/150 |
| 0 wei, 2020 B, 3000/60, sqrt 88457784.., L 89797578.., ETH, HOOK | 87 | 33 29 8 7 0 1 9 | 87 | 3/3/3 | 0.954 | 1.0 | 1.0 | 46/53/81 | 0.05/0.05/0.05 | 0x75379d5d:3593564c:1540 (87) | 1 | 87 / 87 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/85 |
| 0 wei, 2276 B, 100/1, sqrt 79228092.., L 10000008.., WETH, HOOK | 71 | 2 10 9 12 24 11 3 | 71 | 5/6/6 | 0.0 | 1.0 | 1.0 | 4/4/73 | 0.0109/0.0993/0.3 | 0x80e49ed1:3593564c:836 (47) | 12 | 66 / 68 | 0.028 | 1281.9/1601.5/1921.1 | 0 | 0x58daec31:dd46508f (2) | 0/13 | 0/58 |
| 0 wei, 2276 B, 10000/200, sqrt 25135685.., L 31520191.., WETH, no hook | 38 | 11 1 11 1 3 6 5 | 38 | 5/5/6 | 0.0 | 0.0 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/0 |
| 1999999999999997576 wei, 1444 B, 100/1, sqrt 17715955.., L 44721359.., ETH, no hook | 32 | 0 16 13 2 0 0 1 | 32 | 3/3/4 | 0.625 | 1.0 | 1.0 | 63.2/273/572.1 | 0.005/0.028/0.077 | 0x88767899:3593564c:1284 (22) | 23 | 10 / 10 | 0.781 | 251.8/1589/2601.4 | 0 | 0x58daec31:dd46508f (25) | 0/24 | 0/8 |
| 1999999999999992334 wei, 1444 B, 100/1, sqrt 56022770.., L 14142135.., ETH, no hook | 32 | 0 5 2 5 0 3 17 | 29 | 3/3/5.8 | 0.781 | 1.0 | 0.906 | 194.4/319/578.8 | 0.0051/0.036/0.0646 | 0x88767899:3593564c:1284 (25) | 27 | 3 / 3 | 0.688 | 389.4/1609/2866.6 | 0 | 0x58daec31:dd46508f (22) | 0/27 | 0/4 |
| 0 wei, 2020 B, 3000/60, sqrt 10215775.., L 77755182.., ETH, HOOK | 25 | 0 0 0 0 1 24 0 | 25 | 3/3/4 | 0.84 | 0.96 | 0.96 | 46/48/183.8 | 0.0234/0.05/2.5 | 0x75379d5d:3593564c:1540 (24) | 9 | 22 / 22 | 0.08 | 1144.3/1485.5/1826.7 | 0 | 0x58daec31:dd46508f (2) | 0/0 | 0/21 |
| 0 wei, 2276 B, 100/1, sqrt 14457535.., L 54745799.., WETH, HOOK | 22 | 9 1 8 0 1 1 2 | 22 | 6/6/7 | 0.0 | 1.0 | 1.0 | 4/4/171 | 0.0105/0.0495/0.0995 | 0xa0332fd6:3593564c:836 (6) | 12 | 19 / 21 | 0.0 | -/-/- | 0 | - (0) | 0/19 | 0/3 |
| 0 wei, 2276 B, 100/1, sqrt 14464765.., L 54773207.., WETH, no hook | 16 | 2 2 1 11 0 0 0 | 16 | 2/2/3 | 1.0 | 1.0 | 1.0 | 72/111/239 | 0.0375/0.094/0.2243 | 0xfc7241d4:3593564c:836 (5) | 11 | 16 / 16 | 0.625 | 179.4/284/1088.4 | 0 | 0x58daec31:dd46508f (10) | 0/3 | 0/13 |

### Engine view: (value wei, calldata len, fee, tick spacing, quote, hook-free), any price/liquidity: every group with >= 15 launches and a first-real-buy share >= 5% (the other groups are listed after)

| key (distinct sqrt,L) | n | per day d0..d6 | wallets | nonce p10/50/90 | fresh (nonce<=3) | any buy | frb | frb off p10/50/90 | frb ETH p10/50/90 | frb top fingerprint (n) | frb EOAs | frb repeat (>=3 pools) / also in lc fam | pulled | pull off p10/50/90 | pull<frb | pull via | early-outsider reaction nf | baseline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 wei, 2276 B, 100/1, ETH, no hook (6) | 698 | 72 45 97 117 131 129 107 | 698 | 2/2/3 | 0.999 | 1.0 | 0.821 | 73.2/119/204.8 | 0.0297/0.14/0.32 | 0xd6d35b56:e6cb474f:484 (567) | 83 | 563 / 571 | 0.64 | 146/349/1974.2 | 0 | 0x58daec31:dd46508f (447) | 0/32 | 21/661 |
| 0 wei, 2276 B, 100/1, WETH, no hook (15) | 227 | 37 20 45 46 39 22 18 | 227 | 2/2/3 | 1.0 | 1.0 | 0.841 | 67/110/231 | 0.028/0.137/0.495 | 0xd6d35b56:e6cb474f:484 (154) | 68 | 184 / 181 | 0.714 | 144.7/413.5/1942.4 | 0 | 0x58daec31:dd46508f (162) | 1/32 | 7/195 |
| 0 wei, 2276 B, 100/1, WETH, HOOK (13) | 119 | 13 12 22 14 29 17 12 | 119 | 5/6/7 | 0.0 | 1.0 | 1.0 | 4/4/123.4 | 0.0142/0.075/0.297 | 0x80e49ed1:3593564c:836 (50) | 36 | 102 / 106 | 0.034 | 1032.6/1361/1856.7 | 0 | 0x58daec31:dd46508f (4) | 0/49 | 0/70 |
| 0 wei, 2020 B, 3000/60, ETH, HOOK (7) | 117 | 33 29 8 9 3 26 9 | 116 | 3/3/3 | 0.923 | 0.991 | 0.991 | 46/52/89.5 | 0.05/0.05/0.15 | 0x75379d5d:3593564c:1540 (116) | 10 | 113 / 113 | 0.026 | 948.6/1059/1741.4 | 0 | 0x58daec31:dd46508f (3) | 0/0 | 0/110 |
| 1999999999999997576 wei, 1444 B, 100/1, ETH, no hook (1) | 32 | 0 16 13 2 0 0 1 | 32 | 3/3/4 | 0.625 | 1.0 | 1.0 | 63.2/273/572.1 | 0.005/0.028/0.077 | 0x88767899:3593564c:1284 (22) | 23 | 10 / 10 | 0.781 | 251.8/1589/2601.4 | 0 | 0x58daec31:dd46508f (25) | 0/24 | 0/8 |
| 1999999999999992334 wei, 1444 B, 100/1, ETH, no hook (1) | 32 | 0 5 2 5 0 3 17 | 29 | 3/3/5.8 | 0.781 | 1.0 | 0.906 | 194.4/319/578.8 | 0.0051/0.036/0.0646 | 0x88767899:3593564c:1284 (25) | 27 | 3 / 3 | 0.688 | 389.4/1609/2866.6 | 0 | 0x58daec31:dd46508f (22) | 0/27 | 0/4 |
| 0 wei, 1892 B, 150000/1500, USDG, no hook (24) | 24 | 4 6 2 2 1 5 4 | 16 | 15.3/612/7716.3 | 0.0 | 0.25 | 0.083 | 285.7/600.5/915.3 | 0.0054/0.0059/0.0065 | 0xccc88a9d:0a2b8f36:6372 (1) | 2 | 2 / 2 | 0.083 | 1082.7/1185.5/1288.3 | 0 | 0x58daec31:dd46508f (2) | 0/4 | 0/2 |
| 0 wei, 1892 B, 50000/500, USDG, no hook (20) | 20 | 3 5 1 2 4 4 1 | 19 | 127.2/733/6214.4 | 0.0 | 0.35 | 0.2 | 237.4/595.5/1188.8 | 0.0061/0.0129/0.0201 | 0x6131b5fa:e21fd0e9:7076 (1) | 4 | 1 / 2 | 0.25 | 492.4/1485/2209.2 | 0 | 0x58daec31:dd46508f (4) | 0/4 | 0/2 |
| 0 wei, 1892 B, 9000/90, USDG, no hook (19) | 19 | 0 6 2 5 2 2 2 | 14 | 22/314/6002.4 | 0.0 | 0.211 | 0.105 | 198.1/870.5/1542.9 | 0.0354/0.0949/0.1545 | 0x204faca1:3593564c:3866 (1) | 2 | 0 / 0 | 0.053 | 1925/1925/1925 | 0 | 0x58daec31:b88d4fde (1) | 0/2 | 0/2 |
| 0 wei, 1316 B, 770000/7700, USDG, no hook (16) | 16 | 6 3 1 1 1 2 2 | 14 | 16.5/613/3865 | 0.0 | 0.125 | 0.062 | 2978/2978/2978 | 0.082/0.082/0.082 | 0xfd03abca:260595cf:6276 (1) | 1 | 1 / 1 | 0.062 | 457/457/457 | 0 | 0x58daec31:dd46508f (1) | 0/0 | 0/2 |
| 0 wei, 1316 B, 300000/3000, USDG, no hook (15) | 15 | 1 1 4 1 4 3 1 | 13 | 206.4/1605/5844.2 | 0.0 | 0.2 | 0.067 | 1/1/1 | 0.0081/0.0081/0.0081 | 0x03b37ff4:bf04568f:1316 (1) | 1 | 0 / 0 | 0.067 | 584/584/584 | 0 | 0x58daec31:dd46508f (1) | 0/1 | 0/2 |

Groups with a first-real-buy share below 5% (no buyer to trade with): 1217700000000000 wei, 1444 B, 883131/200, ETH, no hook (249): n 249, wallets 2, frb 0.012, pulled 0.0; 0 wei, 1892 B, 989999/9900, USDG, no hook (189): n 189, wallets 3, frb 0.0, pulled 0.011; 40000000000000 wei, 1444 B, 790000/60, ETH, no hook (161): n 161, wallets 1, frb 0.0, pulled 0.0; 0 wei, 1892 B, 900000/9000, USDG, no hook (152): n 152, wallets 55, frb 0.0, pulled 0.033; 0 wei, 1892 B, 989998/9900, USDG, no hook (151): n 151, wallets 1, frb 0.0, pulled 0.0; 0 wei, 1892 B, 800000/8000, USDG, no hook (141): n 141, wallets 62, frb 0.0, pulled 0.035; 0 wei, 1892 B, 700000/7000, USDG, no hook (137): n 138, wallets 58, frb 0.0, pulled 0.051; 0 wei, 1892 B, 600000/6000, USDG, no hook (122): n 122, wallets 40, frb 0.008, pulled 0.049; 1217699999999999 wei, 1444 B, 883131/200, ETH, no hook (121): n 121, wallets 2, frb 0.0, pulled 0.0; 0 wei, 1892 B, 870000/8700, USDG, no hook (113): n 113, wallets 35, frb 0.027, pulled 0.071; 0 wei, 1892 B, 500000/5000, USDG, no hook (101): n 101, wallets 51, frb 0.0, pulled 0.01; 0 wei, 1892 B, 990100/9901, USDG, no hook (98): n 98, wallets 6, frb 0.01, pulled 0.0; 0 wei, 1892 B, 860000/8600, USDG, no hook (93): n 93, wallets 24, frb 0.011, pulled 0.022; 0 wei, 1892 B, 880000/8800, USDG, no hook (90): n 90, wallets 35, frb 0.0, pulled 0.056; 0 wei, 1892 B, 770000/7700, USDG, no hook (82): n 82, wallets 35, frb 0.0, pulled 0.024; 0 wei, 1892 B, 890000/8900, USDG, no hook (66): n 68, wallets 22, frb 0.0, pulled 0.029; 0 wei, 1892 B, 750000/7500, USDG, no hook (61): n 61, wallets 24, frb 0.0, pulled 0.082; 0 wei, 1892 B, 989997/9900, USDG, no hook (60): n 60, wallets 1, frb 0.0, pulled 0.0; 0 wei, 1444 B, 10000/200, ETH, no hook (50): n 51, wallets 51, frb 0.039, pulled 0.0; 0 wei, 1892 B, 810000/8100, USDG, no hook (48): n 48, wallets 26, frb 0.0, pulled 0.021; 0 wei, 1892 B, 200000/2000, USDG, no hook (46): n 46, wallets 28, frb 0.0, pulled 0.152; 0 wei, 1892 B, 850000/8500, USDG, no hook (45): n 45, wallets 21, frb 0.0, pulled 0.0; 0 wei, 1316 B, 500000/5000, USDG, no hook (44): n 44, wallets 26, frb 0.023, pulled 0.045; 0 wei, 2276 B, 10000/200, WETH, no hook (2): n 39, wallets 39, frb 0.0, pulled 0.0; 0 wei, 1316 B, 810000/60, USDG, no hook (37): n 37, wallets 1, frb 0.027, pulled 0.0; 0 wei, 1316 B, 850000/60, USDG, no hook (35): n 35, wallets 1, frb 0.0, pulled 0.029; 0 wei, 1892 B, 100000/1000, USDG, no hook (32): n 32, wallets 20, frb 0.031, pulled 0.156; 0 wei, 1316 B, 800000/60, USDG, no hook (32): n 32, wallets 1, frb 0.0, pulled 0.0; 0 wei, 1892 B, 990000/9900, USDG, no hook (31): n 31, wallets 25, frb 0.0, pulled 0.032; 0 wei, 1316 B, 840000/60, USDG, no hook (30): n 30, wallets 1, frb 0.0, pulled 0.0; 0 wei, 1316 B, 700000/7000, USDG, no hook (29): n 29, wallets 22, frb 0.034, pulled 0.138; 0 wei, 1892 B, 400000/4000, USDG, no hook (29): n 29, wallets 22, frb 0.0, pulled 0.069; 0 wei, 1316 B, 200000/2000, USDG, no hook (29): n 29, wallets 27, frb 0.034, pulled 0.103; 0 wei, 1316 B, 830000/60, USDG, no hook (29): n 29, wallets 1, frb 0.0, pulled 0.0; 0 wei, 1316 B, 890000/60, USDG, no hook (29): n 29, wallets 1, frb 0.0, pulled 0.0; 0 wei, 1892 B, 920000/9200, USDG, no hook (28): n 28, wallets 11, frb 0.036, pulled 0.036; 0 wei, 1316 B, 400000/4000, USDG, no hook (26): n 26, wallets 18, frb 0.038, pulled 0.154; 0 wei, 1316 B, 600000/6000, USDG, no hook (26): n 26, wallets 16, frb 0.0, pulled 0.115; 0 wei, 1316 B, 870000/60, USDG, no hook (26): n 26, wallets 1, frb 0.0, pulled 0.0; 0 wei, 1444 B, 3000/60, ETH, no hook (25): n 25, wallets 25, frb 0.04, pulled 0.0; 0 wei, 1892 B, 660000/6600, USDG, no hook (25): n 25, wallets 17, frb 0.0, pulled 0.0; 0 wei, 1316 B, 860000/8600, USDG, no hook (25): n 25, wallets 12, frb 0.0, pulled 0.04; 0 wei, 1892 B, 701000/7010, USDG, no hook (24): n 24, wallets 7, frb 0.0, pulled 0.083; 0 wei, 1316 B, 450000/4500, USDG, no hook (24): n 24, wallets 12, frb 0.0, pulled 0.167; 0 wei, 1316 B, 860000/60, USDG, no hook (24): n 24, wallets 1, frb 0.042, pulled 0.0; 0 wei, 1316 B, 820000/60, USDG, no hook (23): n 23, wallets 1, frb 0.0, pulled 0.0; 0 wei, 1316 B, 900000/60, USDG, no hook (22): n 22, wallets 1, frb 0.045, pulled 0.0; 0 wei, 1316 B, 880000/60, USDG, no hook (22): n 22, wallets 1, frb 0.0, pulled 0.0; 0 wei, 1444 B, 10000/200, ETH, HOOK (21): n 21, wallets 21, frb 0.0, pulled 0.0; 0 wei, 1316 B, 100000/1000, USDG, no hook (21): n 21, wallets 17, frb 0.0, pulled 0.095; 0 wei, 1892 B, 990101/9901, USDG, no hook (21): n 21, wallets 2, frb 0.0, pulled 0.0; 0 wei, 1316 B, 900000/9000, USDG, no hook (20): n 20, wallets 14, frb 0.0, pulled 0.2; 0 wei, 1316 B, 550000/5500, USDG, no hook (20): n 20, wallets 13, frb 0.0, pulled 0.25; 0 wei, 1316 B, 800000/8000, USDG, no hook (20): n 20, wallets 17, frb 0.0, pulled 0.1; 0 wei, 1892 B, 550000/5500, USDG, no hook (20): n 20, wallets 16, frb 0.0, pulled 0.05; 0 wei, 1316 B, 880000/8800, USDG, no hook (20): n 20, wallets 16, frb 0.0, pulled 0.0; 0 wei, 1892 B, 450000/4500, USDG, no hook (19): n 19, wallets 11, frb 0.0, pulled 0.0; 0 wei, 1316 B, 990000/9900, USDG, no hook (18): n 18, wallets 14, frb 0.0, pulled 0.056; 0 wei, 1892 B, 701300/7013, USDG, no hook (18): n 18, wallets 4, frb 0.0, pulled 0.0; 0 wei, 1892 B, 955950/9560, USDG, no hook (18): n 18, wallets 1, frb 0.0, pulled 0.0; 0 wei, 1892 B, 990010/9900, USDG, no hook (17): n 17, wallets 2, frb 0.0, pulled 0.0; 0 wei, 1892 B, 980000/9800, USDG, no hook (17): n 17, wallets 12, frb 0.0, pulled 0.118; 0 wei, 1892 B, 2500/25, USDG, no hook (17): n 17, wallets 15, frb 0.0, pulled 0.0; 0 wei, 1316 B, 890000/8900, USDG, no hook (15): n 15, wallets 10, frb 0.0, pulled 0.0; 0 wei, 1316 B, 150000/1500, USDG, no hook (15): n 15, wallets 14, frb 0.0, pulled 0.333

### Token-code skeleton (fam.tok) within the non-vbot launches: every family with >= 15 launches

| key | n | per day d0..d6 | wallets | nonce p10/50/90 | fresh (nonce<=3) | any buy | frb | frb off p10/50/90 | frb ETH p10/50/90 | frb top fingerprint (n) | frb EOAs | frb repeat (>=3 pools) / also in lc fam | pulled | pull off p10/50/90 | pull<frb | pull via | early-outsider reaction nf | baseline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 16afd61e5922 | 6954 | 1387 1225 971 1078 769 809 715 | 417 | 3/5/6305.1 | 0.123 | 0.626 | 0.009 | 30.9/614/1968.8 | 0.0058/0.0105/0.0858 | 0x0d9187d4:01000400:267 (2) | 54 | 30 / 31 | 0.02 | 415.9/1471/2602.2 | 1 | 0x58daec31:dd46508f (137) | 0/87 | 0/4253 |
| cb79985db9ea | 946 | 117 60 141 153 179 158 138 | 909 | 2/2/3 | 0.938 | 0.945 | 0.77 | 71/116.5/214 | 0.0297/0.14/0.34 | 0xd6d35b56:e6cb474f:484 (721) | 97 | 713 / 724 | 0.624 | 145.9/359.5/1961.3 | 0 | 0x58daec31:dd46508f (590) | 1/55 | 28/834 |
| d4e7eae43daa | 663 | 87 46 50 155 91 137 97 | 163 | 39.4/2134/9479.6 | 0.06 | 0.341 | 0.075 | 33.5/120/2434.8 | 0.0066/0.0567/0.2137 | 0xfc7241d4:3593564c:836 (9) | 33 | 44 / 39 | 0.167 | 300/1229/2507 | 0 | 0x58daec31:dd46508f (111) | 0/61 | 1/158 |
| 58d593205138 | 480 | 66 64 78 70 46 97 59 | 155 | 77.1/694/52130.3 | 0.008 | 0.094 | 0.033 | 162/1322/2596 | 0.0062/0.0153/0.1044 | 0xccc88a9d:0a2b8f36:17604 (2) | 15 | 9 / 9 | 0.129 | 880.4/1144/2199.7 | 0 | 0x58daec31:dd46508f (62) | 0/16 | 0/25 |
| 4e451d1aef8a | 448 | 56 71 48 28 74 75 96 | 67 | 190.8/2204.5/5265.5 | 0.0 | 0.219 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.067 | 379.9/1751.5/2811.1 | 0 | 0x58daec31:dd46508f (30) | 0/21 | 0/66 |
| 564fe314d3b6 | 391 | 33 19 87 38 59 86 69 | 171 | 5/996/8651 | 0.0 | 0.435 | 0.317 | 4/4/169.1 | 0.0114/0.07/0.2822 | 0x80e49ed1:3593564c:836 (50) | 41 | 103 / 107 | 0.046 | 708.8/1200/2071.8 | 1 | 0x58daec31:dd46508f (18) | 0/59 | 0/109 |
| c0b7d40078fa | 321 | 2 29 62 33 79 57 59 | 113 | 58/639/5656 | 0.012 | 0.044 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.016 | 342.8/673/2527.4 | 0 | 0x58daec31:dd46508f (5) | 0/4 | 0/8 |
| 6a2a8d4f6cd0 | 271 | 8 14 12 7 32 5 193 | 30 | 160/370/1978 | 0.011 | 0.059 | 0.037 | 23.1/493/1161.4 | 0.0183/0.0715/0.4609 | 0x7ddbd395:fea69838:2116 (2) | 10 | 2 / 2 | 0.015 | 678.1/1263.5/1869.9 | 0 | 0x58daec31:dd46508f (4) | 0/9 | 0/7 |
| a98b3b9e80a7 | 269 | 54 66 16 24 16 73 20 | 156 | 3/310/3219.4 | 0.405 | 0.543 | 0.457 | 46/52/94 | 0.05/0.05/0.206 | 0x75379d5d:3593564c:1540 (122) | 17 | 114 / 114 | 0.03 | 790.2/1207.5/1950.7 | 0 | 0x58daec31:dd46508f (8) | 0/6 | 0/122 |
| fa4982d5acd8 | 182 | 8 25 25 51 33 19 21 | 71 | 339.1/2102.5/8168.9 | 0.0 | 0.093 | 0.022 | 222.9/607.5/2026.7 | 0.0061/0.0069/0.0136 | 0xccc88a9d:0a2b8f36:3684 (1) | 4 | 2 / 2 | 0.055 | 621.9/1103.5/2713.6 | 1 | 0x58daec31:dd46508f (10) | 0/5 | 0/10 |
| 037449b17ce6 | 142 | 14 22 32 25 10 15 24 | 70 | 40.3/598.5/5771 | 0.0 | 0.056 | 0.028 | 91.9/212.5/1523.1 | 0.0208/0.0618/0.178 | 0x603206d6:3f0bde25:1163 (1) | 4 | 3 / 3 | 0.077 | 443/1068/2454 | 0 | 0x58daec31:dd46508f (11) | 0/3 | 0/4 |
| 8213fb3a1859 | 134 | 1 2 1 7 62 42 19 | 52 | 24.6/840/6716.8 | 0.007 | 0.239 | 0.157 | 10/376/1929 | 0.0065/0.0212/0.0877 | 0xf0b7eaaf:39ecce49:1060 (1) | 19 | 12 / 15 | 0.164 | 256.6/981.5/2218.7 | 0 | 0x58daec31:dd46508f (22) | 1/23 | 1/7 |
| 6aa075332129 | 129 | 1 2 7 61 32 7 19 | 16 | 116.6/241/676.4 | 0.0 | 0.016 | 0.016 | 62.4/184/305.6 | 0.0088/0.0117/0.0145 | 0x28df563f:a0040023:263 (1) | 1 | 2 / 2 | 0.457 | 1044.8/1156/2187.6 | 0 | 0x58daec31:dd46508f (59) | 0/1 | 0/1 |
| f21d2b1e0215 | 93 | 14 44 16 4 8 4 3 | 27 | 82.2/477/3054.2 | 0.0 | 0.14 | 0.108 | 338.4/1938.5/2875.4 | 0.0068/0.015/0.0267 | 0xccc88a9d:0a2b8f36:3140 (3) | 7 | 10 / 9 | 0.118 | 841/1763/2083 | 0 | 0x58daec31:dd46508f (11) | 0/2 | 0/11 |
| 65daaea0eb53 | 83 | 5 9 15 12 16 13 13 | 48 | 79.2/1322/7296 | 0.024 | 0.277 | 0.012 | 34/34/34 | 0.0742/0.0742/0.0742 | 0x65050a9b:4d819a2a:580 (1) | 1 | 1 / 0 | 0.169 | 699.6/1929/2674.5 | 0 | 0x58daec31:dd46508f (14) | 0/1 | 0/20 |
| 2be340ff91da | 58 | 27 9 6 9 1 3 3 | 35 | 177.8/2168/7593.9 | 0.0 | 0.155 | 0.017 | 150/150/150 | 0.0062/0.0062/0.0062 | 0x28df563f:a1040011:311 (1) | 1 | 1 / 1 | 0.103 | 649/1673.5/2073.5 | 0 | 0x58daec31:dd46508f (6) | 0/3 | 0/6 |
| 97c7ba1b0d3f | 50 | 1 1 9 7 7 21 4 | 25 | 112.9/1405.5/7214.3 | 0.0 | 0.02 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.06 | 1459.6/2038/2150 | 0 | 0x58daec31:dd46508f (3) | 0/0 | 0/1 |
| 41e79f39d63d | 49 | 27 5 3 3 10 1 0 | 24 | 244.4/848/2541.8 | 0.0 | 0.102 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/5 |
| 41ff56a3838e | 45 | 1 1 4 4 0 18 17 | 31 | 126/1317/5433.8 | 0.0 | 0.111 | 0.044 | 442.7/1501.5/2560.3 | 0.0203/0.0207/0.021 | 0x68d41e60:0c89e77a:366 (1) | 2 | 1 / 2 | 0.067 | 418.6/517/1361.8 | 0 | 0x58daec31:dd46508f (3) | 0/4 | 0/1 |
| ac88142e186c | 40 | 2 3 16 4 3 3 9 | 21 | 210.1/2247.5/7523.7 | 0.0 | 0.075 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.025 | 2792/2792/2792 | 0 | 0x58daec31:dd46508f (1) | 0/2 | 0/1 |
| 0ae090736572 | 33 | 0 29 3 0 1 0 0 | 26 | 118/1387/8370.4 | 0.0 | 0.485 | 0.273 | 44.4/372/908.4 | 0.0084/0.0139/0.0814 | 0xf0b7eaaf:39ecce49:1732 (3) | 8 | 5 / 4 | 0.152 | 780.8/1500/2067 | 0 | 0x58daec31:dd46508f (4) | 0/6 | 0/5 |
| 70adce63e2b2 | 31 | 1 1 7 8 7 3 4 | 11 | 118/453/5818 | 0.0 | 0.194 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.032 | 1946/1946/1946 | 0 | 0x58daec31:dd46508f (1) | 0/0 | 0/6 |
| da46f00671e4 | 29 | 0 0 0 0 0 0 29 | 20 | 142/581/6246.2 | 0.0 | 0.034 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.034 | 1236/1236/1236 | 0 | 0x58daec31:dd46508f (1) | 0/0 | 0/1 |
| 22efc1f9ac78 | 26 | 0 0 0 24 0 0 2 | 23 | 400.5/1661.5/8152 | 0.0 | 0.308 | 0.192 | 131.2/394/2192.4 | 0.0061/0.0092/0.0149 | 0x0737c553:81020097:264 (1) | 5 | 3 / 5 | 0.077 | 409/1069/1729 | 1 | 0x58daec31:dd46508f (2) | 0/7 | 0/0 |
| 8cca56b5678f | 24 | 5 4 5 2 3 1 4 | 14 | 73/2465.5/7952.9 | 0.0 | 0.0 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/0 |
| c93705851bff | 24 | 11 11 2 0 0 0 0 | 14 | 74.7/1374.5/4962.2 | 0.0 | 0.292 | 0.083 | 1/1/1 | 0.0083/0.0091/0.0098 | 0x03b37ff4:bf04568f:1316 (1) | 2 | 0 / 1 | 0.042 | 1559/1559/1559 | 0 | 0x58daec31:dd46508f (1) | 0/3 | 0/4 |
| aff2095fe75b | 23 | 1 3 0 9 6 3 1 | 15 | 50.4/1127/5775.4 | 0.0 | 0.087 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.043 | 2282/2282/2282 | 0 | 0x58daec31:dd46508f (1) | 0/0 | 0/2 |
| 9826fe8abb23 | 21 | 0 1 0 16 3 0 1 | 14 | 59/760/6111 | 0.0 | 0.143 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/3 |
| 8ac8e66327f5 | 19 | 0 0 0 12 7 0 0 | 7 | 444.8/5736/64158.8 | 0.0 | 0.0 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/0 |
| 133066b8899e | 16 | 0 16 0 0 0 0 0 | 12 | 326.5/2117.5/6850 | 0.0 | 0.125 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.062 | 2181/2181/2181 | 0 | 0x58daec31:dd46508f (1) | 0/1 | 0/1 |
| ef0c062c9a98 | 16 | 0 0 0 14 2 0 0 | 11 | 91.5/1038.5/7685 | 0.0 | 0.062 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/1 | 0/0 |

### Launch wallet: the 15 largest of the 124 wallets with >= 15 launches (none has a first-real-buy share >= 20%)

| key | n | per day d0..d6 | wallets | nonce p10/50/90 | fresh (nonce<=3) | any buy | frb | frb off p10/50/90 | frb ETH p10/50/90 | frb top fingerprint (n) | frb EOAs | frb repeat (>=3 pools) / also in lc fam | pulled | pull off p10/50/90 | pull<frb | pull via | early-outsider reaction nf | baseline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0x909a0af40a | 447 | 37 119 70 33 41 77 70 | 1 | 1501.8/2159/3214.8 | 0.0 | 0.092 | 0.007 | 214.4/372/536.8 | 0.0079/0.0104/0.1693 | 0xf0b7eaaf:39ecce49:1732 (2) | 3 | 0 / 0 | 0.004 | 2094.1/2134.5/2174.9 | 0 | 0x58daec31:dd46508f (2) | 0/7 | 0/26 |
| 0xf159c76157 | 399 | 72 65 73 33 58 63 35 | 1 | 1768.2/2285/2785.6 | 0.0 | 0.028 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.003 | 433/433/433 | 0 | 0x58daec31:dd46508f (1) | 0/1 | 0/9 |
| 0x511a69dab0 | 308 | 81 74 71 49 33 0 0 | 1 | 62906.8/63504.5/64111.1 | 0.0 | 0.042 | 0.01 | 115.4/529/959.4 | 0.014/0.0495/0.0899 | 0xf5307745:5f575529:4069 (1) | 3 | 0 / 0 | 0.003 | 1694/1694/1694 | 0 | 0x58daec31:dd46508f (1) | 0/5 | 0/6 |
| 0x136ae1c077 | 230 | 0 0 0 0 0 0 230 | 1 | 179.8/365/582.2 | 0.0 | 0.0 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/0 |
| 0xc5ca9505ec | 200 | 200 0 0 0 0 0 0 | 1 | 3/4/5 | 0.35 | 1.0 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/200 |
| 0x28ef99c944 | 200 | 200 0 0 0 0 0 0 | 1 | 3/4/5 | 0.35 | 1.0 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/200 |
| 0x4e547dd83e | 200 | 200 0 0 0 0 0 0 | 1 | 3/4/5 | 0.35 | 1.0 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/200 |
| 0xfefa3f8031 | 200 | 200 0 0 0 0 0 0 | 1 | 3/4/5 | 0.35 | 0.81 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/162 |
| 0x5374ec8035 | 200 | 0 200 0 0 0 0 0 | 1 | 3/4/5 | 0.35 | 1.0 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/200 |
| 0x864c76e769 | 200 | 0 200 0 0 0 0 0 | 1 | 3/4/5 | 0.35 | 1.0 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/200 |
| 0x9ad9fd788e | 200 | 0 200 0 0 0 0 0 | 1 | 3/4/5 | 0.35 | 1.0 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/200 |
| 0x0167acc240 | 200 | 0 0 200 0 0 0 0 | 1 | 3/4/5 | 0.35 | 1.0 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/200 |
| 0x025d00e246 | 200 | 0 0 200 0 0 0 0 | 1 | 3/4/5 | 0.35 | 0.85 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/170 |
| 0x8e8409d9ed | 200 | 0 0 200 0 0 0 0 | 1 | 3/4/5 | 0.35 | 1.0 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/200 |
| 0xff320f5227 | 200 | 0 0 0 200 0 0 0 | 1 | 4/5/6 | 0.0 | 1.0 | 0.0 | -/-/- | -/-/- | - (0) | 0 | 0 / 0 | 0.0 | -/-/- | 0 | - (0) | 0/0 | 0/200 |

All 124 wallet groups: first-real-buy share distribution {0.0: 114, 0.1: 8, 0.2: 2}; median launch nonce of these wallets: 927.5

### msg.value spectrum of the whole launcher family (vbot included; 21,018 pools, quote pairs excluded): top 40 exact values

| value (ETH) | pools | of which non-vbot |
|---|---|---|
| 0 | 6574 | 6574 |
| 3 | 3355 | 0 |
| 2.4333285 | 3182 | 0 |
| 0.000735 | 2800 | 2800 |
| 5 | 1543 | 0 |
| 0.00063 | 1200 | 1200 |
| 0.0012177 | 383 | 383 |
| 4e-05 | 161 | 161 |
| 0.000525 | 150 | 150 |
| 9.333333333 | 111 | 111 |
| 40 | 110 | 110 |
| 2 | 103 | 103 |
| 1.8 | 29 | 29 |
| 33.33333333 | 16 | 16 |
| 1.7 | 12 | 12 |
| 4 | 12 | 12 |
| 0.005 | 7 | 7 |
| 10 | 6 | 6 |
| 1e-06 | 6 | 6 |
| 1.6 | 5 | 5 |
| 0.0005 | 5 | 5 |
| 0.5 | 4 | 4 |
| 1.9 | 4 | 4 |
| 1.000250094 | 3 | 3 |
| 8.333333333 | 3 | 3 |
| 0.004 | 3 | 3 |
| 1.5 | 3 | 3 |
| 16 | 2 | 2 |
| 0.0002000500188 | 2 | 2 |
| 0.001882961294 | 2 | 2 |
| 0.1 | 2 | 2 |
| 1 | 2 | 2 |
| 0.008823529412 | 2 | 2 |
| 1.008261551 | 2 | 2 |
| 0.0003518947289 | 2 | 2 |
| 0.02042801556 | 2 | 2 |
| 0.001 | 2 | 2 |
| 0.05848591659 | 2 | 2 |
| 0.05124 | 2 | 2 |
| 0.60701 | 2 | 2 |

Distinct exact values: 1237 (non-vbot 1234). Non-vbot by decade: {"1e-5": 355, "1e-4": 4731, "0": 6574, "1e1": 134, "1e-2": 92, "1e-3": 678, "1e0": 296, "1e-6": 29, "1e-1": 42, "<1e-6": 7}.

1,444-byte ETH hook-free non-vbot launches by value (top 25): 0.0012177 x383, 4e-05 x161, 0 x113, 9.333333333 x111, 40 x110, 2 x103, 1.8 x29, 33.33333333 x16, 1.7 x12, 4 x12, 10 x6, 1.6 x5, 1e-06 x5, 1.9 x4, 8.333333333 x3, 0.005 x3, 1.5 x3, 16 x2, 0.001882961294 x2, 1 x2, 0.5 x2, 0.0005 x2, 0.60701 x2, 0.001673834547 x2, 1.05 x2

## Scripts (run in order; all read the census cache only)
`extract.py` (lc rows + launch calldata decode -> lc_rows.jsonl), `load_ev.py` (events -> ev.pkl), `common.py`, `spectrum.py`, `groups.py`, `groups_value.py`, `cands.py` (line definitions), `detail.py` (first-12-swap patterns), `vbot_router.py`, `hooks.py`, `replay.py` (the replay), `rules_run.py` (the brief's rules -> rules_results.json), `tp_grid.py`, `follow_grid.py`, `optx.py`/`optx_c1.py` (operator calldata), `c1_nofrb.py`, `c1_signal.py`, `c1_wave.py`, `c1_reaction.py`, `c1_move.py`, `a98b_sells.py`, `checks.py`, `misc_counts.py`, `final_numbers.py`, `tables.py`. Each `X.py` has its output in `X.out`.
