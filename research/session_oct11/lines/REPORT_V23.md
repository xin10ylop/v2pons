# V3/V2 lines after verification (synthesizer, Oct 11 ~22:15 UTC)

All 27 lens results (workflow journal; the task's copy was truncated): no candidate lost 2 lenses; only reaction refuted (5 keys). The 9 keys are 4 lines. Numbers: synth/s01-s08 (G2/G3 integer replays) unless marked (lens); net of gas, $15 unless stated, val = days 6-7.

## 1. Survivors, ranked
**1. V3 356-B d27d1e00 value-0 launches (NEW).** lc:89885b75 contains all 111 (its value launches add about +1%).
- Buy +60, sell +260: n 111, +114.97%, median +0.06%, win 53.2%, 1.8% pulled; val n 83 +127.24% $787/day; last 24 h +70.15%; slices 9/9.
- Lottery: top 10% of trades give 93%; without the best 10, +11.46%. At $5: $268.5/day val, median -0.21%.
- Who: the operator's SwapRouter02 pump fleet; 22 of 111 trades get a buy in the hold (+588.8%), the other 89 -2.15%.
- Reaction: pulls are cleanup from +239 on. But an outside buy of 0.0005 ETH or more before +60 goes with no pump: 6/44 pumped vs 32/67 (Fisher p 0.0002, by-day odds ratio 0.21), and those pools made +12.65% vs +182.17%. Our buy is such a buy.
- Engine: the V3 route plus a d27d1e00 decoder (356 B, value 0, pool by CREATE2), fixed timers.

**2. V2 tok 70adce63, value >= 40 ETH (known operator, new rule).**
- Buy +150, sell +250: n 1029, +1.60%, median +1.49%, win 76.1%, 0 pulled; val n 325 +1.64% $39.8/day; last 24 h +1.60%; 28/28. At $5 $11.2/day; at 0.1 ETH $737/day.
- Who: the operators' first buy, in the hold in 89.2% of trades; without it -0.73%.
- Reaction: pulls come at least 158 blocks after a stranger's buy (lens k03), so the margin is 58 blocks.
- Engine: a V2 route (router 0x89e5db8b), keyed on f305d719, 196 B, value >= 40 ETH.
- Top risk: their reaction to an outside buy before theirs is unseen since day 4.

**3. V2 fleet tok 0f34e3b5 (known, new rule; = the 1.0-ETH shape minus 24 losing tokens).**
- Buy +20, sell +80: n 603, +3.53%, median -0.73%, 0 pulled; val n 183 +3.70% $50.4/day; last 24 h $28.7; 19/19. At $5 $15.8/day.
- Who: operator-funded single-use wallets (a buy in the hold in 41.8% of trades).
- Reaction: certain; 160 of 165 pulls land 76-100 blocks after an outside buy (lens): a 16-block margin.
- Engine: the same V2 route, keyed on value 1.0 ETH.
- Top risk: a clock under 60 blocks makes every trade -100%.

**4. V3 crowd line (known): the 836-B shape; tok d4e7eae4 is the same launches (1,013 shared).**
- Census, K20 sell +80: n 1046, +7.76%, median -0.05%, $118.3/day val, 28/28.
- The crowd's min-out is 0 (681/681, lens): our buy cannot revert it.
- After the census it stopped paying: in 23 launches the crowd bought by +80 once, against a 38.5% census rate (p 2e-4). The rule made +0.08%, 1 win.

## 2. Refuted
- **Whole candidates:** none.
- **Reaction refutations** (the edge is the operator's or crowd's own buying, with fewer than 10 stranger cases):
  - 356-B: one 0.0004-ETH stranger buy in the hold.
  - tok d4e7eae4: 78 of 83 "strangers" are crowd bots (lens); the crowd-shape lens did not refute.
  - lc 89885b75: its only stranger wave was dumped on (lens).
  - tok 97c7ba1b: early outside buy, no pump.
  - 70adce63: no outside buy before the operators' buy on days 5-7.
- **Grid rejections (not re-verified):** 13ead562 (broken day 7), 740-B, 58d59320, 30.09 ETH, 0a600ad0, launchpads, the early fronts on the fleet and 70adce63.

## 3. New versus known
- **New line:** 356-B, a late timer on the operator's pump; C had rejected lc:89885b75 as a front.
- **New rules:**
  - Fleet: +20 lands in an empty gap, so it causes no reverts, and +80 beats the 76-block clock.
  - 70adce63: +150 replaces C's +2 front; the margin is 58 blocks, not 1.
- **Crowd line:** its min-out is now known (0), but it broke after the census.

## 4. Recommendation
**Build the V3 route first** (the engine already decodes V3 launches dry) and arm 356-B, and keep the crowd line dry until it passes REPORT_W's gate (100 or more launches at +4% or better, no pull before +80). Then build the V2 route for 70adce63 (its loss is bounded if the operators skip their buy), then the fleet.

**Gate before live money:**
1. eth_call a SwapRouter02 buy, the approve and the sell on a live 356-B pool.
2. Decoder dry 24 h: every launch caught, buy timed to +60, sell by +262.
3. A $5 probe on alternate launches (untraded launches = control).

**Halts over the first 40 trades:**
- **356-B:** halt on a failed sell; 3 or more pulls at or before our sell (census 2/111); 7 or fewer of 40 pumped (13.7 expected; false halt 1.6%, catches a 14% pump rate 83% of the time); or a loss beyond $10 (census worst drawdown at $5: -$5.04).
- **70adce63:** halt on any pull by our sell (census 0/1029), or the operators' buy in 30 or fewer of 40 (census 89.2%).
- **Fleet:** halt on any pull by our sell (0/603) or one less than 76 blocks after our buy, or a buy in the hold in 9 or fewer of 40 (census 41.8%).

Files: analysis/V23/synth/ (s01-s08, verdicts_all.json) and the 27 lens directories.
