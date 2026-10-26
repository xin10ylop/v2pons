# Other front seats on Robinhood and Base, searched by outcome (Oct 26)

Asked: all the money came from the 2.433 operator, before it changed its setup (Robinhood +$1,515 over 1,267 trades Oct 8-12; Base +$588
over 87 trades Oct 14-15). Those lines are gone. Search the same two chains for other setups like it: the same people on other wallets,
or unrelated people running the same thing. Skip the lines where the operator's bots are the only buyers it lets through and any outside
buy is rugged within seconds.

**Answer: nothing like it exists now on either chain.** The search covered Robinhood Aug 1 - Oct 26 and Base Sep 10 - Oct 26. It
assumed no operator, wallet, shape or size. It found every pool created and pulled, every wallet that bought in the first 20 seconds and
sold before the pull, and every line where a buy ahead of the fleet still got the fleet's buy to sell into.

**The 2.433 operator's line is the only one that ever had our seat:** buy ahead of the bot, sell into its buy seconds later. That was
Robinhood Sep 26 - Oct 12 and Base Oct 14-15.

**Two smaller, slower seats did exist on Robinhood in late August and early September, and disappeared.** The only real-size trader on
them was the one other crew doing this (D65, below):

- **The third operator's 1 ETH V2 tier, while it ran a slow mode** (3-12 pairs a day, pulled after 40-80 minutes), Aug 18 - Sep 15.
  D65 won 15 of 18 trips, +0.58 ETH, at 0.04-0.14 ETH.
- **A cluster of 1 ETH V3 pools at fee 0.3%** (1-8 a day, fresh nonce-2 launch wallets, through the V3 position manager), Aug 24 -
  Sep 8. D65 won 20 of 20 trips, +1.39 ETH, at 0.05-0.16 ETH; a few other wallets also won there.

Neither line pulled on real outside buys: 0 rugged of 69-137 a day. Neither gave our trade either: a buy ahead of their fleet usually got
no fleet buy (the fleet came in 1 of 6 and 1 of 3 fronted pools). The profit came from holding 3-15 minutes and selling into the pool's
general buying.

Both stopped by mid-September. On Sep 19 the tier switched to a 10-minute burst mode (100-150 pairs a day) that pulls on any foreign
buy, dust included (REPORT_OCT21). The V3 pools fell to one or two a week.

Every other line read is one of these:

- a trap of the kind described: real outside buys pulled on, unsold, with no fleet buy to sell into;
- closed: the fleet skips pools someone buys into first;
- open but not paying: a 5-10% pool fee eats the seat, or there is no fleet pump to sell into;
- crowd launches that one-time wallets snipe for small change;
- a line of a day or two that nobody tested, and that never came back.

- **The same people on other wallets: no.** The 2.433 token, byte-identical on every chain it ran, is on no pool after Oct 12 on Robinhood
  and none after Oct 15 on Base. The same developer's token family (it shares an unknown selector, `3c130d90`) is on operator A's tokens
  and on Base's fee-0 volume-bot lines. All of them are traps.
- **Unrelated people: one other crew traded the 2.433 line beside us,** the "D65" crew (`research/session_oct11/lines/REPORT_X.md`).
  - Followed from Aug 1 to today, it made money at real size in three ways:
    - the 2.433 line: +0.77 ETH over 2,171 trips (1,213 at a real stake), Oct 10-12;
    - the two slower seats above: +0.58 and +1.39 ETH, Aug 18 - Sep 15;
    - sniping one-off crowd launches: a 120 ETH V3 pool (Aug 22, +2.38 ETH), two hooked launches (Aug 3, +1.97), and about 2 ETH V2
      launches with 1-12 ETH of crowd buying on 17 scattered days (Aug 2 - Sep 23, +1.76).
  - Its real-size tries on lines that turned out to be traps lost:
    - a 5 ETH fee-0.96% line on Aug 13: -0.94 ETH;
    - a 31 ETH hooked line on Oct 1: -0.46 ETH;
    - 10-20%-fee pools on Aug 27-30: -0.51 ETH;
    - V2 0.5 ETH pairs: -0.24 ETH.
  - Since Oct 12, 6,071 of its 6,079 early trades on Robinhood were dust (0.00002 ETH); the other 8 were small probes (net +0.01 ETH).
    On BNB it trades 0.00009 BNB on the operator's pools.
  - A crew that tests new lines with real money has found nothing that pays since Oct 12.
- **Live today (Oct 26, 00:00-13:00 UTC): no new line.**
  - Robinhood: the volume bot's 5 ETH line (trap), the tick-spacing-1 line (trap), the third operator's V2 tiers.
  - Base: the V2 crew's tiers and the 0.5013 ETH timer line.

## 1. How it searched, with no operator assumed

