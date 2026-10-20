# The adversarial verifier on C-1, Oct 11 (hand-back ~16:30 UTC)

## Verdict: NOT YET
The census line reproduces exactly, the token can be sold and our relay trades it; but all of the profit is the operator's own buying, that
buying almost stopped in the 2.6 h after the census, and the census cannot show how the operator reacts to us.

For: (1) own replay: entry at the bot's first buy T + 2, hold 60: n 573, mean +16.3%, median +9.9%, win 78.2%, pulled before sell 3.1%,
$200/day; positive every census day; holds for T+1..T+3. (2) We can sell: the token is a plain OpenZeppelin ERC20 with burn, 11 functions,
no owner, no external calls, no time/origin checks (no tax, blacklist, max-wallet or cooldown possible); an eth_call round trip through our
deployed relay on a live C-1 pool: buy then sell -0.025%, matching v4math; 501 outsider round trips in the census: mean +20.5%, median +10.4%.
(3) No fast reaction to strangers visible: pulls within 30 blocks of a stranger's buy >= 0.001 ETH: 1 of 118 vs 4.0 expected; one rider
(0x97ac054b, 0.0002 ETH) is in 448 of 573 pools.
Against: (1) in our hold windows the bot's router bought 591.3 ETH, everyone else 0.42 ETH; replaying only the others' swaps gives -3.3%; the
operator can stop buying when it sees us at no cost. (2) Fading: +27.3% (Oct 5) to +10.2% (last 24 h; +6.7% without the top 5%); after the
census, 18 launches, 17 with a bot buy: +1.8% mean, +0.65% median, 10/17 wins; median bot buying by T+60 fell to 0.04 ETH vs 0.3-1.4 ETH on
census days (p ~0.008 under the census distribution). (3) The census is blind to a reaction against us: strangers of our size are rare (6-8
bought >= 0.005 ETH in 7 days, 2-3 pulled within 100 blocks vs 0.6-1.0 expected); our relay is a public address with 1,091 past trades;
operator A pulled 24 of our 43 trades and that census showed nothing either.

Answers: the bot sells through the same router in 125 of 573 pools by T+100 (first sell at T+48/85/96); the pull comes 5/27/127 blocks after
its last buy. Holds 40/80/100: +12.8%/+20.0%/+22.0% with 1.0%/5.6%/7.9% pulled. Reaction (buy >= 0.001 ETH within 10 blocks of the trigger,
every swap tx fetched): 21 pools, 3 pulled within 60 blocks vs 1.0 expected; the 4 pulled within 100 blocks came 60, 64, 45, 60 blocks after
the stranger's buy. A's 0/32 reproduces (30-block window); B's 8/37 reproduces but 4 of the 8 are the bot's own router wallets and 2 in pools
the bot never bought. Depth at entry 10.0-12.2 ETH virtual (min 8.1); our buy +0.11%, our sell -0.12%. Router call e6cb474f: word 2 = ETH in
(6,722 of 6,722), word 3 = min-out 0 (all 6,749), word 7 = 0 marks a buy, word 8 = the token; gas limit 1,000,000, priority fee = gas price;
confirmed in full on 3 buys and 2 sells from the chain. Engine fit: the engine drops the call (no ETH value); decode_launch decodes 453/453
launches: fee 100, ts 1, sqrtP 792280926924313289846529216293289, ticks -887272..184216, liquidity 1.00000088e23 (444 of 453; 5 variants);
the front liquidity check read 0 (launch tick == the range's top tick); 32% of triggers after the 150-block trigger limit; the live pool
charges 125 ppm (25 ppm protocol fee), < 0.01 point. Not covered: signing, nonce, gas, block position, the pool state 60 blocks later, the
relay's balance, any reaction to a real transaction.

Live probe only after: the engine change built with tests, and a dry run of >= 24 h and 100 triggers showing >= +8% mean and median bot
buying >= 0.3 ETH by T+60. Setup: 0.002 ETH stake, buy at T+2, sell at entry + 60, take-profit off; trade every other trigger and dry-score the
rest; 40 trades. Halt on: 2 pulls within 20 blocks of our buy; 2 pulls before our sell in the first 20 trades or 3 in 40; bot buying in traded
pools below half that in untraded pools over 15+ pairs; mean below +3% after 20 trades or -$15 cumulative; the router call changing or no bot
buy for 3 hours. Scale to 0.0058 ETH only after 40 trades at >= +5% mean with <= 5% pulled before the sell.

Replay grid (hold 20/40/60/80/100): T+1 +9.1/+13.9/+17.5/+21.0/+23.2% (pulled 0/0.9/3.0/5.4/7.9%); T+2 +8.0/+12.8/+16.3/+20.0/+22.0%
(0/1.0/3.1/5.6/7.9%); T+3 +6.4/+11.4/+14.7/+18.2/+19.8%. Per day (T+2 hold 60): Oct 4 72 launches/71 with a bot buy +15.4%; Oct 5 45/44
+27.3%; Oct 6 97/67 +16.0%; Oct 7 117/82 +16.9%; Oct 8 131/112 +16.7%; Oct 9 129/109 +16.7%; Oct 10 107/88 +10.2%. Files: analysis/V/
(sim.py, harness.py, rpc.py, v01..v26 with .out).
