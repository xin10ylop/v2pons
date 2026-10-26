# Other front seats on Robinhood and Base, searched by outcome (Oct 26)

Asked: all the money came from the 2.433 operator, before it changed its setup (Robinhood +$1,515 over 1,267 trades Oct 8-12; Base +$588
over 87 trades Oct 14-15). Those lines are gone. Search the same two chains for other setups like it: the same people on other wallets,
or unrelated people running the same thing. Skip the lines where the operator's bots are the only buyers it lets through and any outside
buy is rugged within seconds.

**Answer: there is no other one, on either chain, in everything read: Robinhood Aug 1 - Oct 26, Base Sep 10 - Oct 26.** The search
assumed no operator, wallet, shape or size. It found every pool created and pulled, every wallet that bought in the first 20 seconds
and sold before the pull, and every line where a buy ahead of the fleet still got the fleet's buy to sell into. Only one line ever
passed: **the 2.433 operator's**, on Robinhood Sep 26 - Oct 12 and on Base Oct 14-15. Every other line is one of these:

- a trap of the kind described: real outside buys pulled on, unsold, with no fleet buy to sell into;
- closed: the fleet skips pools someone buys into first;
- a one-day, untested line that never came back.

- **The same people on other wallets: no.** The 2.433 token, byte-identical on every chain it ran, is on no pool after Oct 12 on Robinhood
  and none after Oct 15 on Base. The same developer's token family (it shares an unknown selector, `3c130d90`) is on operator A's tokens
  and on Base's fee-0 volume-bot lines. All of them are traps.
