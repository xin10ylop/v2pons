# The ride on the volume bot's 2.4333 and 3.0 lines (hand-back ~18:05 UTC Oct 11)

Result: no ride on either line; both NOT tradable. The ride pays when nobody reacts, but the operator pulls about 9 blocks after a
stranger buys after T (the bot's first buy) too, and the ride has to hold about 25 blocks. Our pools are excluded from "untouched" figures.

1. What the bot does after T (r04/r05 census, r12 chain: 311 launches in 6 h with every log to +400 and their transactions). Buys go to
   0x1cbaf24d (c1120e3d) from 141 wallets; sells from those wallets to the Universal Router (24856bc3); pulls a0f7978d on 0x1cbaf24d; no
   new router; no non-bot buy >= 0.02 ETH. 2.4333 census: T at +8, the 2nd buy at T+27 (p10/90 T+20/33), 0.15 ETH, +12%; first bot sell
   T+33; 6% pulled by T+30. From Oct 10 13:52 fronted pools were pulled at T+3 (377 of our 400 on Oct 10 06-12 UTC; 1 of 129 untouched).
   Today before 15:32 untouched (40): 2nd buy T+26, +11.6%, no pull by T+60; our 118 fronted pools pulled at T+3 in 108 (timed off T).
   15:32-16:28 (14): 6 pulled at T+18..20 with no 2nd buy. From 16:28 (4): 2nd buy T+23, +18%, no pull. 3.0: before 04:22 the 2nd buy at
   T+24 (+8%), first sell T+34; since 04:22 T at +38..+42, 2nd buy T+24 (+8.3%), the first sell at T+25 before the 2nd buy in about half.
2. Ride replay (q 0.0058, buy at the head of T+2; validated exactly on our 131 real trades, r18). Best rule: sell right behind the bot's next
   buy (q 0.002 or 0.0097 changes results by <= 0.3 points; T+1 = T+2). 2.4333 census days 0-5 with no reaction: n 1,816, mean +3.6%, median
   +9.0%, win 88%, worst -100%, 5.0% pulled, $0.54/trade (by day +8.0/+7.0/+2.5/+0.3/+3.2/+1.0%; day 6 -87%, 88% pulled). Chain, no reaction:
   fee-2500 pools n 40 +8.75% win 92.5% worst -10%; 15:32-16:28 n 14 -38% (43% pulled); from 16:28 n 4 +10.7% ($1.60/trade, ~$690/day at
   432 launches/day). 3.0 no reaction: n 95 +2.2%, median +2.5%, win 73%, 0 pulled, $0.33/trade (~$92/day); census new regime +1.6% (n 156).
   Fixed holds 10-60: -2.3..+4.3%. Break-even pull rate ~8%. With the reaction modelled (a pull at our buy + 7) every rule on every line is
   -100%.
3. Reaction to buys after the bot (r08/r09/r14/r16/r17). Census, one-off wallets buying >= 0.00003 ETH after T: 2.4333 86 pools, 65 pulled
   within 14 blocks of that buy; 3.0 96 pools, 88 pulled within 14; median lag 9 on both. Between T and the 2nd buy: 14 of 19 pulled by T+30
   (2.4333) vs 23 of 950 without such a buy; 3.0 15 of 20 vs 28 of 2,723. Dust under 0.00003 draws no reaction; recurring (its own) wallets
   are spared. 3.0 today: a 0.002 buy at T+47/+68/+75 pulled 9/8/9 blocks later (3 of 3); all 7 non-dust buys after T pulled 5-27 later;
   before the bot 0x8c009ea5 (0.002 at +4..+6, 22 pools) pulled 3-6 later in 18; 0x7ae81404 (0.00297 at +1/+2, 4 pools) pulled 5-7 later;
   our probe 9 after. The 3.0 pull follows any non-dust stranger buy at any time. 2.4333 today: two late strangers (0.0023 at T+214, 0.0002
   at T+221) pulled 26-27 later; 1 case since 15:32. Our pools where our front made the bot's buy revert (6): 3 rebought ~26 blocks later and
   lived (pulls +78, +138, none in 400); 3 no rebuy, pulled +27/+28/+28.
4. Decoys on 2.4333 since 16:28 (r15), per pool: a fresh wallet (nonce 0) buys 0.00495 via the router 0x65050a9b at +1..+3; 0xb8c879dc buys
   0.00495 via 0xfd1b271f at +2..+4 and sells at T+1; 0x8cf143dd buys 0.00013 or 1e-05; the sentinel 2e-06. ETH ahead of the bot p50 0.0099,
   p90 0.01003. A 0.002 front fills the bot's buy at 1.0004 (min of 4 pools), 0.0024 at 1.0001, 0.0058 reverts 4 of 4. 57 fresh decoy
   wallets in 3 h, all nonce 0, no funding transaction within 2,000 blocks back (funded earlier or internally).
5. A $5 ride probe (2.4333 only) would need a new engine mode (an exit armed on the T trigger) and the census reaction predicts -100% in
   65-76% of pools: one pull in 10 trades rules it out; no cheaper test exists because buys under 0.00003 are ignored.

Note on research/session_oct11/vbot_recent.py: its decoy column matched `from == 0x65050a9b` but that address is the router the decoys call
(the `to`), and it looked for bot sells sent to the bot's router while they go to the Universal Router; its 2nd-buy and pull columns agree
with this analysis. Files: analysis/R/ (r01-r18 with outputs, common.py, ride.py, case lists r08_cases.txt, r14_cases.txt).
