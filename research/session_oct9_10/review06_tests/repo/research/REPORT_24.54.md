### 24.54 Supply: 24.45's pending v4 test, run on the chain, and the four conditions elsewhere (Oct 8)

*Why.* The owner's research item 5, research only. Report 24.45 left one open candidate on Robinhood Chain's v4 pools: the 2-2.45%
fee families, which paid +14% to +92% on paper at the first seat. Its decisive question was whether the operator withholds the
pump and pulls the liquidity when an outsider buys first. The test was five to ten $3 trades at the first seat. This session
holds no wallet, and every outside buy on these launches is the same experiment with someone else's money. So the test was run
from the chain: every launch, swap, liquidity change and swap sender, Sep 29 21:00 - Oct 8 10:30 UTC.
- Pull: `src/analysis/v4_slowrug_pull.py`, data in `data/derived/edge_check/Q/`.
- Test: `src/analysis/v4_slowrug_test.py`, output in `slowrug_test.txt`.

*Supply: the family is one operator, and it has left the fee tier.*
- **One launcher.** On Sep 27-29, 107-126 of the family's launches a day went through one launcher contract, `0x3194e326`, from a
  fresh deployer every time.
- **Fewer launches.** From Sep 30 the operator made 22-56 a day across 1.2-5% fees.
- **A new tier.** From Oct 5 13:00 it moved to 0.01-0.5% fees (54, 133 and 111 on Oct 5-7; 13 by Oct 8 10:30) and stopped the
  2-2.45% tier (0 launches Oct 6-8).
- **Follow the launcher, not the fee.** A fee filter would have lost the family. One reading of the 1.5-5% band alone suggested the
  operator had quit. A sample of the 1% family found none of its launches there.

*Anatomy.* 99% of the swaps on its 602 launches are its own wallets:
- about 2,000 single-use wallets (nonce 0, each on one launch);
- a fleet of about 50 wash wallets (thousands of nonces, trading only its launches, 5-11 swaps per launch).

The crowd's first buy lands at block 22, 44 or 64 (p10, p50, p90), with 34 buys and 1.5 ETH in 30 s. The deployer removes all
the liquidity on 94% of launches within 20 minutes (median block 2,393, four minutes).

*The test, read from other people's buys.*
1. **The first seat is empty, and the one outsider who took it got nothing.** 141 of the 602 launches drew a real outside buy (0.0002
   ETH or more from an established wallet), at a median of 55 s in, behind the crowd. In eight cases an outsider bought before
   the crowd. One matches the planned test exactly. On Sep 30 a wallet with 319 transactions, through its own router, bought
   $2.54 in block +1 of a 1.35% launch. The operator sent no crowd, and the deployer removed 100% of the liquidity 14 blocks later.
   With 24.45's two early buyers, that is three of three first-seat outsiders with no pump after them.