- **Unrelated people: one other crew traded the 2.433 line beside us,** the "D65" crew (`research/session_oct11/lines/REPORT_X.md`).
  - Followed from Aug 1 to today, it made money at real size only twice:
    - on the 2.433 line: +0.77 ETH, Oct 10-12;
    - on two one-off crowd launches on Aug 3: +1.97 ETH.
  - Every other line it tried at real size lost: -1.32 ETH on 13.4 ETH staked. Its worst tries were a 5 ETH line on Aug 13 (-0.94 ETH)
    and a 31 ETH hooked line on Oct 1 (-0.46 ETH).
  - Since Oct 12 it has only made dust trades: 0.00002 ETH on Robinhood, and 0.00009 BNB on the operator's BNB pools.
  - A crew that tests new lines with real money found nothing else that pays either.
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
| Robinhood | 64 (08/01 - 10/25) | 696,598 | 146,128 | 108,731 (56,503) | 137 |
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
| v2 fee - ts - via `0xc9271f5cb901e30a22268687a8776e6a048e0cb9` | 08/12-08/13 (2) | 38 | tolerant (exits, no front evidence) | 13 / 0 | 1 / 1 | +65.4% |
| v4 fee 2500 ts 25 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/14-09/28 (4) | 32 | tolerant (exits, no front evidence) | 326 / 3 | 9 / 5 | +9.4% |
| v4 fee 10000 ts 200 hook x 11 | 10/09-10/12 (2) | 27 | tolerant (exits, no front evidence) | 129 / 0 | 1 / 0 | +1.2% |
| v4 fee 10000 ts 200 via `0x28f73157c7e5d508e8a144892c6c4f38a8e218f5` | 10/01-10/02 (2) | 20 | tolerant (exits, no front evidence) | 16 / 3 | 0 / 0 | +59.3% |
| v4 fee 3000 ts 60 hook x 1e-09 | 08/12-08/13 (2) | 23 | mixed | 23 / 16 | 2 / 0 | - |
| v2 fee - ts - x 0.1 | 08/13 (1) | 19 | mixed | 1 / 0 | 1 / 0 | +128.6% |
| v4 fee 375 ts 4 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 10/01 (1) | 13 | mixed | 0 / 0 | 1 / 0 | +10.0% |
| v4 fee 375 ts 4 x 1 | 08/14 (1) | 9 | mixed | 2 / 0 | 0 / 1 | +51.3% |
| v4 fee 2500 ts 25 x 2 | 08/20 (1) | 8 | mixed | 1 / 0 | 0 / 0 | +10.3% |
| v3 fee 3000 ts 60 x 0.0006 | 09/28-09/29 (2) | 45 | untested | 0 / 0 | 0 / 1 | +6.7% |
| v2 fee - ts - x 0.491 | 10/05 (1) | 10 | untested | 0 / 0 | 0 / 0 | +20.1% |
| v3 fee 100 ts 1 x 0.33 | 09/30 (1) | 9 | untested | 0 / 0 | 0 / 0 | +31.0% |
| v4 fee 10000 ts 200 x 1 | 08/01-08/19 (14) | 5,414 | CLOSED | 1273 / 43 | 0 / 18 | +6.9% |
| v3 fee 10000 ts 200 x 1 | 08/06-08/20 (15) | 4,606 | CLOSED | 4 / 18 | 0 / 5 | +8.0% |
| v3 fee 10000 ts 200 via `0x73991a25c818bf1f1128deaab1492d45638de0d3` | 08/02-10/21 (13) | 164 | CLOSED | 171 / 9 | 20 / 20 | +8.1% |
| v4 fee 10000 ts 200 hook via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/19-10/09 (8) | 100 | CLOSED | 884 / 14 | 5 / 22 | +0.3% |
| v4 fee 9000 ts 90 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/12-08/20 (5) | 49 | CLOSED | 173 / 2 | 10 / 10 | +6.2% |
| v3 fee 3000 ts 60 x 1 | 08/11-08/12 (2) | 37 | CLOSED | 3 / 0 | 2 / 3 | +43.9% |
| v3 fee 100 ts 1 via `0x73991a25c818bf1f1128deaab1492d45638de0d3` | 08/11-10/05 (4) | 36 | CLOSED | 5 / 0 | 0 / 8 | +89.8% |
| v3 fee 500 ts 10 via `0x73991a25c818bf1f1128deaab1492d45638de0d3` | 08/13-08/18 (2) | 24 | CLOSED | 0 / 0 | 1 / 3 | +9.6% |
| v4 fee 3000 ts 60 hook via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 09/19-09/22 (2) | 22 | CLOSED | 498 / 2 | 1 / 7 | +25.0% |
| v4 fee 3000 ts 60 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/16-08/17 (2) | 18 | CLOSED | 0 / 3 | 0 / 15 | - |
| v3 fee 3000 ts 60 via `0x73991a25c818bf1f1128deaab1492d45638de0d3` | 08/06-08/14 (2) | 17 | CLOSED | 20 / 0 | 2 / 4 | +6.1% |
| v3 fee 10000 ts 200 x 0.5 | 08/11 (1) | 17 | CLOSED | 67 / 0 | 0 / 4 | - |
| v4 fee 100 ts 3 hook via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/16-09/22 (2) | 17 | CLOSED | 0 / 23 | 0 / 16 | - |
| v4 fee 75 ts 1 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 08/13 (1) | 14 | CLOSED | 0 / 0 | 0 / 7 | - |
| v4 fee 9000 ts 90 x 1 | 08/11 (1) | 10 | CLOSED | 1 / 0 | 0 / 3 | +19.4% |
| v4 fee 10000 ts 200 hook x 0.0181 | 08/19 (1) | 8 | CLOSED | 3 / 0 | 0 / 3 | +39.6% |
| v4 fee 100 ts 2 hook via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 09/22 (1) | 8 | CLOSED | 0 / 13 | 0 / 8 | - |
| v4 fee 100 ts 5 hook via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 09/22 (1) | 8 | CLOSED | 0 / 8 | 0 / 8 | - |
| v3 fee 10000 ts 200 x 3 | 08/16-08/18 (3) | 785 | TRAP | 0 / 5 | 0 / 0 | +3.4% |
| v3 fee 100 ts 1 x 0.000125 | 09/21 (1) | 29 | TRAP | 2 / 3 | 0 / 0 | +2.0% |
| v4 fee 100000 ts 1000 via `0x58daec3116aae6d93017baaea7749052e8a04fa7` | 09/21-09/30 (3) | 27 | TRAP | 0 / 1 | 8 / 6 | -11.7% |
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