| step | script | what it does |
|---|---|---|
| census | `census.py CHAIN START END` | every native-paired pool created in the window on Uniswap v4 (the PoolManager), every V2 factory and every V3 factory; the liquidity put in; the pull (its own liquidity taken out within 2 h); the launch transaction |
| round trips | `roundtrips.py` | every swap of every pulled pool, from creation to pull. A buy of X tokens and a later sell of exactly X tokens before the pull is one round trip, matched from logs alone. The buyer is looked up only for trips entered within 20 s of the liquidity add. |
| who | `summarize.py` | the early round trips by the contract the buyer called. A private router or relay is one group; on a public router, each wallet is one. A group profiting on two or more operators' pool types (venue + tick spacing + hook), several pools a wallet, is an independent bot. Ours and D65's are known. Ranked by what they took at a real stake (0.001 ETH or more). |
| the seat | `front.py` | per line (one pool shape and launch size, or one launch route), 14 pools a day: the fleet (recurring holders, plus buys through the line's own pull contract or through a private router 10+ wallets call); every real-size outside buy (0.001 ETH and 0.05% of the pool or more) and whether its buyer sold, or was pulled on within ~10 s while holding with no fleet buy to sell into (RUGGED); the pools someone bought ahead of the fleet, and whether the fleet still came; the paper seat (1% of the pool at launch+1, sold after the fleet's 1st or 3rd real buy) |
| verdict | `verdicts.py` | each line over all its days: **FRONT-OPEN** (fronted pools still got the fleet: the seat that paid), **CLOSED** (the fleet skips fronted pools), **TRAP** (outside buys rugged at least as often as they got out), TOLERANT, UNTESTED, MIXED. Lines the earlier reports settled are labelled and not re-tested, except the 2.433 line, kept as the control. |
| same operator | `bytecode.py` | each pulled pool's token code (pools of 0.5+): byte-identical to the 2.433 token, or carrying its selector `3c130d90` |
| the rivals | `rivals_now.py`, `rivals_timeline.py`, `wallet_tx.py` | the D65 crew's nonces now and back to February on Robinhood, Base, BNB, Ethereum and Arbitrum; what each live wallet trades |

**Validation.** Told nothing about any operator or wallet, the census and round trips found the right people and lines:

- **Robinhood, Oct 10 12:00-18:00:**
  - the early profitable wallets were our engine wallet (646 pools, +0.214 ETH) and the D65 crew (`0xb4c345dc` +0.158, `0x488faf52`
    +0.129, `0x544ef435` +0.060);
  - the 2.433 line came out FRONT-OPEN: bot buy at +9 blocks, paper seat +13.3% (our live trades made +12 to +16%), 25 of 25 real
    outside buys sold;
  - the volume bot's 5 ETH line came out TRAP, the tick-spacing-1 line (its own single-use fleet) UNTESTED.
- **Base, Oct 14:** our Base relay was found the same way (52 pools, 51 won, +0.113 ETH), and the 2.433 Base line came out FRONT-OPEN.

Over all days, our Robinhood relay measures +0.611 ETH (Oct 8-12; the record says +$1,515).

## 2. What was read

<!-- COVERAGE -->
| chain | days | native pools created | pulled within 2 h | round trips (entered within 20 s) | line-days tested |
|---|---|---|---|---|---|
| Robinhood | 86 (08/01 - 10/25) | 953,228 | 187,439 | 154,363 (63,911) | 323 |
| Base | 46 (09/10 - 10/25) | 169,683 | 41,092 | 641,972 (14,080) | 45 |
<!-- /COVERAGE -->

Robinhood's RPC served everything back to Aug 1. Base's publicnode serves about 45 days, so Base starts Sep 10; one earlier Base day (May
25) was sampled through Tenderly (section 5).

## 3. Every line where anyone bought ahead of the fleet, and what happened