2. **The pull answers outside money.**
   - Fee tiers of 2% and up: the deployer pulls 5 blocks (0.5 s) after an outside buy. A $2.6-5 buy is followed by the pull
     within 1 s on 65% of occasions and within 3 s on 74% (n 23). A $5-13 buy: 88% and 94% (n 16). A test-size dust buy almost
     never triggers it.
   - The sub-1% tier: the reflex is slower (10-19 blocks, mode 15) but still there. Within 3 s, a $2.6-5 buy is followed by the
     pull 44% of the time (n 16), a $5-13 buy every time (n 10).
   - On both tiers the first outside buy is followed by the pull within 5 s on 71% of 141 launches. A placebo (arrival times
     drawn from the outsiders' own, on launches no outsider bought) gives 1.6%.
3. **The outsiders who bought lost.** 183 positions, 164 lost everything, net -3.68 ETH on 4.41 ETH in.

*The $3 seat, priced.* On paper, with the crowd and the pull schedule unchanged by us, a $3 buy at the head of block b0+1 makes:
+22% at a 10 s hold, +55% at 20 s, +82% at 30 s, winning about 90% of the time. That reproduces 24.45 on the new period. With
the reflex, the pull lands before a 10-30 s exit on at least 74% of $3 buys in the 2-5% tiers and at least 44% in the sub-1%
tier. The expected return is at most -60% and -13% a trade. The one real first-seat $3 buy lost all of it.

**The pending test is answered without running it: the 2-2.45% family is a trap.** Its pump is the operator's own wash money, and
its pull follows any outside buy of a few dollars within a second. Five to ten live $3 trades would cost about $2-3 each to
show what the chain already shows.

*A variant the chain cannot test.* The operator's sub-1% tier (from Oct 5) changes one number: a round trip costs about 0.1%
instead of 4-5%.
- **The rule.** Buy two blocks after the first real-size buy on one of its pools (the operator's crowd on 306 of 312), then
  sell 4 blocks later. That prices at +3.6% a trade (83% winning, p5 -0.8%). Selling 9 blocks later prices at +6.5% (94%). The
  numbers are the same at $3 and $25, and positive on every day Oct 5-8 (+2.4% to +6.2% at 4 blocks).
- **Why it might work.** Both exits come before the tier's 10-19-block reflex. The 4-block exit would beat even the 5-block
  reflex of the earlier tiers.
- **Where the money comes from.** All of it is the operator's own wash money: 553 of the 560 non-dust buys inside the hold
  are its wallets.
- **Why the 2% tiers fail.** The same rule is about zero there (-0.2% to +0.3%); the fees take it.
- **What the chain cannot say.** Whether our buy shortens the reflex or stops the crowd. Nobody outside has done this; 7 outside
  buys in all landed in those windows.

This, not 24.45's design, is the only $3 question left on this family. It is a $15-30 question with a short life. The tier is
three days old, the operator changes its fee every few days, and an operator watching its own pools can end it whenever it
likes. A test would need:
- the launch read from the feed (a transaction to `0x3194e326`);
- the crowd's first buy read from the feed (a router call carrying the pool key);
- a v4 buy-and-sell relay (BuyOnce is Pons-only);
- a sell landing 0.4-0.9 s after the buy.

Not built: research only.

*The other launchers in the band:*
- `0x815542e8` (3%, 179 launches): no scripted crowd. The seat loses its fee (-6.6%), and outsiders lost 28% on average.
- `0x58daec31` (a multicall many launchers share): outsiders lost 37 ETH on 45.
- `0x7c7e48f9` (2%): the seat loses about 5%.

*The four conditions elsewhere* (`data/derived/edge_check/Q/SURVEY.md`). The conditions are:
1. FCFS with no priority fee.
2. A launch tax keyed to discrete time.
3. An exact curve.
4. A pre-tick crowd visible on the feed.

Two web surveys (chains; launchpads) were checked on the chain where it decides the answer:
- **Robinhood Chain still meets 1 and 4** (measured Oct 8). Half the transactions offer a tip, but tip order is random (48% of
  adjacent pairs descending), and no receipt was charged above the base fee (0 of 41).
- **Arbitrum One left the FCFS set.** On Sep 10 its blocks were random in tip (48%) and charged no tips (0 of 43). On Oct 7 they
  were sorted by tip (79%) and charged them (32 of 50), consistent with the reported switch to priority-gas auctions on Sep 24.
- **Two other Robinhood launchpads meet 2 and 3:**
  - Clanker v4: swaps revert in the deployment second, then a fee falls per second from 66.7% to 4.2% over 15 s.
  - Bankr/LONG on Doppler: 80% falling linearly to 1.69% over 10 s.

  Neither has a crowd. Clanker made 13 launches in seven days. Of 1,135 Doppler-hook launches a day, 4% have any swap in the
  first minute. Both tax sells inside the window, and neither has Pons' cliff.
- **Every other time-keyed launch tax runs on a priority-fee chain**, where the seat is bought, not raced: Zora and Virtuals v5 on
  Base; Meteora's fee scheduler, Jupiter Studio and Heaven on Solana; four.meme's X Mode on BSC; Clanker on Monad.
- **Possible FCFS chains without the launchpad.** MegaETH (ordering undocumented) and the default Orbit chains may meet condition
  1. Neither has a time-tax launchpad yet.

**Verdict: the four conditions hold together in one place, Pons on Robinhood Chain.**

Watch items, each of which would change this:
- Robinhood Chain turning on tip ordering. ArbOS 61 allows it, off by default; it would end the free race on Pons too.
- A Virtuals v5 router going live on Robinhood. The repository carries deploy scripts for it; its tax is per second, can start at
  a scheduled time, and runs on a constant-product curve.
- A time-tax launchpad appearing on a confirmed FCFS chain.