Notes on the lines that were not traps or closed (none of them is the 2.433 kind; none is live):

- **Robinhood, fee 0.25% / tick spacing 25 through the PositionManager (Aug 14 - Sep 28, 4 days, 32 pools):** ordinary crowd launches,
  not a scripted line.
  - The "fleet" is 95-125 recurring wallets whose first real buy comes 3-19 minutes after launch; the pump is x1.02-1.35.
  - On Sep 27-28 the outsiders who fronted it lost money net (about -0.09 ETH).
- **Robinhood, V2 micro-pairs through `0xc9271f5c` (Aug 12-13, 38 pools of 0.04-0.17 ETH):** its "outside" winners on Aug 13 are six
  wallets that each bought exactly 0.00198 ETH in the same block (+248) and sold into the same later buys. That is a coordinated bundle,
  not strangers. No independent wallet ever tried it, and it was gone after two days.
- **Robinhood, launcher `0x28f73157` (Oct 1-2, 20 pools):** 0.1-0.2 ETH micro-pools that a 36-wallet fleet pumps x5 to x140.
  - Nobody ever bought ahead of the fleet.
  - The late buyers were pulled on unsold: 3 rugged at +1458..+1464 blocks, with the pull at +1467.
  - Gone after two days.
- **Robinhood, hooked 11 ETH pools at fee 1% (Oct 9-12, 27 pools):** 129 outside buys sold, but the paper seat is +1.2%. Real buyers
  trade them, and there is no fleet pump to sell into.
- **Robinhood, the third operator's 0.3 ETH tier (Sep 16, 35 pools; factory `0x8bceaa40`, router `0x89e5db8b`):** a paper seat of +194%
  after its fleet's third buy, but nobody outside ever tried it. This operator's other tiers pull 9-60 s after any foreign buy, sooner than
  this fleet's buys at 14-22 s. One day only.
- **The rest** are 1-2 day lines of 8-19 pools with no outsider ever ahead of the fleet, or dust pools: the 1e-9 ETH hooked pools of Aug
  12-13, where 16 outside buys were rugged.