**Robinhood** (lines the earlier reports settled are not repeated: operator A, the volume bot's 3/5 ETH lines, the tick-spacing-1 wash
line, the third operator's V2 tiers, the launchpad hook, the fee traps):

<!-- TABLE_RH -->
| line (venue, fee in ppm, tick spacing, launch size or route) | days | pools | verdict | real outside buys: sold / rugged | fronted pools: fleet came / none | paper seat after the fleet's 1st buy |
|---|---|---|---|---|---|---|
| v4 fee 2500 ts 50 x 2.43 (the 2.433 line) | 09/26-10/11 (16) | 5,321 | **FRONT-OPEN** | 32 / 18 | 22 / 0 | +12.1% |
| v4 fee 5000 ts 100 x 2.43 (the 2.433 line) | 10/11-10/12 (2) | 129 | **FRONT-OPEN** | 56 / 0 | 26 / 0 | +10.4% |
| v4 fee 8388608 ts 2 hook via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/24-08/25 (2) | 118 | **FRONT-OPEN** | 167 / 1 | 8 / 1 | +1.5% |
| v4 fee 50000 ts 200 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 09/01-09/10 (6) | 109 | **FRONT-OPEN** (seat negative after fees) | 85 / 17 | 21 / 3 | -2.1% |
| v4 fee 80000 ts 800 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 09/02-09/05 (4) | 67 | **FRONT-OPEN** (seat negative after fees) | 26 / 2 | 16 / 2 | -12.6% |
| v4 fee 60000 ts 600 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 09/02-09/05 (3) | 27 | **FRONT-OPEN** (seat negative after fees) | 13 / 7 | 4 / 1 | -7.4% |
| v4 fee 9000 ts 90 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/12-09/12 (21) | 239 | tolerant (exits, no front evidence) | 430 / 8 | 39 / 29 | +6.2% |
| v4 fee 100000 ts 1000 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/27-09/30 (17) | 225 | tolerant (exits, no front evidence) (seat negative after fees) | 62 / 6 | 47 / 23 | -11.1% |
| v4 fee 2500 ts 25 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/14-09/28 (15) | 150 | tolerant (exits, no front evidence) | 786 / 9 | 23 / 21 | +6.7% |
| v4 fee 50000 ts 500 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/26-09/08 (11) | 147 | tolerant (exits, no front evidence) | 74 / 9 | 22 / 9 | +1.5% |
| v2 fee - ts - via `0xc9271f5cb901e30a22268687a8776e6a048e0cb9` | 08/12-08/13 (2) | 38 | tolerant (exits, no front evidence) | 13 / 0 | 1 / 1 | +65.4% |
| v4 fee 8388608 ts 60 hook via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/25-09/04 (3) | 37 | tolerant (exits, no front evidence) (seat negative after fees) | 6 / 0 | 3 / 2 | -0.7% |
| v4 fee 40000 ts 400 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 09/01-09/04 (3) | 33 | tolerant (exits, no front evidence) | 19 / 2 | 4 / 2 | +2.3% |
| v4 fee 10000 ts 200 hook x 11 | 10/09-10/12 (2) | 27 | tolerant (exits, no front evidence) | 129 / 0 | 1 / 0 | +1.2% |
| v4 fee 20000 ts 200 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/27-09/03 (3) | 25 | tolerant (exits, no front evidence) | 7 / 0 | 2 / 0 | +12.3% |
| v4 fee 9000 ts 90 x 1 | 08/05-08/11 (2) | 23 | tolerant (exits, no front evidence) | 90 / 0 | 6 / 4 | +19.9% |
| v4 fee 10000 ts 200 via `0x28f73157c7e5d508e8a144892c6c4f38a8e218f5` | 10/01-10/02 (2) | 20 | tolerant (exits, no front evidence) | 16 / 3 | 0 / 0 | +59.3% |
| v4 fee 3000 ts 60 hook x 1e-18 | 08/05 (1) | 11 | tolerant (exits, no front evidence) | 62 / 0 | 2 / 0 | - |
| v4 fee 8388608 ts 2 hook x 4.06 | 08/24 (1) | 11 | tolerant (exits, no front evidence) | 17 / 0 | 2 / 1 | +3.7% |
| v4 fee 30000 ts 300 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 09/01 (1) | 9 | tolerant (exits, no front evidence) | 4 / 0 | 2 / 0 | +5.8% |
| v4 fee 100000 ts 200 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 09/01-09/13 (12) | 282 | mixed | 18 / 11 | 32 / 11 | -6.7% |
| v4 fee 150000 ts 1500 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/26-09/06 (11) | 154 | mixed | 63 / 35 | 30 / 17 | -16.9% |
| v4 fee 3000 ts 60 hook x 1e-09 | 08/12-08/13 (2) | 23 | mixed | 23 / 16 | 2 / 0 | - |
| v2 fee - ts - x 0.1 | 08/13 (1) | 19 | mixed | 1 / 0 | 1 / 0 | +128.6% |
| v4 fee 180000 ts 1800 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 09/02 (1) | 16 | mixed | 1 / 0 | 2 / 0 | -16.8% |
| v4 fee 375 ts 4 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 10/01 (1) | 13 | mixed | 0 / 0 | 1 / 0 | +10.0% |
| v4 fee 2500 ts 25 x 0.000106 | 08/26 (1) | 11 | mixed | 1 / 0 | 0 / 0 | +3.2% |
| v4 fee 375 ts 4 x 1 | 08/14 (1) | 9 | mixed | 2 / 0 | 0 / 1 | +51.3% |
| v4 fee 100000 ts 200 x 0.048 | 09/04 (1) | 9 | mixed | 1 / 0 | 2 / 0 | -2.1% |
| v4 fee 2500 ts 25 x 2 | 08/20 (1) | 8 | mixed | 1 / 0 | 0 / 0 | +10.3% |
| v4 fee 700000 ts 7000 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/29 (1) | 8 | mixed | 0 / 0 | 0 / 1 | - |
| v4 fee 300000 ts 3000 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/31 (1) | 8 | mixed | 0 / 0 | 1 / 0 | -9.0% |
| v4 fee 10000 ts 200 x 0.000106 | 08/26 (1) | 75 | untested | 0 / 0 | 0 / 0 | +1.7% |
| v3 fee 3000 ts 60 x 0.0006 | 09/28-09/29 (2) | 45 | untested | 0 / 0 | 0 / 1 | +6.7% |
| v2 fee - ts - x 0.491 | 10/05 (1) | 10 | untested | 0 / 0 | 0 / 0 | +20.1% |
| v3 fee 100 ts 1 x 0.33 | 09/30 (1) | 9 | untested | 0 / 0 | 0 / 0 | +31.0% |
| v3 fee 10000 ts 200 x 1 | 08/06-08/29 (24) | 7,788 | CLOSED | 5 / 24 | 1 / 6 | +8.0% |
| v4 fee 10000 ts 200 x 1 | 08/01-09/01 (21) | 6,744 | CLOSED | 1468 / 80 | 0 / 23 | +7.8% |
| v3 fee 10000 ts 200 via `0x73991a25c818bf1f1128deaab1492d45638de0d3` | 08/02-10/21 (25) | 296 | CLOSED | 568 / 22 | 38 / 72 | +7.8% |
| v4 fee 10000 ts 200 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/26-09/13 (9) | 211 | CLOSED | 2101 / 6 | 2 / 16 | -0.6% |
| v4 fee 3000 ts 60 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/16-09/02 (6) | 141 | CLOSED | 941 / 17 | 7 / 44 | +25.1% |
| v4 fee 10000 ts 200 hook via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/19-10/09 (8) | 100 | CLOSED | 884 / 14 | 5 / 22 | +0.3% |
| v3 fee 3000 ts 60 via `0x73991a25c818bf1f1128deaab1492d45638de0d3` | 08/06-09/05 (9) | 92 | CLOSED | 95 / 9 | 4 / 22 | +4.8% |
| v3 fee 3000 ts 60 x 1 | 08/11-09/01 (4) | 55 | CLOSED | 30 / 28 | 2 / 3 | +42.2% |
| v4 fee 75 ts 1 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/13-09/08 (4) | 45 | CLOSED | 13 / 0 | 6 / 11 | +25.5% |
| v4 fee 15000 ts 200 x 0.242 | 09/10 (1) | 44 | CLOSED | 0 / 0 | 1 / 5 | -1.6% |
| v3 fee 100 ts 1 via `0x73991a25c818bf1f1128deaab1492d45638de0d3` | 08/11-10/05 (4) | 36 | CLOSED | 5 / 0 | 0 / 8 | +89.8% |
| v4 fee 10000 ts 200 x 0.05 | 09/08-09/11 (3) | 35 | CLOSED | 1 / 1 | 0 / 6 | - |
| v4 fee 100 ts 3 hook via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/16-09/22 (3) | 26 | CLOSED | 0 / 35 | 0 / 25 | - |
| v3 fee 500 ts 10 via `0x73991a25c818bf1f1128deaab1492d45638de0d3` | 08/13-08/18 (2) | 24 | CLOSED | 0 / 0 | 1 / 3 | +9.6% |
| v4 fee 3000 ts 60 hook via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 09/19-09/22 (2) | 22 | CLOSED | 498 / 2 | 1 / 7 | +25.0% |
| v3 fee 10000 ts 200 x 0.5 | 08/11 (1) | 17 | CLOSED | 67 / 0 | 0 / 4 | - |
| v4 fee 2500 ts 25 x 1 | 08/24-09/09 (2) | 17 | CLOSED | 0 / 0 | 0 / 4 | +5.3% |
| v4 fee 100 ts 5 hook via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/25-09/22 (2) | 17 | CLOSED | 0 / 23 | 0 / 16 | - |
| v4 fee 100 ts 2 hook via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/25-09/22 (2) | 16 | CLOSED | 0 / 25 | 0 / 16 | - |
| v3 fee 100 ts 1 x 0.00189 | 09/05 (1) | 11 | CLOSED | 0 / 0 | 0 / 10 | - |
| v4 fee 8388608 ts 2 hook x 4.05 | 08/24 (1) | 10 | CLOSED | 44 / 0 | 0 / 3 | +4.9% |
| v4 fee 8388608 ts 2 hook x 4.04 | 08/24 (1) | 9 | CLOSED | 79 / 0 | 0 / 6 | - |
| v3 fee 100 ts 1 x 0.1 | 08/31 (1) | 9 | CLOSED | 22 / 0 | 1 / 7 | +11.6% |
| v4 fee 10000 ts 200 hook x 0.0181 | 08/19 (1) | 8 | CLOSED | 3 / 0 | 0 / 3 | +39.6% |
| v4 fee 3000 ts 60 x 1.01 | 09/11 (1) | 8 | CLOSED | 0 / 0 | 0 / 8 | - |
| v3 fee 10000 ts 200 x 3 | 08/16-08/18 (3) | 785 | TRAP | 0 / 5 | 0 / 0 | +3.4% |
| v4 fee 10000 ts 200 x 1.5 | 09/01-09/07 (7) | 533 | TRAP | 2 / 20 | 3 / 0 | +30.6% |
| v4 fee 10000 ts 200 x 3.5 | 09/07 (1) | 40 | TRAP | 0 / 4 | 0 / 0 | +3.5% |
| v3 fee 100 ts 1 x 0.000125 | 09/21 (1) | 29 | TRAP | 2 / 3 | 0 / 0 | +2.0% |
| v4 fee 500000 ts 5000 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/26 (1) | 10 | TRAP | 0 / 1 | 2 / 0 | -68.3% |
| v4 fee 250000 ts 2500 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 09/02 (1) | 10 | TRAP | 1 / 1 | 2 / 1 | -38.1% |
| v4 fee 0 ts 1 hook x 0.04 | 10/19 (1) | 9 | TRAP | 5 / 7 | 1 / 0 | +1.4% |
<!-- /TABLE_RH -->

**Base:**

<!-- TABLE_BASE -->
| line (venue, fee in ppm, tick spacing, launch size or route) | days | pools | verdict | real outside buys: sold / rugged | fronted pools: fleet came / none | paper seat after the fleet's 1st buy |
|---|---|---|---|---|---|---|
| v4 fee 5000 ts 100 hook x 1.53 (the 2.433 line) | 10/14-10/15 (2) | 85 | **FRONT-OPEN** | 21 / 0 | 22 / 0 | +22.1% |
| v4 fee 5000 ts 100 hook x 4.13 (the 2.433 line) | 10/14 (1) | 48 | **FRONT-OPEN** | 8 / 0 | 6 / 0 | +4.4% |
| v4 fee 5000 ts 100 hook x 2.13 (the 2.433 line) | 10/14 (1) | 20 | **FRONT-OPEN** | 5 / 0 | 5 / 0 | +13.1% |
| v3 fee 3000 ts 60 x 5 | 10/15 (1) | 9 | untested | 0 / 0 | 0 / 0 | - |
| v4 fee 3000 ts 60 via `0x7c5f5a4bbd8fd63184577525326123b519429bdc` | 09/25 (1) | 8 | untested | 0 / 0 | 0 / 0 | - |
| v4 fee 100 ts 1 x 15 | 10/04 (1) | 35 | CLOSED | 3 / 0 | 0 / 8 | - |
| v4 fee 0 ts 1 x 2.5 | 09/10-09/30 (21) | 4,399 | TRAP | 0 / 19 | 0 / 0 | +2.7% |
| v4 fee 10000 ts 200 x 1.5 | 09/10-09/16 (7) | 1,474 | TRAP | 0 / 3 | 0 / 0 | +11.3% |
| v4 fee 100 ts 1 x 0.301 | 09/10-09/19 (10) | 1,190 | TRAP | 0 / 1 | 0 / 1 | +6.7% |
<!-- /TABLE_BASE -->

Notes on the lines that are not traps or closed (none is the 2.433 kind; none is live):

- **Open at the front but not paying (Robinhood).**
  - Dynamic-fee hooked pools (Aug 24-25, 118 pools): paper seat +1.5%.
  - Three 5-8% fee lines (Sep 1-10): the fee each way makes the seat negative, -2% to -13%.
- **Tolerant for weeks, small money, not a fleet seat (Robinhood).**
  - Fee 0.9% / tick 90 (Aug 12 - Sep 12, 239 pools): D65 tried it and broke even (27 trips, 5 won). The early winners were 26 one-time
    wallets sharing +0.22 ETH over 14 days.
  - Fee 0.25% / tick 25 (Aug 14 - Sep 28, 150 pools): crowd launches. The "fleet" is 95-125 recurring wallets whose first real buy comes
    3-19 minutes after the launch. 47 one-time wallets shared +0.52 ETH; D65 made +0.22 ETH on 20 trips.
- **Robinhood, V2 micro-pairs through `0xc9271f5c` (Aug 12-13, 38 pools of 0.04-0.17 ETH):** its "outside" winners on Aug 13 are six
  wallets that each bought exactly 0.00198 ETH in the same block (+248) and sold into the same later buys. That is a coordinated bundle,
  not strangers. Gone after two days.
- **Robinhood, launcher `0x28f73157` (Oct 1-2, 20 pools):** 0.1-0.2 ETH micro-pools that a 36-wallet fleet pumps x5 to x140.
  - Nobody ever bought ahead of the fleet.
  - The late buyers were pulled on unsold: 3 rugged at +1458..+1464 blocks, with the pull at +1467.
- **Robinhood, hooked 11 ETH pools at fee 1% (Oct 9-12, 27 pools):** 129 outside buys sold, but the paper seat is +1.2%. Real buyers
  trade them, and there is no fleet pump to sell into.
- **Robinhood, the third operator's 0.3 ETH tier (Sep 16, 35 pools):** a paper seat of +194% after its fleet's third buy, but nobody
  outside ever tried it. One day only.
- **The rest** are 1-2 day lines of 8-19 pools with no outsider ever ahead of the fleet, or dust pools.
- **The 1.5 ETH fee-1% tick-200 shape was a trap on both chains, a week apart.**
  - Robinhood Sep 1-7: 533 pools, 20 of 22 real outside buys rugged.
  - Base Sep 10-16: about 250 pools a day through `0x7c5f5a4b` (the Base volume bot's launcher), outside buys of 0.001-0.37 ETH pulled
    on 1-5 blocks later.
- **Base's other new lines (Sep 10-30) were traps too.**
  - A 2.5 ETH fee-0 tick-1 line (same developer's token family): 19 of 19 rugged.
  - A 0.301 ETH fee-0.01% tick-1 line (the 0.5013 timer crew's earlier size).

## 3b. The two slower seats of late August (Robinhood), up close

`front.py` with a 5-pool minimum (`out/front5_rh_*.json`) on three of the days D65 traded them. The run for Sep 5 and Sep 7 hit its
time limit and is not shown. The block time is ~0.1 s.

| day | line | pools | fleet's first real buy | pump | pull (median) | paper seat after the fleet's 1st / 3rd buy | real outside buys: sold / rugged | fronted: fleet came / none |
|---|---|---|---|---|---|---|---|---|
| Aug 18 | third operator 1 ETH, slow mode | 13 | +64 s | x3.1 | 33 min | +8.9% / +23% | 69 / 0 | 1 / 5 |
| Aug 24 | third operator 1 ETH, slow mode | 10 | +135 s | x2.6 | 41 min | +19.9% / +114% | 137 / 0 | 1 / 2 |
| Aug 26 | third operator 1 ETH, slow mode | 12 | +115 s | x2.9 | 60 min | +19.9% / +47% | 5 / 0 | 1 / 3 |
| Aug 18 | V3 1 ETH, fee 0.3% | 7 | +31 s | x6.8 | 5 min | +64% / +92% | 11 / 0 | 1 / 4 |
| Aug 24 | V3 1 ETH, fee 0.3% | 5 | - | - | 5 min | - | 22 / 0 | 0 / 1 |
| Aug 26 | V3 1 ETH, fee 0.3% | 11 | +135 s | x1.85 | 2 min | +1.3% / +4.9% | 40 / 7 | 0 / 4 |

Both lines let real outside buys out. The V3 cluster stopped doing so on Aug 26. Their fleets mostly did not come to a pool someone bought
first, and their first real buys come a minute or two after the launch, not seconds.

What D65 did there is a different trade from ours. It bought at 1-3 s with 0.04-0.16 ETH, held 2-15 minutes and sold into the pool's
general buying.

On the 1 ETH tier its exits came between 2 minutes and 1.6 hours before the pull. On Sep 8-9 the pulls came 30-45 s after the launch
and its last trips there broke even or lost: the slow mode was ending.

Neither line exists now in that form. The 1 ETH tier has run the 10-minute burst mode since Sep 19: 47-157 pairs a day, 10.0-minute
pulls, foreign dust pulled on 9 s later (REPORT_OCT21). Its slow mode last showed on Oct 17-18 with one pair each. The V3 cluster has
launched one or two pools a week since Sep 8 (`linehist.py rh v3_1eth`, `linehist.py rh v2_1eth_op3`).

## 4. The other crew: D65

REPORT_X (Oct 11) found it fronting the 2.433 line beside us and judged it an independent front-runner. The hunt confirms it. It was
active on Robinhood from Aug 1, long before the 2.433 line existed. It fronted that line on the same days we did and made as much.
Outside it, it made real-size money only on two smaller seats in late August and on one-off crowd launches.

- **Its contracts:** two twin 752-byte routers, `0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc` (admin `0x0c628d65`) and
  `0xfd1b271f235e5230eaee9d914ccb1af495bfb758` (admin `0x04a802fe`).
- **Its collectors:** `0x544ef435`, `0xe322fc6d`, `0x488faf52`, `0xc522af57`.
- **Its recurring buyers:** `0xb4c345dc`, `0xb8c879dc`, `0x8cf143dd`, `0x7ae81404`, `0xb002e8a0`, `0xf05d0e3f`. It also ran fresh wallets
  by the hundred, and several of these wallets are now EIP-7702 delegated.

| period | where | what (from its nonces and transfers) |
|---|---|---|
| Feb-Mar 2026 | Base | collector `0x488faf52` +21k transactions, `0xe322fc6d` +12k |
| mid-May - early Jun 2026 | Base | +8k transactions. May 25 sampled: 0.00005 ETH buys sold for 0.0001 (dust) on 2,059-byte tokens, not the 2.433 template |
| Aug 2 - Sep 23 | Robinhood | sniping one-off crowd launches at 0.02-0.5 ETH: a 120 ETH V3 pool (Aug 22, +2.38 ETH); two hooked 1.1 ETH launches with 5.7-7.2 ETH of other people's buys (Aug 3, +1.97); about 2 ETH V2 launches through `0x26605f32`, `0xe9f7ab7d` and others, 1-12 ETH of crowd buying each, on 17 days (+1.76) |
| Aug 18 - Sep 15 | Robinhood | the two slower seats: the third operator's 1 ETH tier in slow mode (18 trips, 15 won, +0.58 ETH) and the V3 1 ETH cluster (Aug 24 - Sep 8, 20 trips, 20 won, +1.39 ETH) |
| Aug 13 - Oct 1 | Robinhood | real-size tries that lost: a 5 ETH fee-0.96% tick-193 line (Aug 13, 54 trips, -0.94 ETH), 10-20%-fee pools (Aug 27-30, -0.51), V2 0.5 ETH (-0.24), a 31 ETH hooked line (Oct 1, -0.46) |
| Oct 10-12 | Robinhood | **the 2.433 line: 2,171 trips, +0.77 ETH** (us over Oct 8-12: +0.61 ETH) |
| Oct 12 - now | Robinhood | 6,071 of 6,079 early trades are dust: `0x7ae81404` and, very likely the same crew, `0x68936d46` (same pools, size, timing and router; each holds 0.0325 ETH) buy 0.00002 ETH at +0.4-0.6 s and sell ~5 minutes later on the volume bot's 5 ETH pools and new 7777 tokens, 0.010-0.028 ETH a day, rising to ~700 pools a day by Oct 25; 8 small probes of 0.01-0.15 ETH (Oct 16-22, mostly tiny hooked fee-0 pools), net +0.01 ETH |
| Oct 16 - now | BNB | dust only: `0xb4c345dc` buys 0.00009 BNB through `0x12f420e5` on the operator's PancakeSwap V2 7777 pools and sells ~5 minutes later for +129% (~$0.05 a trip), +325 trades a day |

Every independent bot the hunt found besides us and D65 trades dust (median stakes 0.00001-0.0004 ETH), across every operator's pools. Examples:

- routers `0x4f881c6a`, `0x204faca1`, `0x8f1a4ba2`, `0x45ba7c11`, `0xb1000000…`;
- wallets `0x24919ef8`, `0xf7b47b17`, `0x754cbbe8`, `0xc3c81a34`, `0xf3ce52b1`.

A few of them made single real-stake snipes on the same one-off crowd launches D65 hit (`0x0f2730c4`, `0x7bcb750d`, `0xcaf681a6`,
`0xb1000000…`, `0x204faca1`). None traded any line at a real stake day after day. `0xcaf681a6`'s +5.65 ETH is a dust bot's: most of it
came from two broken V3 pools on Sep 23-24 (fee 0.01%, 0.02-0.3 ETH), where 0.001 ETH bought tokens that sold for 2-3 ETH.

The largest early profits on Robinhood belong to the lines' own machinery, which the method keeps out of the independent list:

- the tick-spacing-1 line's router `0x543282f8` (+5.53 ETH, Oct 13-20, 164 wallets on 127 pools, about one pool each);
- the 2.433 operator's own bot router `0x1cbaf24d` (+3.09 ETH on its own lines).

## 5. The same operator under other wallets

- **Its token.**
  - The 2.433 line on Robinhood: its first pools came on Sep 26, still with the volume bot's 5,274-byte 777 token. The 1,526-byte 2.433
    token (code hash `63ad5291cdef…`) took over from Sep 28: about 290-320 pools a day, 1,559 on Oct 10, the last 24 on Oct 12, then none
    through Oct 25. None from Aug 1 to Sep 25 either: of the 3,891 pulled-pool tokens of that period carrying its selector, 3,604 are
    operator A's 1,770-byte tokens.
  - On Base: 153 pools on Oct 14-15 (1.5, 2.1 and 4.1 ETH) and none from Sep 10 to Oct 25 otherwise.
  - So it has not come back to either chain with new wallets and the same token. On BNB it has been live since Oct 22 on PancakeSwap V2
    (REPORT_OCT23_SWEEP), where its buyers rug outside buys and only D65's dust survives.
- **Its developer's template.**
  - The selector `3c130d90` is in the 2.433 token, in operator A's 1,770-byte tokens on Robinhood, and in the 1,627-byte tokens of Base's
    fee-0 tick-1 lines: 1.2 ETH from Oct 12, and 2.5 ETH on Sep 10-11 through `0x9f54942b`.
  - Every one of those is a trap.
- **Its routers.** None of the 6,233 distinct launch contracts on Robinhood (122,367 pulled pools) or the 340 on Base (41,420) carries
  its router code: the byte-identical Robinhood / BNB / HyperEVM router, 20,443 B (`routers.py`, `routers.out`).

## 6. What still pays on these chains: dust only

The one front-seat trade still earning on Robinhood is the dust seat under the detectors. D65's two dust wallets make 0.010-0.028 ETH a
day ($25-70) on the volume bot's 5 ETH line and new 7777 pools. That's 0.00002 ETH in at +0.5 s, out ~5 minutes later, about +180% a trip.

It is a different trade from ours: it only works because the stake is under the detector. Five or more bots already take it. Its ceiling
is the dust size times the pool count. Listed for completeness, not proposed.

## 7. Limits

- Base before Sep 10 and Robinhood before Aug 1 were not swept. publicnode refuses older Base blocks, and Tenderly's public gateway
  (1,000 blocks a query, rate-limited) was used only for the D65 history.
- `front.py` tests a line once it has 8 pools in a day from 3+ launch wallets. A smaller or shape-shifting line is still covered by the
  round trips (anyone profiting on it shows up) but gets no verdict.
- A line nobody has fronted yet reads UNTESTED: the 2.433 line itself read UNTESTED from Sep 26 to Oct 9. The untested lines found here
  were each checked by hand (section 3). None is live now. The only one with a fleet buying within a second was a line of 0.0006 ETH dust
  pools (Sep 28-29).
- Fleet detection by recurrence fails for a fleet rotating ~100 wallets (operator A): its own whitelisted wallets look like outsiders. That
  is why the settled trap lines are labelled from the earlier reports, not re-judged.
- Robinhood has no archive state, so the D65 wallet `0x68936d46` is linked to the crew by behaviour, not by funding.
- `research/chase/rugcensus.py` slices the V3 pool address as `data[90:128]` (19 bytes), so its V3 pools never matched (fixed in
  `census.py`: `data[90:130]`).

## 8. What would find the next one

The 2.433 line was visible on the chain for 14 days (Sep 26 - Oct 9) before anyone fronted it at a real stake. A daily run of this hunt
on both chains would catch the next one in that window. Alert on any of:

- a new line that is FRONT-OPEN;
- a new line UNTESTED with a fleet buying within seconds of the launch and a paper seat of +5% or more;
- the D65 routers, dust wallets or `0xb4c345dc` going to real size anywhere (they test new lines with money);
- the 2.433 token code on any new pool.

## 9. Reproducing

```
cd research/hunt_oct26
python3 run_days.py rh 2026-08-01 2026-10-25 3        # census.py + roundtrips.py per UTC day -> out/
python3 run_days.py base 2026-09-10 2026-10-25 2
SKIP_KNOWN=1 python3 run_front.py rh 2                 # front.py per day (settled trap lines skipped)
SKIP_KNOWN=1 python3 run_front.py base 2
python3 summarize.py rh; python3 summarize.py base     # who made money at the front, by group and by line
python3 verdicts.py rh; python3 verdicts.py base       # every line's verdict
python3 bytecode.py rh out/bc_rh.json out/rh_2026*_00.json
python3 rivals_now.py; python3 rivals_timeline.py base bsc rh
python3 linehist.py rh v2_1eth_op3; python3 linehist.py rh v3_1eth   # the two slower seats of late August, day by day
python3 front.py out/rh_20260818_00.json out/front5_rh_20260818.json 5 14    # their seat test (5-pool minimum)
python3 coverage.py; python3 fill_report.py            # this report's tables and the committed *.out files
```

`out/` is not committed (about 2 GB of census and round-trip files). Every step above rebuilds it from public RPCs. The committed
`*.out`/`*.txt` files are the outputs quoted here.
