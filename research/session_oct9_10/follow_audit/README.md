# follow_audit: operator A on Oct 10, from the chain (HANDOFF 12.4, "follow is not moving")

Written Oct 10 ~13:15 UTC from this repository's container. Scripts import `../chain.py` by absolute path (`/home/user/v2pons/...`).

| file | what |
|---|---|
| `opA_day.py` -> `opA_day.json` | every ETH-paired v4 pool initialized Oct 10 00:00 UTC -> 13:07 (1,0xx pools) grouped into launch families by (to, selector, calldata length, value, fee, tick spacing); operator A's launches (to == its launcher `0x3194e326`, or the `2fcb9108` call of a per-launch copy) with their crowd and pull |
| `opA_launches.py` -> `opA_launches.json` | the same for 10:00 UTC -> head only (found none: the operator had stopped) |
| `opA_detail.py` | the five launches' buys, pulls and our own trades (needs `opA_day.json`) |

Findings:

- **Operator A launched 5 pools on Oct 10** (06:48:50, 09:15:42, 09:18:01, 09:21:56, 09:56:25 UTC), all through its original launcher, fees
  0.032-0.5%, tick spacing 200, no hook; **none after 09:56 UTC** (3 hours by the time of writing). Follow traded all five (the day's 5 follow
  trades: +4.8%, +16.4%, -0.3%, -0.1%, +1.3%). "Follow is not moving" because the operator is not launching; `results.py`'s "launches seen …
  follow 24" counts the whole 24-hour window.
- The crowd's first real buy came at launch + 21, + 40, + 50, + 61, + 44; our buy one block after each; the pulls at launch + 9434 (!), + 46
  (5 blocks after our buy, 3 after our sell), + 56 (5 after our buy), none within the scan, + 110186 (!). Two of the five pools (06:48 and
  09:56) ran a full crowd session (166 buys / 7.3 ETH and 126 buys / 3.5 ETH) and were pulled 16 minutes and 3 hours later: the money loop's
  pots, not the quick launches.
- Launch families on the chain today besides operator A and the volume bot (296 v2.433 launches 10:00-13:07 alone, about 100 an hour): the
  volume bot's 9.333 ETH (fees 10111-10114) and 40 ETH (fees 10222-10223) families, several zero-value launchers (`7fde822e`, `7c33638d`,
  `6276cbbe` direct to the PoolManager) with 1% fees, and dozens of one-offs; none with the follow pattern (see HANDOFF 6.5).
