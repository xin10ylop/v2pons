# Analyst G: the owner's method brute force (every launch-shape family x 2,574 rules), hand-back ~18:20 UTC Oct 11

Answer: the grid finds no new line that is both large and safe. The only family that passes every check is the vbot 2.433 line we already
trade (the calibration). Detail: analysis/G/g08_detail.out (per line), g15_table.out (ranked), g06_select_q0.0058.out (all 123 families).

Method. Families kept (>= 20 launches in 7 days and >= 8 in the last 48 h): 79 of 9,829 launch-shape families (target/created contract,
selector, calldata length, fee, tick spacing, hook or not, quote, msg.value) and 44 of 853 token-skeleton families: 123 families, 29,907
pools. Rules: 18 entry offsets K x 143 exits = 2,574 per family (the grid runs in ~15 s). Replay gsim2.py: the brief's method plus
concentrated liquidity across ranges (the single-range formula had made a late narrow position on template d4e7eae4 look like +2,856x) and
our relay's 2,177 historical swaps removed; on 21,923 sampled swaps the replayed price path has median error 1.9e-19, p99 1.4e-10. Rule
choice three ways: V (positive on days 1-5 and 6-7, every 6-hour slice with >= 3 trades positive, best $/day on days 6-7: optimistic), F
(chosen on days 1-5, measured on 6-7), W (chosen on days 1-6, measured on day 7). 9 families have a V rule with every slice positive, 16 more
with a negative slice, 98 none (42 USDG).

Calibration passes: 2.433, all 7 days, buy at K1/K2 and sell into the next buy >= 0.03 ETH within 10 blocks: +11.5%/+9.8%; take-profit 1%
within 10: +11.6%/+11.4%. Our 1,087 real round trips found in the census made +8.43% before gas; the replay of the same trades +8.34%.
1,035 of those buys landed at launch + 1, not + 2.

Top 15 (V rule, q 0.0058): 1 C-2 hooked (initialize 196 B, hook) 16/day K100 hold100 +1130% (likely honeypot: our relay's sell reverted
3/3); 2 vbot 2.433 882/day K1 sell into next buy >= 0.01 within 40: +12.8%/+14.4%, 99% win, 0.6% pulled, $1,686/day, 24/24 slices, +12.4%
last 24 h (KNOWN, live); 3 a98b hooked 17.5/day K40 hold200 +535% (hook cut invisible); 4 tok 037449b1 (3.0 u 5.0) 833/day K200 TP50%
+14.4%; 5 vbot 3.0 588/day K80 TP50% within 200: +21.7%/+28.3%, 93% win (KNOWN line, NEW rule, killed by the reaction); 6 vbot 5.0 222/day
K8 sell into next buy >= 0.05: +2.0%; 7 C-1 hooked WETH (564f) 14.5/day K2 hold200 +9.7% ($21/day); 8 initialize fee 3000 hook WETH
(d4e7eae4) 6.5/day K200 hold200 +7.2% (NEW, ~$7/day); 9 tok 4e451d1a 178/day +69%/-0.2% (lottery); 10 tok a98b3b9e 46.5/day +151%/-74%
(lottery); 11 USDG 1,892 B fee 200000 8.5/day (lottery, 2/7 slices); 12 tok cb79985d (C-1) 149/day K100 hold200 +9.7% with 21% pulled;
13 C-1 ETH 2,276 B 118/day K40 hold100 +5.7%/-0.1% (A's follow rule is better); 14 C-2 hookless 75.5/day K150 hold100 +7.4%/+8.2%, 98% win
(KNOWN family, NEW late rule); 15 58d59320 via eb7c0347 15/day K1 hold200 +20.2%/-0.1%, 27% win (lottery).

The operator watches us. On 2.433, in the 6-hour slice where our engine traded 449 pools, 99% were pulled by launch + 30 (3 blocks after the
bot's buy) against 5% of the 102 pools we did not touch; in the next slice it pulled 95% of all its pools; our rule survives because we sell
into the bot's buy before that pull; the line had paused for 12 h before the census ended. On 3.0 and 5.0 the operator pulled 53 of 54 and
28 of 28 pools a median 9.5-12.5 blocks after a stranger bought (baseline 36-40%). Assuming a pull 4-6 blocks after our buy: 3.0 drops to
+1.8%, 5.0 to +0.6%, C-2 hookless to +1.0% (pull 12 after), 2.433 keeps +6.9% entering at K8 (g14_reaction_safe.out). The honest
out-of-sample pick F fails on our own line (TP 12% within 200 blocks: -14.1% on days 6-7 once the 3-block pull began); W picks were positive
on day 7 in 20 of the 24 families that traded that day.

What is new and what each needs: vbot 3.0 late entry (K16-200, hold ~200; configurable today with fire_at, K > 150 needs TRIGGER_MAX_BLOCKS
raised) needs a live test of the stranger-buy reaction first (REPORT_R answers it: the pull follows any stranger buy at any time); every
K <= 12 is negative on days 6-7, including "fire at + 12, hold 60" (-21.3% on days 6-7, -30.7% in the last 24 h). C-2 hookless at K150 needs
a decoder for the 196-byte PoolManager.initialize launch, then the same reaction test. Line 8 needs WETH, the decoder and hook support for
~$7/day. The hooked lines 1 and 3 need a sell simulation through our relay and the Universal Router first (REPORT_H: no live pool to test).

Limits: hook taxes and sell reverts invisible; reaction rates use fetched buys (biased toward pulled pools); the operator's own min-out reverts
not modelled; USDG fixed at 2,570. Files: analysis/G/ (gsim2.py, tickmath.py, gstats.py, g01-g16 with outputs; the grids .npz not kept).
