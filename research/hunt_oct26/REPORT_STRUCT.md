# Every launch template, tested for a scripted buyer (Nov 2 evening)

**Asked:** is there another line of the 2.433's caliber on Robinhood or Base, not a copy but similar; have the searches dug enough?

**The gap in the earlier sweeps.** `front.py` tested the front seat only on pulled pools launched with 0.5+ native (C-1 launches
token-only and was missed); `allfront.py` read every pool but found lines through other traders' round trips, so a scripted buyer that
nobody fronts yet left no trace. `structlab.py` (new) reads every pool the census saw created, groups them by their launch (target,
selector, calldata length, value; v4 fee, tick spacing, hook), and for each group measures the first big buy (0.02+ native: offset, size,
contract, senders), the front ride (buy at launch + 2, sell after that buy), the behind ride (buy at that buy + 2, hold 20 / 100), whether
the big buy still comes when an outsider bought ahead, and swap-rewriting hooks. It found every known line again, told nothing.

| chain | window | pools | groups (10+ pools) | output |
|---|---|---|---|---|
| Robinhood | Oct 30 - Nov 2 | 14,812 | 407 | `structlab_rh.out` |
| Base | Oct 31 - Nov 2 | 7,996 | 202 | `structlab_base.out` |

**Answer: no new line of the 2.433's caliber.** Every group with a large paper result is a known line that punishes outsiders, a
honeypot hook, or small:

| group | a day | paper | why not |
|---|---|---|---|
| RH 2.433 operator's 3.0 ETH line (POSM 1,444 B, fee 1%) | 380 | front -5.3%; behind its bot +6.8% (h100) | `slot30_rh.out` (SLOT=300 MIN_OUT=0.0001): in all 10 pools where an outsider bought after the bot (0.0001 ETH and up), the pull came 6-20 blocks after that buy (no outsider: a median 610 blocks after the bot's). Closed |
| RH third operator's V2 50.1 / 40.6 ETH | 130 | front +1.0-1.3% | pulls 13-60 s after any outside buy (REPORT_OCT20). Closed |
| RH third operator's V2 1 ETH | 79 | front +11.8% | the big buy never came in 4 of 4 fronted pools. Closed |
| Base 0.501 ETH timer line (v4 2,180 B) | 118 | front +105% | the big buy never came in 6 of 6 fronted pools (REPORT_NOV2: TRAP) |
| Base V2 crew 1.2 / 1.5 / 1.6 / 15 ETH | 30 each | front +0.4 to +9.5% | 1.6: 0 of 45 fronted pools got the big buy; the crew reacted to our own buys in October |
| RH 2,020 B crowd, Base launchpads | - | - | hooks that may rewrite swaps (sells may fail): never traded |
| RH launchpad `0x7891ea88` | 80 | front +4.9% | its buyer comes at +29 s with 0.02 ETH: about 0.0004 ETH a trade at $13 |

**Lines that pay, as before:** C-1 (behind its router, 92 a day, now quiet 50 cap 200: +21.4% a trade on 7 days, `c1exit_168h.out`)
and the V3 crowd (behind its routers, about 48 pumped a day, take-profit +9%: +8.5%, `crowd_v3_836_fix.out`).

**Small untested leads (self-buy lines).** The launch wallet buys its own pool 25-40 s after the launch with 0.1-0.2 ETH, then pulls:
Robinhood V2 (launch contract `0xbbf5c604`, 3,940 B, about 0.17 ETH of launch liquidity, 9 a day) and Robinhood v4 fee 0 (POSM 1,572 B,
tick spacing 200, about 7 launch wallets, 10 a day). The front seat would take most of that buy (paper +56% to +1,000% at 0.005 ETH, the
pools are thin), but nobody has ever bought ahead (the reaction is unknown), the profit per pool is bounded by the launcher's 0.1-0.2 ETH,
a pull before the sell takes everything, and each needs engine work (a V2 path on Robinhood; a v4 front family keyed by its launch length,
since value 0 is C-1's). A $5 probe would answer the reaction question; not built.