- **Base, three new lines Sep 10-30, all traps:**
  - a 1.5 ETH fee-1% line through `0x7c5f5a4b` (the Base volume bot's launcher), about 250 pools a day, Sep 10-16: 0.001-0.37 ETH outside
    buys pulled on 1-5 blocks later;
  - a 2.5 ETH fee-0 tick-1 line (same developer's token family), Sep 10-30: 19 of 19 rugged;
  - a 0.301 ETH fee-0.01% tick-1 line (the 0.5013 timer crew's earlier size), Sep 10-19.

## 4. The other crew: D65

REPORT_X (Oct 11) found it fronting the 2.433 line beside us and judged it an independent front-runner. The hunt confirms it found the
line on its own: it fronted on the same days we did, made as much, and lost money everywhere else.

- **Its contracts:** two twin 752-byte routers, `0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc` (admin `0x0c628d65`) and
  `0xfd1b271f235e5230eaee9d914ccb1af495bfb758` (admin `0x04a802fe`).
- **Its collectors:** `0x544ef435`, `0xe322fc6d`, `0x488faf52`, `0xc522af57`.
- **Its recurring buyers:** `0xb4c345dc`, `0xb8c879dc`, `0x8cf143dd`, `0x7ae81404`, `0xb002e8a0`, `0xf05d0e3f`. It also ran fresh wallets
  by the hundred, and several of these wallets are now EIP-7702 delegated.

| period | where | what (from its nonces and transfers) |
|---|---|---|
| Feb-Mar 2026 | Base | collector `0x488faf52` +21k transactions, `0xe322fc6d` +12k |
| mid-May - early Jun 2026 | Base | +8k transactions. May 25 sampled: 0.00005 ETH buys sold for 0.0001 (dust) on 2,059-byte tokens, not the 2.433 template |
| Aug 1-9 | Robinhood | two crowd launches sniped at 0.06-0.10 ETH: +1.97 ETH (Aug 3, two hooked 1.1 ETH pools with 5.7-7.2 ETH of other people's buys) |
| Aug 10 - Oct 1 | Robinhood | real-size tries that lost: 5 ETH fee-0.96% tick-193 line (Aug 13, 54 trips, -0.94 ETH), V2 0.5 ETH (-0.21), 31 ETH hooked line (Oct 1, -0.46) |
| Oct 10-12 | Robinhood | **the 2.433 line: 2,171 trips, +0.77 ETH** (us over Oct 8-12: +0.61 ETH) |
| Oct 12 - now | Robinhood | dust only: `0x7ae81404` and, very likely the same crew, `0x68936d46` (same pools, size, timing and router; each holds 0.0325 ETH) buy 0.00002 ETH at +0.4-0.6 s and sell ~5 minutes later on the volume bot's 5 ETH pools and new 7777 tokens; 0.010-0.028 ETH a day, rising to ~700 pools a day by Oct 25 |
| Oct 16 - now | BNB | dust only: `0xb4c345dc` buys 0.00009 BNB through `0x12f420e5` on the operator's PancakeSwap V2 7777 pools and sells ~5 minutes later for +129% (~$0.05 a trip), +325 trades a day |

Every independent bot the hunt found besides us and D65 trades dust (median stakes 0.00001-0.0004 ETH), across every operator's pools. Examples:

- routers `0x4f881c6a`, `0x204faca1`, `0x8f1a4ba2`, `0x45ba7c11`, `0xb1000000…`;
- wallets `0x24919ef8`, `0xf7b47b17`, `0x754cbbe8`, `0xc3c81a34`, `0xf3ce52b1`.

Apart from a handful of single trades (`0xb1000000…` on two V2 pairs, `0x204faca1` once, `0x7bcb750d` on the Aug 3 crowd launches), none
of them traded a real stake at the front of any line, and none did it repeatedly anywhere but the 2.433 line.

## 5. The same operator under other wallets

- **Its token.**
  - The 2.433 line on Robinhood: its first pools came on Sep 26, still with the volume bot's 5,274-byte 777 token. The 1,526-byte 2.433
    token (code hash `63ad5291cdef…`) took over from Sep 28: about 290-320 pools a day, 1,559 on Oct 10, the last 24 on Oct 12, then none
    through Oct 25.
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
  were each checked by hand (section 3). None is live now, and none had a fleet that buys within seconds of the launch on a schedule.
- Fleet detection by recurrence fails for a fleet rotating ~100 wallets (operator A): its own whitelisted wallets look like outsiders. That
  is why the settled trap lines are labelled from the earlier reports, not re-judged.
- Robinhood has no archive state, so the D65 wallet `0x68936d46` is linked to the crew by behaviour, not by funding.
- `research/chase/rugcensus.py` slices the V3 pool address as `data[90:128]` (19 bytes), so its V3 pools never matched (fixed in
  `census.py`: `data[90:130]`).

## 8. What would find the next one

The 2.433 line was visible on the chain for 14 days (Sep 26 - Oct 9) before anyone fronted it at a real stake. A daily run of this hunt on both chains
would catch the next one in that window. Alert on any of:

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
python3 coverage.py
```

`out/` is not committed (about 2 GB of census and round-trip files). Every step above rebuilds it from public RPCs. The committed
`*.out`/`*.txt` files are the outputs quoted here.
