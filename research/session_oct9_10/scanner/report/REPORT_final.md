# Other operators with the volume bot's edge on Robinhood Chain (final report)

Written Oct 11, 2026 at about 04:00 UTC for the owner and the next agent.
It merges `report/REPORT_owner.md` with the corrections of `report/CRITIQUE.md`.
`report/REPORT_method.md` is a 540-byte stub that holds no method report, so the method content here comes from REPORT_owner.md sections 8 and 10 and from the critic's checks.
Where the critic and REPORT_owner.md disagreed, I opened the evidence file the critic named and decided; Appendix D lists each decision.
Every path below is relative to the scanner directory `/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/` unless it starts with `src/`, `docs/` or `research/` (the repository at `/home/user/v2pons`).
The repository holds a copy of the scanner directory at `research/session_oct9_10/scanner/`, except `report/work/` and `report/merge/`, which hold all the evidence gathered after the census.
Dollar figures use $15 = 0.0058 ETH, two pool fees and about $0.012 of gas a round trip, as every analysis did.

## 1. The answer

No independent operator on Robinhood Chain gives the volume bot's front edge at $15, in the 48-hour census to Oct 10 18:20 UTC or in the 8.6 hours after it (`report/work/headcheck3.json`, `report/work/router_scan.json`).
The one place the same edge exists is the volume bot's own 3.0 ETH line ("v3.0"), where the same router `0x1cbaf24d` buys at launch +6 to +10 in 92% of pools with minOut 0.95 of the launch quote (`skeptic_0x58daec3116aae6d93017baaea7749052e8a04f/s1_basics.json`).
A front there at 0.0058 ETH replays at +6.0% a trade, about $0.90, and about $400 a day at the census rate of 444 launches a day (`skeptic_0x58daec3116aae6d93017baaea7749052e8a04f/s4_replay.json`).
It is a conditional candidate at medium confidence, because it very likely belongs to the operator that answered v2.433 with decoys within about 6 hours (`REPORT.md`).
Since 01:57 UTC Oct 11 an outside wallet, `0x8cf143dd`, buys ahead of the v3.0 bot in 85 of 97 launches, and the pull now comes exactly 3 blocks after the bot's buy in 77 of the 83 of those pools that were pulled (`report/work/f8_fresh.json`).
That wallet also sold into the bot's buy in 56 of those pools, and the pull still came at bot+3, so a sell at bot+1 keeps a 2-block margin, the same margin front had on v2.433 live (`report/work/decoy3.json`, `report/merge/verify_decoy.txt`, HANDOFF 16.10).
The second option is a different trade: a 50-block ride on operator C-1's self-funded wash crowd, +8% to +12% a trade in replay and about $90 to $127 a day, which needs a new entry type in the engine (`skeptic_0x58daec3116aae6d93017baaea7749052e8a04f/f2276_100/a5_ride.json`, `report/work/c1/c1_fresh.json`).
Everything else that was flagged is a trap (operator C-2), negative at $15 (the small pot), thin (v5.0), or a one-off that has not recurred (the hooked launcher).
Nothing can trade until the feed access is authorized (HANDOFF 16.11).
v3.0 also needs a code change before even a dry run, because the engine's fee bound rejects every 1% launch (`src/flip_engine.py` lines 103 and 494).

What the owner decides:
- Whether to pursue authorized feed access (HANDOFF 16.11); without it none of the trades below can run, and the box stays stopped.
- If access comes: v3.0 first (the fee-bound change and the exit-counter halt in code, then the staged dry run and probes of section 3.1), C-1 second (a new entry type, section 3.2), nothing else.
- Whether the next agent should run the hourly RPC watch of section 9 meanwhile; it touches neither the box nor the feed.

## 2. The census

The census:
- Window: blocks 83,520,210 to 85,203,897, Oct 8 18:20:48 to Oct 10 18:20:47 UTC, 48 hours (`census/README.md`).
- 11,889 PoolManager `Initialize` logs, of which 6,865 are ETH-paired v4 pools (`census/README.md`).
- Every pool's events were fetched from its launch block to launch + 3,000 blocks, about 5 minutes, and all 6,865 windows are complete (`census/README.md`).
- Transactions were fetched for each pool's launch, its first 8 swaps and its first 2 pulls: 38,559 in all, none missing (`census/README.md`).
- About 1,800 RPC POSTs were made; 192 answered HTTP 429 and all recovered on retry (`census/README.md`).
- A strict launch family is keyed by launch target, selector, calldata length, fee, tick spacing and whether the hook is zero, for example `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|10000|200|true` (`census/README.md`).
- There are 1,644 strict families; 104 have 5 or more launches and hold 5,069 pools; 1,540 have 1 to 4 launches and hold 1,796 pools, 1,384 of them singletons (`census/README.md`, REPORT_owner.md section 6).
- Evidence-checked labels: 1,843 v2.433 pools, 1,436 of the volume bot's other lines, 77 operator A pools and 3,509 unlabelled (`census/README.md`).

The analysis:
- All 104 strict families with 5 or more launches were assigned to 29 analysts; 96 have a result file, and analysts 2 and 3 left only exploration scripts for their 8 families (`report/work/table.json`, `report/work/a23_missing.txt`).
- The analysts also regrouped across launch contracts, deployers and fee tiers (Appendix B).
- The analysts' ranked list has 7 entries for 6 distinct families, because the key `...|1444|500|10|true` appears twice (`REPORT.md`, "ranked").
- 5 skeptics re-derived each flagged family from the raw rows with their own code and traced its money; they judged the 6 families as 5 operators, the small pot's two fee tiers together (`REPORT.md`).
- After the census, a chain read to block 85,505,323 (02:57:50 UTC Oct 11, 8.62 hours) counted every ETH-pair launch by fingerprint (`report/work/headcheck3.json`).
- The v3.0 skeptic's fetch and replay were rerun to the head (`report/work/f7_fetch.py`, `report/work/f8_analyse.py`, `report/work/f8_fresh.json`).
- The bot's router was checked in every post-census ETH pool to block 85,513,808, about 03:12 UTC (`report/work/router_scan.json`).

What changed after the census (Oct 10 18:20 to Oct 11 02:57 UTC), from `report/work/headcheck3.json`:

| line | launches in 8.62 h | last launch (UTC) | per hour, hour by hour from 18:20 |
|---|---|---|---|
| v2.433 (2.4333 ETH, fee 0.25%) | 174 | Oct 10 19:28 | 152, 22, then 0 for 7 hours |
| v3.0 (3.0 ETH, fee 1%) | 231 | Oct 11 02:48 | 21, 28, 18, 14, 22, 16, 14, 60, 38 (the last bucket is 37 minutes) |
| v5.0 (5.0 ETH, fee 1%) | 90 | Oct 11 02:48 | 13, 10, 13, 10, 9, 12, 14, 7, 2 |
| operator C-1 (fee 100, value 0) | 30 | Oct 11 02:43 | 3, 2, 1, 1, 10, 4, 5, 3, 1 |
| operator C-2 (PM initialize, fee 500) | 46 | Oct 11 00:26 | 9, 6, 7, 9, 8, 7, then 0 |
| small pot (its two launch prices only) | 9 | Oct 11 00:17 | 4, 0, 0, 0, 1, 4, 0, 0, 0 |
| hooked one-off (code hash `f07d1c53`) | 0 | Oct 10 17:56 (in the census) | none |

- v2.433, the line the engine traded, has not launched since 19:28 UTC Oct 10, 7.5 hours of silence at 02:57 UTC (`report/work/headcheck3.json`).
- v3.0 ran at 19 launches an hour for the first 7 hours, the census rate of 444 a day (`report/work/headcheck3.json`, `s1_basics.json`).
- It then ran at about 60 an hour from 01:20 UTC, 98 launches in the last 1.62 hours (`report/work/headcheck3.json`).
- The census's busiest 6-hour slice of v3.0 held 142 launches, 23.7 an hour, so 60 an hour has no precedent in the 48 hours (`skeptic_0x58daec3116aae6d93017baaea7749052e8a04f/s4_replay.json`, "slices").
- The bot's router `0x1cbaf24d` bought within 40 blocks of launch in no post-census ETH pool other than v2.433, v3.0 and v5.0 pools, to block 85,513,808 (`report/work/router_scan.json`).
- So the bot did not move v2.433 to a new launch price or fee in that time.
- The biggest new fingerprint after the census (fee 1%, tick spacing 200, sqrtP 1908498483466244238266951834509291, 107 pools) is the 7fde822e launchpad of deployer `0x06cb3a68`, with no buy of 0.004 ETH or more and no pull in 300 blocks (`report/work/newfp.json`).
- In the v2.433 pools after the census, the decoy wallet `0xb4c345dc` (router `0xfd1b271f`) bought 0.00495 ETH ahead of the bot in 88 of 174 (`report/work/f8_fresh.json`).
- Our replayed front there was +7.7% mean, with 67 of 174 bot buys reverting (`report/work/f8_fresh.json`).

## 3. The ranked families

| rank | family | launches a day | replay a trade at $15 | $ a day at $15 | skeptic's verdict (confidence) | status at 02:57 UTC Oct 11 |
|---|---|---|---|---|---|---|
| 1 | v3.0: the volume bot's 3.0 ETH line | 444 (census); at a 456-a-day pace for the first 7 h after it; 60 an hour in the last 1.62 h | +6.0% mean, $0.90 | about $400 | candidate, conditional (medium) | launching; an outside fronter and pulls at bot+3 since 01:57 |
| 2 | operator C-1: POSM 2,276-byte launches, fee 0.01%, wash crowd router `0xd6d35b56` | 124 (48-h mean); 89 outside one 92-launch 6-h slice; 84 since | +11.5% mean, $1.73 (census); +8.1%, $1.22 (since) | about $90 to $127 | candidate, different trade (medium) | launching |
| 3 | v5.0: the volume bot's 5.0 ETH line | 217 (census), 253 (since) | +1.75% mean, $0.26 | about $57 to $66 | thin; inside the v3.0 verdict | launching |
| 4 | hooked one-off: code hash `f07d1c53`, buyer `0x9fdd8cea` | one burst of 100 in 23 minutes | +132% mean, +71% median (analyst) | $0 unless it recurs | not a candidate (medium) | no launch since Oct 10 17:56 |
| 5 | small pot: POSM 1,444-byte launches at 1.5-2.5 ETH, fee 0.01%/0.05% | about 11 (month average) | -30.1% mean when an outsider of our size holds early | about -$50 | not a candidate (high) | launched to 00:17 |
| 6 | operator C-2: PM initialize, fee 0.05%, crowd routers `0x628bd69e` and twins | 96 | -95.8% mean with its observed reaction | about -$1,379 | not a candidate (high) | launched to 00:26 |

Sources per row are in the subsections below.
The analysts' scores ranked the hooked one-off first (815) and v3.0 second (456.49) (`REPORT.md`, "ranked"); this table ranks by what each is worth to the engine now.
The small pot ranks above C-2 because it loses about $50 a day against C-2's $1,379; both are no-trade.

### 3.1 v3.0, the volume bot's 3.0 ETH line (with v5.0)

**What it is.**
- Strict key `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|10000|200|true`: 1,339 launches in 48 hours, of which 889 are v3.0, 434 are v5.0 and 16 are unrelated (`s1_basics.json`).
- The 16 unrelated launches have value 0 (15) or 1e-6 ETH (1), a different sqrtP and no bot buy (`s1_basics.json`, "v-other").
- A v3.0 launch is a PositionManager `multicall` of 1,444 bytes with value exactly 3.0 ETH, fee 1%, tick spacing 200, no hook, sqrtP 679394651928963067279918579724198 and mint liquidity 25725498245903809899643 (`s1_basics.json`).
- Every v3.0 launch comes from a distinct wallet, at nonce 3 in 458 of 889 (`s1_basics.json`).
- A v5.0 launch is the same with 5.0 ETH, sqrtP 526364174002223567019744861584709 and liquidity 33218249502344340119344 (`s1_basics.json`).
- HANDOFF section 1 already listed both as the bot's untraded families.

**Still active.**
- Yes: 235 v3.0 and 91 v5.0 launches from 18:20 Oct 10 to 02:57 Oct 11, after v2.433 stopped at 19:28 (`report/work/f8_fresh.json`).
- The 235 in 8.63 hours average 654 a day, but 98 of them came in the last 1.62 hours; the first 7 hours ran at 456 a day (`report/work/headcheck3.json`).
- The planning rate is therefore the census's 444 a day, and the planning value about $400 a day (`s4_replay.json`).

**The scheduled buyer and whose money it is.**
- The bot's router `0x1cbaf24d` buys (selector `c1120e3d`) in 889 of 889 v3.0 pools and 434 of 434 v5.0 pools in the census, and in 235 of 235 and 91 of 91 since (`s1_basics.json`, `report/work/f8_fresh.json`).
- The buy lands at +6 to +10 blocks in 819 of 889 v3.0 pools, +8 being the most common (313) (`s1_basics.json`).
- Its size is 0.0495 / 0.074 / 0.124 / 0.174 / 0.236 ETH (min / p10 / p50 / p90 / max) (`s1_basics.json`).
- Its minOut (calldata word 4) is 0.95 of the launch-state quote in every v3.0 and v5.0 pool, census and since (`s1_basics.json`, `report/work/f8_fresh.json`).
- That leaves 0.0794 to 0.0817 ETH of room ahead of the bot's buy, against 0.0154 to 0.0158 ETH at v2.433's 0.99 (`report/work/room_v3.json`).
- It buys from 110 reused wallets on v3.0 and 100 on v5.0, none shared with v2.433's 31 (`skeptic_0x58daec3116aae6d93017baaea7749052e8a04f/s5_identity.json`).
- The launch wallet pulls all the liquidity through the same router (`a0f7978d`), in 342 of 889 v3.0 pools within 3,000 blocks, never before or in the block of the bot's buy (`s1_basics.json`).
- The bot's ETH goes into a pool the operator owns and comes back to it in the pull, so our profit is the operator's own money.
- The router is a public launch-bundler: an `eth_call` of its buy from an unrelated address succeeded on live v3.0 pools (`skeptic_0x58daec3116aae6d93017baaea7749052e8a04f/s6b_router_gate_live.json`).
- Sharing the router therefore proves the tool, not the owner.
- The skeptic links v5.0 to v2.433's operator through the decoy funder `0x488faf52`, which bought directly in 16 v5.0 pools (`REPORT.md`, v3.0 verdict).

**Replayed returns and their sample.**
- Front at 0.0058 ETH (buy landing at launch +1, sell at the head of bot+1), all 889 v3.0 pools: +6.03% mean, +6.09% median, 99.2% win, 0 pulled first, 7 deadline exits at -2.07%, $0.904 a trade, $401.9 a day (`s4_replay.json`).
- A seeded random 300: +6.18% mean (`s4_replay.json`).
- Every census 6-hour slice replays between +5.6% and +6.7% (`s4_replay.json`, "slices").
- Landing at +2, or selling at bot+2, prices the same; selling at bot+3 loses 8 stakes in the census (`s4_replay.json`).
- If the pull always came at bot+3 and our sell slipped to bot+3, the replay would lose 882 of 889 stakes (`s4_replay.json`, "if_pull_at_bot+3_always_sell+3").
- The stake curve is flat: +5.97% at 0.0029 ETH, +5.93% at 0.05 ETH, +5.85% at 0.07 ETH with 1 bot buy dropped (`s4_replay.json`).
- At 0.08 ETH 343 bot buys revert, and at 0.1 ETH the mean is -1.96% (`s4_replay.json`).
- The engine caps the front stake at 0.006 ETH in code (`src/flip_engine.py` line 128).
- After the census, the skeptic's replay rerun on 235 v3.0 pools gives +6.19% mean, +6.56% median, 98.7% win, 0 bot buys dropped (`report/work/f8_fresh.json`).
- In the 85 pools with the outside fronter `0x8cf143dd` ahead of the bot it gives +6.48% mean, +7.75% median, 85 of 85 positive (`report/work/f8_fresh.json`, `report/merge/verify_f8.txt`).
- v5.0, census: +1.75% mean, +1.81% median, 87% win, $0.26 a trade, $57 a day (`REPORT.md`, v3.0 verdict).
- v5.0 since the census, 91 pools: +1.76% mean, +1.81% median, 87.9% win (`report/work/f8_fresh.json`).

**Break-even.**
- A forced exit in this 1% fee tier costs about -2.1%, against about -0.6% on v2.433 (`REPORT.md`, v3.0 verdict).
- So the trade breaks even when about 26% of trades get the real bot buy to fill (`REPORT.md`, v3.0 strongest_objection).
- On v2.433, HANDOFF 16.10 computed that our 0.0058 ETH plus the operator's two 0.00495 ETH decoys would have made the bot's buy revert in about 72% of pools, which is near that line.
- On v3.0 the same effect needs about 0.074 ETH ahead of the bot besides our stake (the 0.0794 ETH room less 0.0058, `report/work/room_v3.json`).
- The largest buy ahead of the v3.0 bot so far is 0.00495 ETH (`report/work/decoy3.json`).

**Trap evidence from the census.**
- 24 census pools had a non-operator buy ahead of the bot (21 v3.0, 3 v5.0), and the bot still bought in all 24 (`s3_outsiders.json`, `REPORT.md`).
- 23 of those 24 were pulled at bot+3 (11), bot+4 (2) or bot+8 to +11 (10) (`REPORT.md`, v3.0 verdict).
- The reaction tightened over time: the Oct 9 16:48 burst pulled at bot+8 to +10, the Oct 10 04:38 burst at bot+3 in 8 of 11 (`REPORT.md`).
- None of the three census outsiders ever sold, and all were rugged (`REPORT.md`).

**Trap evidence since 01:57 UTC Oct 11: the outside fronter `0x8cf143dd`.**
- It bought ahead of the bot in 85 of the 97 v3.0 launches from its first pool (block 85,469,936, about 01:57 UTC) to 02:57 UTC (`report/work/f8_fresh.json`, `report/merge/verify_f8.txt`).
- It buys 0.000099 ETH (16 times), 0.00099 (53), 0.00297 (10) or 0.00495 (6) through router `0x65050a9b` (selector `4d819a2a`, 580 bytes) (`report/work/decoy3.json`).
- It buys at launch +1 (13 times), +2 (58), +3 (10) or +4 to +6 (4) (`report/merge/verify_decoy2.txt`).
- It sold in 80 of its 85 pools, at launch +8 to +10 in 75 of the 80 (`report/work/decoy3.json`, `report/merge/verify_decoy2.txt`).
- Ordered against the bot's buy by block and log index, 24 sells came before the bot's buy, 18 in the bot's block after it, 32 at bot+1 and 6 later (`report/work/fresh2/events.json`, `report/merge/verify_decoy.txt`).
- The 24 sells before the bot's buy returned -1.99% each (`report/merge/verify_decoy.txt`).
- The 56 sells at or after the bot's buy returned +1.2% to +10.9%, median +7.85% (`report/merge/verify_decoy.txt`).
- So a seller into this bot's buy has existed since 01:57 UTC Oct 11.
- In the 32 pools where it sold at bot+1, our planned sell block, the pull came at bot+3 in 31 and at bot+4 in 1 (`report/merge/verify_decoy.txt`).
- In the 18 pools where it sold in the bot's own block, the pull came at bot+3 in 17 and at bot+4 in 1 (`report/merge/verify_decoy.txt`).
- In the 5 pools where it held, the pull came at bot+3 in all 5 (`report/merge/verify_decoy.txt`).
- Of the 83 pools it entered that were pulled, 77 were pulled exactly 3 blocks after the bot's buy, 4 at bot+4, 1 at bot+5 and 1 at bot+1,985 (`report/work/f8_fresh.json`).
- In the 48 v3.0 pools after 19:28 UTC without it that were pulled, every pull came at bot+21 or later (`report/work/f8_fresh.json`, `report/merge/verify_f8.txt`).
- The operator's answer to a seller is therefore observed: the same bot+3 pull it gives a holder, which a bot+1 sell survived every time by 2 blocks.
- Its sells follow the launch, not the bot: it sold before the bot's buy whenever the bot bought at +9 or later and its own sell came first (`report/merge/verify_decoy2.txt`).
- That matches HANDOFF 16.10's description of v2.433's decoys, which "sell back at +8..+11, right after the bot's buy" and sell first when the bot buys at +9 or later.
- If its sell lands ahead of ours at bot+1, our return drops by 0.07 to 0.40 points (`report/merge/order_cost.json`).
- It is an established wallet: nonce 1,671 at its first v3.0 buy, 1,937 at 03:00 UTC, 0.0188 ETH balance (`report/work/decoy3.json`).
- It was a buyer in 83 of the operator A launches counted by an earlier study (`research/session_oct9_10/origins/eras/p2_buyercnt.json`).
- Its transaction value is 0.0001 ETH where the pool receives 9.9e-05 ETH, so router `0x65050a9b` keeps 1% of each buy (`report/work/decoy3.json`).
- The C-1 and small-pot skeptics found router `0x65050a9b` used by unrelated outsiders (15 buys and 9 sells in 66 C-1 pools; rugged outsiders in small-pot pools) (`REPORT.md`).
- HANDOFF section 1 (line 96) still calls `0x65050a9b` the volume bot's own decoy router.
- Whether `0x8cf143dd` is a competing front-runner or the operator's own decoy cannot be told from public data.
- Either way, the pull now comes at bot+3 in the pools it enters.

**Fakeable exits.**
- Every exit trigger can be faked at gas cost: the router's buy is callable by anyone, and the feed shows reverting transactions (`REPORT.md`, v3.0 verdict).

**The skeptic's verdict.**
- Candidate, conditional, medium confidence: the numbers survive, the adversary is the one that answered v2.433 with decoys within about 6 hours, and the trap margin is already at bot+3 (`REPORT.md`).
- The verdict stands after the post-census read: rank 1, medium confidence, about $400 a day.
- The open question for the live probe is the 2-block margin under live feed timing, not an unknown reaction.
- On v2.433 live, 173 of 174 trades from 13:38 to 14:28 UTC Oct 10 sold one block after the bot's buy, and the one loss came from a feed block delivered a quarter of a second late (HANDOFF 16.10).

**Gated next step, with pass criteria (the skeptic's, with one addition).**
- Stage 0, now, no feed: once an hour, the same read as `report/work/f7_fetch.py` and `report/work/f8_analyse.py` (move `report/work/fresh2/` aside first, since the fetch caches the head it read and that folder is this report's evidence), logging the v3.0 bot's minOut ratio, the ETH ahead of its buy, the fronter's sells, and pull minus bot.
- Stage 1, dry run (`FRONT_DRY_RUN=1`) over at least 200 v3.0 launches: at least 98% recognised in the launch block; the bot's buy at +6 to +14 in at least 95%; minOut 0.95 of the launch quote in 100%; non-us ETH ahead of the bot 0.01 or less in at least 95%; the simulated sell block (bot+1) before the pull in 100%; replayed mean +5% or better.
- The addition to stage 1: the sell is sent in the feed block of the bot's buy in at least 99%, because the v2.433 loss of Oct 10 14:28 was a feed block a quarter of a second late (HANDOFF 16.10).
- Stage 2, live probe, 50 launches at 0.002 ETH: 0 pulled first; at least 90% sold at bot+1; the pull at least 2 blocks after our sell every time; the bot still buys in at least 95% of the pools we entered; net mean +4% or better; no fake router buys; no decoys of 0.01 ETH or more ahead.
- Stage 3: 200 trades at 0.0058 ETH with the same criteria before calling it live.
- Halts: the engine already halts front on the first pull at or before our sell (`FRONT_HALT_FILE`, `src/flip_engine.py` line 132).
- The skeptic's second halt, after 5 consecutive exits that are not the bot's buy or are deadline exits, does not exist in the engine and needs code before stage 2 (section 7.2).
- v5.0 is not worth a slot at +1.75%; log it in the same dry run only.

### 3.2 Operator C-1: a ride on a self-funded wash crowd

**What it is.**
- Strict key `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2276|100|1|true`: 245 launches in 47.4 hours (`skeptic_0x58daec3116aae6d93017baaea7749052e8a04f/f2276_100/a2_census.json`).
- That is 124 a day on average, but the 6-hour slices hold 16, 15, 25, 92, 38, 13, 8 and 38, so one slice holds 38% of the launches (`a2_census.json`).
- The other seven slices run at about 89 a day (`a2_census.json`).
- A launch is a PositionManager `multicall` of 2,276 bytes, value 0, fee 0.01%, tick spacing 1, no hook, sqrtP 792280926924313289846529216293289 in 242 of 245, range [-887272, 184216], from a fresh deployer at nonce 2 or 3 (`a2_census.json`).
- It is neither operator A nor the volume bot: no address overlaps the 152 known ones (`REPORT.md`, C-1 verdict).

**Still active.**
- Yes: 30 launches from 18:20 Oct 10 to 02:43 Oct 11, about 84 a day, close to the non-burst census rate (`report/work/c1/c1_fresh.json`).

**The scheduled buyer and whose money it is.**
- The buyer is the operator's own router `0xd6d35b56` (selector `e6cb474f`), used by at least 1,049 wallets that buy and sell with minOut 0 (`REPORT.md`, C-1 verdict).
- All 5,763 router calls the skeptic fetched carry gas limit 1,000,000 and a gas price equal to the tip, with minOut 0 in calldata word 3 (`REPORT.md`, C-1 verdict).
- In 66 fully attributed pools it made 4,072 buys for 652.7 ETH and 1,691 sells for 275.6 ETH, while outsiders bought 0.255 ETH in all (`REPORT.md`, C-1 verdict).
- The money loops: creators' pulled ETH goes through the multisend `0xf341c935` to the next launcher, which sends it to the hub `0xbae53801`, which funds the router and pays 965 crowd wallets' gas (`f2276_100/f3_money.json`, `f5_recipients.json`).
- The router held 76.5 ETH at the skeptic's last read (`REPORT.md`).
- The first router buy is not on a schedule: +4 / +68 / +116 / +204 / +501 blocks after launch (min / p10 / p50 / p90 / max) (`a2_census.json`).
- So there is nothing to front; the trade is to ride the crowd's buying after its first buy.
- One wallet, `0x97ac054b`, already rides these pools at 0.0002 ETH, for a realised +13.9% mean over 52 rides with 2 lost to pulls (`REPORT.md`, C-1 verdict).

**Replayed returns and their sample.**
- Buy at the end of the block after the first router buy (c1+1), sell 50 blocks later, census 203 plus 6 fresh pools: +11.53% mean, +5.72% median, 69.4% win, 5 stakes lost to the pull (2.4%), $1.73 a trade (`f2276_100/a5_ride.json`).
- Without the top 5% of trades the mean is +7.6% (`a5_ride.json`).
- Landing at c1+2 gives +10.5% and at c1+3 +10.0% (`a5_ride.json`).
- A 20-block hold gives +6.8% mean and a -0.1% median (`a5_ride.json`).
- A 100-block hold gives +21.9% mean with 16 stakes lost (`a5_ride.json`).
- A random entry between launch +30 and +300 with the 50-block hold gives +5.96% mean and +0.32% median, so the trigger adds something (`a5_ride.json`).
- The rerun on the 27 post-census pools with a router buy (to 02:43 UTC) gives +8.12% mean, +3.15% median, 70.4% win, 1 stake lost (`report/work/c1/c1_fresh.json`).
- At 89 launches a day, 203 of 245 with a router buy and $1.73 a trade, the census side is worth about $127 a day (`a2_census.json`, `a5_ride.json`).
- At the post-census rate, about 75 rides a day at $1.22, it is worth about $90 a day (`report/work/c1/c1_fresh.json`).
- The 48-hour mean of $175 a day leans on the one 92-launch slice and is not the planning figure.

**Trap evidence.**
- No pool was pulled before the first router buy; pulls come 40 / 84 / 376 / 1,917 blocks after it (min / p10 / p50 / p90) (`a2_census.json`).
- 6 of 15 pools with an outsider buy of 0.001 ETH or more among the first 8 swaps were pulled within 100 blocks, against 12.3% of matched controls (binomial p about 0.006) (`f2276_100/a6_trap.json`, `a7_outsiders.json`).
- Those six pulls came 60 to 86 blocks after the outsider's buy, only 10 to 36 blocks after our planned 50-block sell (`REPORT.md`, C-1 objection).
- Read swap by swap, those six look like the normal pull after the router stops buying, 40 to 105 blocks after its last buy (`REPORT.md`, C-1 verdict).
- No outsider has ever bought $15 at the trigger in these pools, so the operator's answer to our size is untested.

**The skeptic's verdict.**
- Candidate, but a different trade (a ride, not a front), medium confidence (`REPORT.md`).
- It stays rank 2 at about $90 to $127 a day.

**Gated next step, with pass criteria (the skeptic's).**
- Dry run over at least 100 triggered launches, pricing our buy at minOut 0.97 of the quote and logging two shadow exits: one at +40, and an early sell if no router buy follows within 20 blocks (`REPORT.md`, C-1 live_test).
- Dry-run pass: the engine's prices within 0.5% of the chain replay; mean +5% or better and median +2% or better after two fees and gas; at most 5% of rides with a pull at or before the planned sell; front trades lost to slot occupancy counted against it.
- Then 50 live rides at $5 (0.00195 ETH): realised mean +5% or better; at most 2 stakes lost; the delay from our buy to the pull no shorter than in the dry run; the router's buying after our buy no thinner than in the dry run.
- Only then $15.

### 3.3 The hooked one-off (code hash `f07d1c53`)

**What it is.**
- 102 pools launched through per-launch contracts with one code hash `f07d1c5394b19c29a66c743b88203c903d43913ae90ca1292462955c4cc28a57`, selector `e1e75b94`, 5,572 bytes, value 50018847145969 wei, fee 0.25%, tick spacing 25, a 937-byte hook, sqrtP 2506289003612544606728200307581467 (`REPORT.md`, verdict 1; `skeptic_CODEHASH_f07d1c5394b19c29a66c743b88203c9/rows.json`).
- 100 of the 102 were traded inside 23 minutes, 17:33:21 to 17:56:05 UTC Oct 10; the "51 a day" is that burst averaged over 48 hours (`REPORT.md`).

**Still active.**
- No launch with its fingerprint from 18:20 Oct 10 to 02:57 Oct 11 (`report/work/headcheck3.json`).

**The scheduled buyer and whose money it is.**
- One wallet, `0x9fdd8cea`, bought each pool once at +14 / +15 / +16 blocks (p10 / p50 / p90) through the Universal Router, in descending size tiers from 2.01 ETH down to 0.06 ETH (`analyse_27/results.json`, G3; `REPORT.md`).
- Its minOut was exactly 0.95 of the launch quote, leaving 0.027 to 0.039 ETH of room ahead of it (`skeptic_CODEHASH_f07d1c5394b19c29a66c743b88203c9/minout.json`).
- The launch wallet pulled every traded pool at +29 / +30 / +32, 14 to 16 blocks after the buy, and both wallets then burnt the whole token supply (`REPORT.md`).
- The 100 launch wallets held 48.54 ETH and the buyer 4.17 ETH at the skeptic's read, so this was a one-way move of about 48 ETH into fresh wallets, not a loop (`skeptic_CODEHASH_f07d1c5394b19c29a66c743b88203c9/balances_now.json`).

**Replayed returns.**
- The analyst's front replay: +132% mean, +71% median, 96% win, n 102 (`analyse_27/results.json`, G3); the skeptic did not re-run it.

**Trap evidence.**
- None observed, because no outsider ever bought (`REPORT.md`).
- The hook reads `tx.origin` and makes an external call, and whether our buy at launch +1 would pass it was never tested at launch state (`REPORT.md`).
- The chain-wide dust bot `0xe71a69f4` is absent from all 102 pools, which fits either an unrecognised launch path or a hook that blocks it (`REPORT.md`).

**The skeptic's verdict.** Not a candidate, medium confidence: a one-off (`REPORT.md`).

**Gated next step.**
- Watch only, over the RPC: the fingerprint above, the sibling family `0x6765bede` / `82a55dde`, and any launch by the 100 deployers in `skeptic_CODEHASH_f07d1c5394b19c29a66c743b88203c9/g3_raw.json`.
- Consider trading only if it shows at least 3 bursts on at least 2 days with at least 150 launches, one buyer at +12 to +20 in at least 95%, minOut at or below 0.95 of the quote, and the pull at least 12 blocks after the buy in at least 98% (`REPORT.md`).
- Then simulate our relay's buy and sell at the launch block before any stake (`REPORT.md`).

### 3.4 The small-pot operator (POSM 1,444 bytes, fee 0.01% or 0.05%)

**What it is.**
- POSM `multicall` launches of 1,444 bytes at 1.5 to 2.5 ETH with fee 0.01% (tick spacing 1) or 0.05% (tick spacing 10), no hook: 22 in the census window (17 and 5), 339 since Sep 11 (`skeptic_0x58daec3116aae6d93017baaea7749052e8a04f/f1444_100/data/c9.json`, `c8.json`).
- It launches in sessions: about 11 a day on average, none on some days, 48 on Oct 6 (`REPORT.md`).

**Still active.**
- 9 launches at its two main launch prices from 18:20 Oct 10 to 00:17 Oct 11; this match on price alone is approximate (`report/work/headcheck3.json`).

**The scheduled buyer and whose money it is.**
- A fresh dispatcher funds the launch wallet and 10 fresh crowd wallets 800 to 1,200 blocks before each launch (`REPORT.md`, small-pot verdict).
- The crowd buys 10 times through the Universal Router from about +300 (`REPORT.md`).
- After the pull the crowd returns its ETH and the pot moves to the next dispatcher (`REPORT.md`).
- The pot grew from 2.15 ETH on Sep 29 to 2.51 ETH on Oct 10 (`REPORT.md`).
- It is operator A's design with its own pot, not operator A's known addresses (`REPORT.md`).

**Replayed returns.**
- Front with the family's rule, the 17 census pools: +60.85% mean, 0 pulled first (`c9.json`).
- All 339 launches since Sep 11: +49.9% mean, 49 pulled first (`c8.json`).
- Since Oct 5, 121 launches: +32.6% mean, 21 pulled first (`c8.json`).

**Trap evidence.**
- With an outside holder of 0.002 ETH or more before the crowd (29 pools): -30.1% mean, median -100%, 15 pulled first (`REPORT.md`, small-pot verdict).
- At 11 launches a day and $15 that is about -$50 a day.
- Wallet `0x578e7a8e` bought exactly 0.005 ETH early in 24 consecutive pools on Oct 5-6: the crowd completed in 8 of the first 10, then 10 of the next 14 were pulled with no crowd buy (`f1444_100/data/c6_trap.json`).
- The operator tolerates holders of about 0.0003 ETH, and wallet `0x5e6ec144` already runs this hold at that size, about $0.40 a trade (`REPORT.md`).
- The follow variant also fails: with a mid-crowd outsider of 0.002 ETH or more, the crowd reached 10 buys in 2 of 17 cases (`REPORT.md`).

**The skeptic's verdict.** Not a candidate, high confidence: negative at $15 (`REPORT.md`).

**Gated next step.**
- None recommended.
- The skeptic's optional probe (0.0005, then 0.002, then 0.0058 ETH, stop at 2 aborts, about $45 at risk) is expected to fail at the 0.002 or 0.0058 step (`REPORT.md`).

### 3.5 Operator C-2 (PM initialize, fee 0.05%)

**What it is.**
- Strict key `0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|true`: 192 launches in 48 hours (`REPORT.md`, C-2 verdict).
- A launch is a `PoolManager.initialize` from a fresh deployer, then a POSM 1,380-byte mint by the same wallet 37 to 213 blocks later, median 41 (`REPORT.md`).

**Still active.**
- 46 launches from 18:20 Oct 10 to 00:26 Oct 11 (`report/work/headcheck3.json`).

**The scheduled buyer and whose money it is.**
- Its crowd routers `0x410499a0`, `0xebe93d2f` and `0x628bd69e` (one code) with 480 keeper wallets first buy at +68 / +72 / +82 / +110 / +231 after the mint (`REPORT.md`).
- Deployer N's pull proceeds pass through two one-use hop wallets to deployer N+1, traced to the wei twice, and a deployer funded the crowd router directly (`skeptic_0x8366a39cc670b4001a1121b8f6a443a643e409/money.json`, `hops.json`).

**Replayed returns.**
- With no reaction to our buy, a ride from +1 to +180: +7.19% mean, 97.9% win, 2 pulled, n 192 (`skeptic_0x8366a39cc670b4001a1121b8f6a443a643e409/replay.json`).
- With the operator's observed reaction applied to our buy: -95.8% mean, 96% of stakes lost, about -$1,379 a day (`reaction_ev.json`).
- Counting only the 4-to-5-block reactions, the ride is -27% (`reaction_ev.json`).

**Trap evidence.**
- 24 of 25 outside buys of 1e-4 ETH or more were followed by a pull within 166 blocks (`reaction_ev.json`).
- 8 of the 25 were followed by a pull exactly 4 blocks later: 5 in the census and 3 in the fresh set (`reaction_ev.json`, `census_delays` and `fresh_delays`).
- A known sniper, `0xe9d83e95`, buys 9.01e-5 to 9.99e-5 ETH here, just under the 1e-4 trigger, while it buys 0.00019 to 0.0005 ETH elsewhere (`REPORT.md`).

**The skeptic's verdict.** Not a candidate, high confidence: a trap; do not spend a dry-run slot on it (`REPORT.md`).

**Gated next step.**
- None.
- If the owner wants it closed with money, 20 probes at 0.00015 ETH (about $8 at risk) fail at 2 pulls within 180 blocks of our buy (`REPORT.md`).

## 4. Controls and method validity

The method is valid.
- The v2.433 front control (sell one block after the bot's buy), all 1,843 census pools: +11.86% mean, +14.01% median, 94.6% win, 0 pulled first (`analyse_10/calib.json`, `analyse_11/calib.json`, `analyse_26/results.json`).
- The same on the live window Oct 10 09:07 to 11:40 UTC, 409 pools: +13.98% mean, +16.17% median, 98.5% win (`analyse_10/calib.json`), which matches the live +14% a trade.
- The census mean is below +14% because 229 bot buys reverted on decoys ahead of them; with the bot's buy kept, the mean is +13.54% (n 1,614) (`analyse_10/calib.json`).
- 1,080 of our real relay round trips re-priced by the model: median absolute difference 3e-16, maximum 0.004, all within 0.5 points (`analyse_26/results.json`, method_calibration).
- Operator A follow control: +4.34% mean, +3.27% median, 84% win, 0 pulled first, n 75, in every analyst but one (`analyse_10/calib.json`, `analyse_26/results.json`), which matches the live +$0.12 a trade at $3.
- The one exception, `analyse_0/calib_opA.json`, has n 73 and +4.36% mean.
- Every analyst with a result file reports these controls, within 0.1 point of each other for the same exit rule (`report/work/controls_dump.txt`).
- The critic re-checked these control figures against the files and found them right (`report/CRITIQUE.md`, "What I checked and found right").
- The skeptics re-derived each flagged family's numbers from the raw rows with their own code; the v3.0 and C-1 figures above reproduce from their output files (`report/CRITIQUE.md`).
- The 97 non-flagged strict families with 1,422 pools reproduce from `census/families.json` (`report/CRITIQUE.md`).

Limits of the method:
- Every replay assumes our buy lands at launch +1 (or c1+1) and our sell at the head of its block; the census has no feed to check that ordering.
- A pull at or before our sell counts as the whole stake lost; a reaction to our own buy is only modelled where the operator's reaction to outsiders was observed (C-2, the small pot, v3.0).
- The 8 families of analysts 2 and 3 have census counts and two ride replays, not an analyst's front and follow (`report/work/a23_missing.txt`).
- `REPORT_method.md` holds no content, so this section is the method report.

## 5. The families not flagged

- All 104 strict families with 5 or more launches were assigned to an analyst (5,069 of the 6,865 pools) (`census/README.md`, `report/work/table.json`).
- 96 of them have an analyst's result file; analysts 2 and 3 left only exploration scripts for their 8 families, so this report gives census counts for those (`report/work/a23_missing.txt`).
- 97 strict families were not flagged; they hold 1,422 pools (`report/work/table.json`, `report/work/a23_missing.txt`).

Why they were not flagged, by class (the full list is in Appendix A):

| class | families | pools in 48 h | why not | source |
|---|---|---|---|---|
| the 7fde822e launchpad (27 launch contracts; deployer `0x06cb3a68` made 454 of its 490 pools; here its families with 5 or more launches) | 43 | 375 | token-only pools with no ETH in them; a real buy in at most 1 pool per family; nobody pulls; a front sells into the untouched pool at -2.06% (two 1% fees) | `analyse_25/results.json` (WIDE-7fde822e: front -2.06%, n 490), `analyse_10/results.json` |
| fee-farm pools (fee 10% to 88% a swap) | 17 | 297 | two fees exceed any move; front -24% to -98% | `analyse_23/results.json` (fee >= 10% class: -75.3%, n 167), `analyse_21/results.json` |
| no ETH at the launch price (`0xfcd18241` at three fee tiers, `0x16cf6788`, a PM 0.3% family) | 5 | 276 | a front cannot buy at launch; no real buy | `analyse_1/results.json`, `analyse_4/results.json`, `report/work/a23_missing.txt` |
| the public launchpad `0x0000ffff` | 5 | 42 | no pull, organic first buys at random times; front -0.6% to -9.2% | `analyse_19/results.json` notes |
| buyers exist but both rules lose | 27 | 432 | a real buyer but no schedule or crowd behind it; front and follow negative after fees | Appendix A |

Three near-misses worth knowing:
- `PM 6276cbbe 196B fee 500 ts 1 hooked` (23 pools) is operator C-2's hooked sibling; its follow replay is +13.3% mean but +0.8% median and 62% win (n 21) (`analyse_26/results.json` F4b).
- It uses C-2's crowd routers (`REPORT.md`, C-2 identity), so C-2's reaction of a pull after 24 of 25 outsider buys likely applies to it too, and the replay does not model that reaction.
- The relay's sell reverted in an `eth_call` on 3 of 3 hooked pools tested and on 1 hookless one, so its sellability is unproven (`analyse_26/honeypot_sim.json`).
- All POSM 2,020-byte launches (238 pools, any fee): follow +4.9% mean but -0.7% median and 23% win (n 52), front -55.4% (`analyse_27/results.json` G1).
- `POSM f7020405 196B fee 1% hooked` (59 pools, no analyst result): 18 recurring wallets buy through the Universal Router at a median +142 blocks; a ride replay gives -1.0% to -2.1% at holds of 5 to 100 blocks, hook effects not modelled (`report/work/f702_ride.json`).

Regroupings across launch contracts and fee tiers found no further candidate: the 7fde822e class (490 pools, front -2.06%), the high-fee 2,020-byte class (168 pools, -75.3%), two dust launchers of 420 and 180 pools (-3.6% and -3.7%), the bot's other sizes at fees 10001-10300 (97 pools, no ETH at the launch price), `SELECTOR:ec64ddcf` (69 pools, -8.6%) and `CODEHASH:8ce82419` (28 pools, -1.9%) (Appendix B).

The 1,540 strict families with 1 to 4 launches (1,796 pools; 1,384 of them singletons) were seen only through those regroupings (`census/README.md`).

## 6. The other DEXes and the bonding-curve factory (counted, not analysed)

From `census/other_dex.json` and the census summary:
- V2 factory `0x8bceaa40`: 3,753 pairs in 48 hours, 3,708 with WETH; created mostly by many contracts ending in ...f66 (`f752ef6c`), by `0x26605f32` and by `addLiquidityETH` callers.
- V2 factory `0x0d1ebb17`: 2,986 pairs, 2,982 with WETH, the same creators.
- V3 factory `0x1f7d7550`: 645 pools, 565 with WETH, mostly through `0x73991a25` (`multicall`, 836 bytes).
- Smaller: V3 `0xe7fef2bc` 33, V3 `0xe51960f1` 19 (mostly HYPE pairs), V2 `0xfc2e4da3` 17 (VIRTUAL pairs), V3 `0x221a6239` 10, V2 `0x43b2bf9f` 10, V2 `0x02a84c1b` 7, and about a dozen with 1 to 4 each.
- No Solidly-style factory was seen, and no v4 `Initialize` came from any address but the PoolManager.
- The bonding-curve factory `0x7ed598bc`: 4,693 creates in 48 hours (179 to 409 per 100,000 blocks), sent mostly to `0xe33e9e47` (`f85f8e41`) and to the factory itself (`a72101af`), with values 0 to 0.07 ETH.
- The v4 pools not paired with native ETH were also left out: 5,024 in the window, including 1,436 paired with USDG `0x5fc5360d` and 1,025 with WETH `0x0bd7d308` (`census/v4_other_pools.jsonl`).
- Nothing in this report says whether any of these hold a scheduled-buyer operator; the census only counted them.

## 7. What the engine needs

Nothing below can run until the feed access is authorized (HANDOFF 16.11); the box must not reconnect to the public feed.
Line numbers are those of `src/flip_engine.py` at de88eb9, the code the box was switched to (HANDOFF 11.2).

### 7.1 Settings, for v3.0 (one front family at a time)

| setting | value | code default (line) | why |
|---|---|---|---|
| `FRONT_VALUE_WEI` | 3000000000000000000 | 2433328500000000000 (127) | the v3.0 launch value; the engine arms a launch only when its value equals this (line 1141) |
| `FRONT_CALLDATA_LEN` | 1444 | 1444 (127) | unchanged |
| `FRONT_FEE` | 10000 | 2500 (144) | v3.0's fee |
| `FRONT_TICK_SPACING` | 200 | 50 (144) | v3.0's tick spacing |
| `FRONT_SQRT_P` | 679394651928963067279918579724198 | v2.433's (145) | v3.0's launch price (`s1_basics.json`) |
| `FRONT_LIQ` | 25725498245903809899643 | v2.433's (145) | v3.0's mint liquidity (`s1_basics.json`) |
| `FRONT_PIN` | 1 | 0 (143) | rejects a 3.0 ETH launch whose fee, tick spacing, sqrtP or liquidity differ (lines 502-522); the 16 value-0 or 1e-6 ETH look-alikes are never armed anyway, because of the value match |
| `FRONT_STAKE_ETH` | 0.0058 | 0.0012, capped at 0.006 in code (128) | the $15 stake; stage 2 uses 0.002 |
| `FRONT_BOT_MINOUT` | 0.95 | 0.99 (147) | the engine's revert model for the bot's buy uses it (line 1022); 0.99 is v2.433's |
| `FRONT_AHEAD_MAX_ETH` | 0.07 | 0.008 (148) | the skeptic's "skip if more than 0.07 ETH sits ahead"; the engine counts others' buys plus our stake (line 1035) |
| `FRONT_TAKE_PROFIT` | 9 | 0.01 (129) | the skeptic says turn the take-profit off for this family; the default fires on any buy behind ours that prices the sell at +1% (line 1003); 9 is the engine's convention for off (line 106) |
| `FRONT_SELL_ON_ETH` | 0 | 0 (156) | the size rule stays off; the bot's router alone triggers the sell (line 1041) |
| `FRONT_BOT_ROUTERS` | `0x1cbaf24d53fe930fce8eff149fa797d2611da149` | the same (157) | unchanged |
| `FRONT_HOLD_BLOCKS` | 18 | 18 (129) | the skeptic's deadline: send at +18, land by +20 |
| `FRONT_MAX_PER_DAY` | at least 500 | 400 (131) | v3.0 runs at 444 a day (`s1_basics.json`); HANDOFF 16.6 offered the owner `set_kv FRONT_MAX_PER_DAY 1000` |
| `FRONT_DRY_RUN` | 1 for stage 1 | 1 (126) | stage 1 is a dry run |

The fee bound:
- `front_mismatch` rejects any launch whose fee is above `FEE_MAX_PPM` (line 494), and `FEE_MAX_PPM` defaults to 9999 (line 103).
- With the settings above and the default bound, every one of the 889 census v3.0 launches returns "fee 10000" and is logged as armed with eligible false, never traded (`report/merge/fee_check.txt`, the engine's own `decode_launch`, `front_mismatch` and `front_fingerprint` run on all 889 with the settings above; `report/CRITIQUE.md`, error 2).
- With `FEE_MAX_PPM=10000`, all 889 decode, pass `front_mismatch` and show no fingerprint difference (`report/merge/fee_check.txt`).
- But `FEE_MAX_PPM=10000` also lets follow trade operator A's pools at exactly 1% (line 573), which it excludes today.
- So the clean fix is the code change in 7.2; a settings-only route is `FEE_MAX_PPM=10000`, and only while follow is not trading live.

### 7.2 Code changes

1. A front-only fee bound: `front_mismatch` (line 494) should use its own bound (for example a new `FRONT_FEE_MAX_PPM`, or skip the follow bound when the fee equals `FRONT_FEE`), so v3.0's 1% passes and follow's bound stays at 9999.
2. The skeptic's second halt: after 5 consecutive front exits that are not on the bot's buy, or are deadline exits, write `FRONT_HALT_FILE` and stop front. The engine has only the pull-first halt (line 132) and follow's near-miss halt (line 136), with no counter of exits by reason. This is needed before stage 2.
3. A test for each of the two changes above, in `tests/test_engine.py`.
4. Trading v2.433 and v3.0 together: a set of launch values, each with its own fingerprint, `FRONT_BOT_MINOUT` and room. Both would share the one position slot; only 19 of 889 v3.0 launches fell within 12 blocks of a v2.433 launch (`REPORT.md`). This is only needed if v2.433 comes back.
5. For C-1, a new entry type:
   - arm on the launch calldata: POSM, `ac9650d8`, 2,276 bytes, value 0, fee 100, tick spacing 1, no hook, sqrtP 792280926924313289846529216293289 and liquidity 100000088127620690885293, and the second fingerprint 8.351e32 / 9.487e22 (`REPORT.md`, C-1 live_test);
   - fire on the first transaction to `0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6` with selector `e6cb474f`, 484 bytes, value 0, that is a buy (word 1 the sender, word 7 zero, word 8 the armed token);
   - land at c1+1, accept +2 or +3, skip anything later; price the buy at minOut 0.97 of the quote;
   - hold 50 blocks and sell at the deadline; log the two shadow exits (+40, and an early sell if no router buy follows within 20 blocks);
   - it holds the one position slot for about 5 seconds a trade, which v3.0 at up to 60 launches an hour would also want.

## 8. What the census could not see

- No traces: hook behaviour (taxes, afterSwap deltas, sell blocks), internal ETH transfers and who funded whom were only inferred from top-level transactions and a few `eth_call` simulations.
- No receipts of reverted attempts: a front-runner whose buys revert, or a hook that blocks some buyers, leaves nothing in the logs.
- For that reason the dust bot `0xe71a69f4`'s absence from all 102 hooked one-off pools cannot be explained (`REPORT.md`).
- Who controls `0x8cf143dd`: public data cannot tell a competing front-runner from the operator's own decoy.
- A 48-hour window: an operator that launches in sessions or paused on Oct 8-10 is undercounted or missed; the small pot needed a month of logs to judge (`f1444_100/data/c8.json`).
- Daily rates from 48 hours are bursty: one 6-hour slice holds 38% of C-1's launches (`a2_census.json`), and v3.0 ran at 60 an hour for 1.6 hours after the census (`report/work/headcheck3.json`).
- Transactions for only the first 8 swaps and first 2 pulls of each pool: crowd attribution beyond that needed fresh fetches by the skeptics (`census/README.md`).
- No feed: transaction ordering inside a block, the tips, and what a sequencer feed shows before execution were not observed; every replay assumes our buy lands at launch +1 and our sell at the head of its block.
- Only native-ETH v4 pools were analysed (section 6).

So "none" here means none in this window, on v4 native-ETH pools, among families with 5 or more launches or caught by a regrouping.
What would change it: a new operator appearing (the watch in section 9), the hooked one-off recurring, a 7-day census, an analysis of the V2/V3 pairs and the bonding curve, or a feed that shows reverted attempts.

## 9. What to watch for

- v2.433 coming back: an `Initialize` with fee 2500, tick spacing 50 and sqrtP 1604517591721945638372359205383840; it once paused for 14 hours (Oct 6-7, HANDOFF 3.2).
- The bot's router `0x1cbaf24d` buying in any new family, which would be the bot under a new launch value or fee (`report/work/router_scan.py` checks it).
- On v3.0, the signs that the edge is closing:
  - the bot's minOut ratio moving from 0.95 toward 0.99, which would cut the room ahead of it from about 0.08 ETH to about 0.016 ETH (`report/work/room_v3.json`);
  - the ETH bought ahead of the bot growing toward that room (today at most 0.00495 ETH, from `0x8cf143dd`); at about 0.074 ETH besides our stake the bot's buy reverts and the trade nears its 26% break-even;
  - the pull moving from bot+3 to bot+2 or into the bot's own block, which would leave a bot+1 sell no margin;
  - `0x8cf143dd` (or a new wallet) selling at bot+1 ahead of our sell in most pools, which costs 0.07 to 0.40 points a trade (`report/merge/order_cost.json`);
  - `c1120e3d` calls to the router that are not the bot's (fake exits);
  - the bot's buy drifting later than +14;
  - the launch rate staying at 60 an hour or falling back to 19 (`report/work/headcheck3.json`).
- On C-1, the delay from an outside buy to the pull, and the router's first-buy timing.
- Any launch by the hooked one-off's 100 deployers.
- When live, the results screen's "pull after our sell" line: a cluster at 1 or 2 blocks means the margin is gone.
- The watching can run from the research side over the public RPC (`eth_getLogs`), which is not the feed that blocked the box; one read an hour of that hour's logs (about 35,000 blocks) is a handful of requests.

## 10. What HANDOFF 16.12 must change, sentence by sentence

Each item quotes the sentence or phrase in `docs/HANDOFF.md` section 16.12 and gives its replacement.

1. Heading "the volume bot's 3.0 ETH line is the one real front candidate": replace with "the volume bot's 3.0 ETH line is the one real front candidate (conditional, medium confidence)".
2. First paragraph, after "Files: `research/session_oct9_10/scanner/` (...)": add "A second pass (Oct 10 22:30 to Oct 11 04:00 UTC) read the chain to block 85,513,808 and wrote `report/work/` and `report/merge/` (the fresh v3.0 read, the outside fronter `0x8cf143dd`, the router scan, C-1 after the census, the fee-bound check and the final report `report/REPORT_final.md`); copy them into `research/session_oct9_10/scanner/report/`, since until then the post-census evidence exists only in the research container."
3. "153 families analysed, 7 flagged, 5 distinct judged": replace with "all 104 families with 5 or more launches were assigned to analysts (96 left a result file), plus regroupings across launch contracts, deployers and fee tiers; the ranked list has 7 entries for 6 distinct families (one key appears twice), judged as 5 operators (the small pot's two fee tiers together)".
4. Item 1, "the skeptic confirmed 889 v3.0 launches in 48 h (about 510 a day, still launching at 21:28 UTC, after v2.433 went silent at 19:28) and 434 v5.0 (about 270 a day)": replace with "the skeptic confirmed 889 v3.0 launches in 48 h (444 a day) and 434 v5.0 (217 a day); in the 8.62 h after the census v3.0 launched 231 more, 19 an hour for 7 hours and then 98 in the last 1.62 h, while v2.433 has not launched since 19:28 UTC Oct 10 (`report/work/headcheck3.json`)".
5. Item 1, "the stake curve is flat at +6.0% from 0.0029 to 0.075 ETH, the bot's buys start reverting at 0.08 ETH": add "; the engine caps the front stake at 0.006 ETH in code (`src/flip_engine.py` line 128)".
6. Item 1, "the 3.25 h after the census +5.83% (n 69)": add "; to 02:57 UTC Oct 11, 235 v3.0 pools replay at +6.19% mean, +6.56% median, 98.7% win (`report/work/f8_fresh.json`)".
7. Item 1, caveat (a), "and the pull came at bot+3 in the latest bursts (bot+8..10 on Oct 9), so our sell at bot+1 survives one block of slip, not two": keep, and add "; since 01:57 UTC Oct 11, 77 of the 83 pulled pools entered by the outside wallet `0x8cf143dd` were pulled at exactly bot+3, while the 48 pulled pools without it were pulled at bot+21 or later (`report/work/f8_fresh.json`)".
8. Item 1, caveat (b), "nobody has ever sold into this bot's buy (the three outsiders held and were rugged), so the operator's reaction to a seller is unobserved": replace with "from 01:57 UTC Oct 11, wallet `0x8cf143dd` bought 0.000099 to 0.00495 ETH through router `0x65050a9b` at launch +1 to +6 in 85 of 97 v3.0 launches and sold into the bot's buy in 56 of them (18 in the bot's block, 32 at bot+1, 6 later) for +1.2% to +10.9%; the operator's answer was the same bot+3 pull it gives a holder: 31 of the 32 pools where it sold at bot+1 were pulled at bot+3, 2 blocks after that sell (`report/work/decoy3.json`, `report/merge/verify_decoy.txt`)".
9. Item 1, caveat (c), "it is the operator who answered v2.433 with decoys within 6 hours, and v3.0's fresh pools have none yet": replace with "it is the operator who answered v2.433 with decoys within 6 hours; v3.0 had none until 01:57 UTC Oct 11, and since then `0x8cf143dd` buys ahead of the bot in most launches, at most 0.00495 ETH against a room of about 0.08 ETH, selling at launch +8 to +10 like v2.433's decoys; whether it is the operator's decoy or a competitor cannot be told from public data".
10. Item 1, caveat (d), "so the skeptic says turn off the take-profit and size rules for this family (the router rule alone)": add "; that is `FRONT_TAKE_PROFIT=9` (the default 0.01 fires, `src/flip_engine.py` lines 129 and 1003) and `FRONT_SELL_ON_ETH=0`".
11. Item 1, after caveat (d): add a caveat (e): "the trade breaks even when about 26% of trades get the real bot buy to fill (`REPORT.md`); on v2.433, our stake plus the two decoys would have reverted the bot's buy in about 72% of pools (16.10), and on v3.0 that needs about 0.074 ETH ahead of the bot besides our stake".
12. Item 1, "`FRONT_PIN 1` (16 value-0 look-alikes must be rejected)": replace with "`FRONT_PIN 1` (it rejects a 3.0 ETH launch whose fee, tick spacing, sqrtP or liquidity differ; the 16 look-alikes have value 0 or 1e-6 ETH and are never armed, because the engine arms only value == `FRONT_VALUE_WEI`, line 1141)".
13. Item 1, "**What the engine needs:** it takes one front family at a time: `FRONT_VALUE_WEI 3000000000000000000`, ..., skip if more than 0.07 ETH sits ahead": add "`FRONT_BOT_MINOUT 0.95` (the revert model, default 0.99), `FRONT_AHEAD_MAX_ETH 0.07`, `FRONT_TAKE_PROFIT 9`, `FRONT_STAKE_ETH 0.0058`, and a fee bound that admits 1%: with the default `FEE_MAX_PPM` 9999, `front_mismatch` (line 494) rejects all 889 census v3.0 launches as 'fee 10000'; `FEE_MAX_PPM=10000` passes them but also opens follow to operator A's 1% pools (line 573), so a front-only fee bound in code is the fix".
14. Item 1, "trading v2.433 and v3.0 together needs a code change (a set of values)": replace "(a set of values)" with "(a set of launch values, each with its own fingerprint, minOut and room)".
15. Item 1, the dry-run gates: add "non-us ETH ahead of the bot 0.01 or less in 95%+" and "the sell sent in the feed block of the bot's buy in 99%+ (the v2.433 loss of 14:28 was a feed block a quarter of a second late, 16.10)".
16. Item 1, "Halt after 5 consecutive non-bot or deadline exits (the decoy signal).": replace with "The skeptic also asks for a halt after 5 consecutive non-bot or deadline exits (the decoy signal); `src/flip_engine.py` has no such counter (only the pull-first halt, line 132, and follow's near-miss halt, line 136), so it needs code before the live probe."
17. Item 2, "245 launches in 48 h (bursty, about 45 a day after the census)": replace with "245 launches in 47.4 h (124 a day on average, but one 6-hour slice holds 92 of them and the other seven run at about 89 a day; 30 launches in the 8.7 h after the census, about 84 a day, `report/work/c1/c1_fresh.json`)".
18. Item 2, "$1.73 a trade; a random entry gives +6.0%, so the trigger adds something": add "; after the census, 27 rides replay at +8.1% mean, +3.2% median, 70% win, 1 stake lost; at 84 to 89 launches a day it is worth about $90 to $127 a day; landing at c1+2 or c1+3 gives +10.5% and +10.0%, a 20-block hold +6.8% mean with a -0.1% median, a 100-block hold +21.9% with 16 stakes lost (`a5_ride.json`)".
19. Item 2, "6 of 15 pools with an outsider buy of 0.001 ETH or more among the first swaps were pulled within 100 blocks": add "(60 to 86 blocks after the outsider's buy, only 10 to 36 blocks after our planned 50-block sell)".
20. Item 2, "Gates: a dry run of 100 triggers, then 50 rides at $5.": replace with "Gates: a dry run of 100 triggers (buy priced at minOut 0.97 of the quote; shadow exits at +40 and on no router buy within 20 blocks; the router's calls all carry gas limit 1,000,000, gas price equal to the tip and minOut 0), then 50 rides at $5."
21. Item 3, "but nothing of this shape recurred": replace with "but nothing of this shape recurred to 02:57 UTC Oct 11 (`report/work/headcheck3.json`)".
22. Item 4 (C-2), "five exactly 4 blocks after": replace with "8 of the 25 exactly 4 blocks after (5 in the census, 3 in the fresh set, `reaction_ev.json`)".
23. Item 4 (C-2): add "Its hooked sibling (`PM 6276cbbe` 196 bytes, fee 500, hooked, 23 pools, follow +13.3% mean, +0.8% median) uses the same crowd routers, so the same reaction likely applies."
24. Items 4 and 5, the order: the list says it is "ranked by what it is worth to the owner", and the small pot (about -$50 a day, -30.1% a trade with an early holder of our size) is worth more than C-2 (about -$1,379 a day with its observed reaction); swap them so the small pot is 4 and C-2 is 5. Both stay no-trade.
25. Item 5 (small pot): add "Wallet `0x5e6ec144` already runs this hold at about 0.0003 ETH (about $0.40 a trade), the size the operator tolerates; the follow variant also fails (with a mid-crowd outsider of 0.002 ETH or more, the crowd reached 10 buys in 2 of 17 cases)."
26. Closing paragraph, "So the only other place the exact edge exists is the same operator's larger line": replace with "So the only other place the exact edge exists is the same operator's larger line, a conditional candidate at medium confidence whose pull now comes at bot+3 wherever an outside wallet buys ahead of the bot".

Outside 16.12, two related lines in `docs/HANDOFF.md` should also change:
- Section 1, line 96, lists `0x65050a9b` as the volume bot's own decoy router; the C-1 and small-pot skeptics found it used by unrelated outsiders (`REPORT.md`), and it keeps 1% of each buy (0.0001 ETH sent, 9.9e-05 into the pool, `report/work/decoy3.json`), so it looks like a public trading-bot router used by the decoys among others.
- Section 16.10, line 952, "the decoys and the bot share the 0.99 x round-number sizes": add that `0x65050a9b` itself keeps 1% of every buy, so a 0.99 x round-number size marks that router, not one operator.
## Appendix A. Every analysed strict family that was not flagged

Columns: the analyst's own front and follow means (n) as reported in its result file; "pools with a buy" and "pulled" are the census's counts (`report/work/table.json`, built by `report/work/table.py`).
A follow n larger than the family's count is the analyst's wider group and is shown as "none in family".

| family (launch target, selector, calldata, fee, tick spacing, hook) | analyst dir | launches in 48 h | pools with a buy >= 0.0002 ETH | pulled by +3,000 | front mean (n) | follow mean (n) | analyst verdict | why not |
|---|---|---|---|---|---|---|---|---|
| 0xc763b179 f0e9eabf 1796B fee 10000 ts 200 hooked | analyse_1 | 143 | 76 | 0 | -9.2% (143) | -9.9% (76) | not stated | buys exist but both rules lose after two fees |
| 0xfcd18241 6fe958d8 68B fee 3000 ts 60 hooked | analyse_1 | 101 | 0 | 32 | none | none | not stated | no ETH at the launch price and no real buy |
| 0xfcd18241 6fe958d8 68B fee 10000 ts 100 hooked | analyse_1 | 83 | 0 | 33 | none | none | not stated | no ETH at the launch price and no real buy |
| POSM ac9650d8 1444B fee 883131 ts 200 no hook | analyse_1 | 76 | 0 | 0 | -98.1% (76) | none | not stated | fee-farm pool, fee 88.3131% a swap: two fees exceed any move |
| 0xfcd18241 6fe958d8 68B fee 100000 ts 200 hooked | analyse_4 | 22 | 0 | 19 | none | none | no-schedule | fee-farm pool, fee 10% a swap: two fees exceed any move |
| PM 6276cbbe 196B fee 838974 ts 9303 no hook | analyse_4 | 20 | 1 | 0 | -93.4% (20) | none | no-schedule | fee-farm pool, fee 83.8974% a swap: two fees exceed any move |
| POSM ac9650d8 1444B fee 3000 ts 60 no hook | analyse_4 | 18 | 6 | 0 | -0.4% (18) | -0.6% (6) | no-schedule | buys exist but both rules lose after two fees |
| 0x815542e8 7c33638d 769B fee 30000 ts 200 no hook | analyse_4 | 18 | 1 | 0 | -6.0% (18) | none | no-schedule | buys exist but both rules lose after two fees |
| 0x404700be 7fde822e 804B fee 10000 ts 200 no hook | analyse_6 | 15 | 0 | 0 | -2.1% (15) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xe696daf6 7fde822e 804B fee 10000 ts 200 no hook | analyse_6 | 15 | 0 | 0 | -2.1% (15) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xb4038254 7fde822e 804B fee 10000 ts 200 no hook | analyse_6 | 14 | 0 | 0 | -2.1% (14) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x0000ffff ac9650d8 1316B fee 2500 ts 25 no hook | analyse_6 | 12 | 0 | 0 | -0.7% (12) | none | not stated | public token launchpad: no pull, organic first buys (analyse_19 notes) |
| 0x31cc7dde 7fde822e 804B fee 10000 ts 200 no hook | analyse_7 | 12 | 0 | 0 | -2.1% (12) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x57689a47 7fde822e 804B fee 10000 ts 200 no hook | analyse_7 | 12 | 0 | 0 | -2.1% (12) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x9bd98b64 7fde822e 804B fee 10000 ts 200 no hook | analyse_7 | 12 | 0 | 0 | -2.1% (12) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xb6ed4932 7fde822e 804B fee 10000 ts 200 no hook | analyse_7 | 12 | 1 | 0 | -2.1% (12) | -2.7% (1) | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xcd1e2cbe 7fde822e 804B fee 10000 ts 200 no hook | analyse_8 | 12 | 0 | 0 | -2.1% (12) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x05d55239 ce5494bb 36B fee 10000 ts 200 no hook | analyse_8 | 11 | 10 | 4 | none | none | not stated | no rule priced by the analyst; my ride replay -0.2% to -1.9% at holds 5-100 (report/work/ride_0x05d55239.json) |
| 0x2b0c7775 7fde822e 804B fee 10000 ts 200 no hook | analyse_8 | 11 | 0 | 0 | -2.1% (11) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x80521fc9 7fde822e 804B fee 10000 ts 200 no hook | analyse_8 | 11 | 0 | 0 | -2.1% (11) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x0000ffff b6982b48 260B fee 2500 ts 25 no hook | analyse_9 | 10 | 0 | 0 | -0.6% (10) | none | not stated | public token launchpad: no pull, organic first buys (analyse_19 notes) |
| 0x3493ab3e 7fde822e 804B fee 10000 ts 200 no hook | analyse_9 | 10 | 0 | 0 | -2.1% (10) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xd912ed6c 7fde822e 804B fee 10000 ts 200 no hook | analyse_9 | 10 | 0 | 0 | -2.1% (10) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| create 60808060 3740B fee 2500 ts 25 no hook | analyse_9 | 10 | 10 | 0 | -0.3% (10) | -0.6% (10) | not stated | buys exist but both rules lose after two fees |
| 0x258dd351 7fde822e 804B fee 10000 ts 200 no hook | analyse_10 | 9 | 0 | 0 | -2.1% (9) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x2a53386d 3d9ab7c9 292B fee 0 ts 200 hooked | analyse_10 | 9 | 9 | 0 | -7.5% (9) | -9.1% (9) | no-schedule | buys exist but both rules lose after two fees |
| POSM ac9650d8 2020B fee 200000 ts 2000 no hook | analyse_10 | 9 | 0 | 0 | -28.2% (9) | none | no-schedule | fee-farm pool, fee 20% a swap: two fees exceed any move |
| 0x78ba8b21 7fde822e 804B fee 10000 ts 200 no hook | analyse_10 | 9 | 0 | 0 | -2.1% (9) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xa1c9c202 7fde822e 772B fee 10000 ts 200 no hook | analyse_11 | 9 | 0 | 0 | -2.1% (9) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xdf4ca4e1 7fde822e 804B fee 10000 ts 200 no hook | analyse_11 | 9 | 0 | 0 | -2.1% (9) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x0000ffff ac9650d8 1476B fee 2500 ts 25 no hook | analyse_11 | 8 | 1 | 0 | -0.6% (8) | -0.7% (1) | no-schedule | public token launchpad: no pull, organic first buys (analyse_19 notes) |
| 0x387a453d 54e231e6 1412B fee 0 ts 200 hooked | analyse_11 | 8 | 8 | 0 | -4.8% (8) | -9.2% (8) | unprofitable | buys exist but both rules lose after two fees |
| 0x575b952f 7fde822e 804B fee 10000 ts 200 no hook | analyse_12 | 8 | 0 | 0 | -2.1% (8) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x5bd1fbe7 a80ac0c2 1156B fee 0 ts 200 hooked | analyse_12 | 8 | 4 | 0 | -2.1% (8) | -2.1% (3) | not stated | buys exist but both rules lose after two fees |
| PM 6276cbbe 196B fee 3000 ts 60 no hook | analyse_12 | 8 | 5 | 0 | none | -0.5% (5) | not stated | no ETH liquidity at the launch price |
| 0xa0ce0291 617ac5de 676B fee 8388608 ts 200 hooked | analyse_12 | 8 | 0 | 0 | -3.1% (8) | none | not stated | no buy of 0.0002 ETH or more in any pool |
| 0xc97b9d2d 7fde822e 804B fee 10000 ts 200 no hook | analyse_13 | 8 | 0 | 0 | -2.1% (8) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xe181b36e a25a9a3d 868B fee 10000 ts 200 no hook | analyse_13 | 8 | 0 | 0 | -2.1% (8) | none | no-schedule | no buy of 0.0002 ETH or more in any pool |
| 0x0000ffff ac9650d8 3236B fee 2500 ts 25 no hook | analyse_13 | 7 | 7 | 0 | -9.2% (7) | -0.6% (7) | unprofitable | public token launchpad: no pull, organic first buys (analyse_19 notes) |
| 0x3493ab3e 7fde822e 772B fee 10000 ts 200 no hook | analyse_13 | 7 | 0 | 0 | -2.1% (7) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x34c0d66f f03e0011 292B fee 0 ts 200 hooked | analyse_14 | 7 | 3 | 0 | -2.6% (7) | -2.6% (2) | not stated | buys exist but both rules lose after two fees |
| 0x575b952f 7fde822e 772B fee 10000 ts 200 no hook | analyse_14 | 7 | 0 | 0 | -2.1% (7) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| POSM ac9650d8 2020B fee 500000 ts 5000 no hook | analyse_14 | 7 | 0 | 0 | -62.9% (6) | none | not stated | fee-farm pool, fee 50% a swap: two fees exceed any move |
| POSM ac9650d8 2020B fee 810000 ts 8100 no hook | analyse_14 | 7 | 0 | 1 | -91.1% (7) | none | not stated | fee-farm pool, fee 81% a swap: two fees exceed any move |
| POSM ac9650d8 2020B fee 9000 ts 90 no hook | analyse_15 | 7 | 1 | 1 | -1.6% (5) | -1.5% (1) | no-schedule | buys exist but both rules lose after two fees |
| 0xc763b179 f0e9eabf 1828B fee 10000 ts 200 hooked | analyse_15 | 7 | 4 | 0 | -14.3% (7) | -17.8% (4) | unprofitable | buys exist but both rules lose after two fees |
| 0xce4c6a28 7fde822e 804B fee 10000 ts 200 no hook | analyse_15 | 7 | 0 | 0 | -2.1% (7) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xd1e3060e 7fde822e 804B fee 10000 ts 200 no hook | analyse_15 | 7 | 0 | 0 | -2.1% (7) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xe43be69c 7fde822e 772B fee 10000 ts 200 no hook | analyse_16 | 7 | 1 | 0 | -2.1% (7) | -2.1% (1) | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xe43be69c 7fde822e 804B fee 10000 ts 200 no hook | analyse_16 | 7 | 0 | 0 | -2.1% (7) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x1756c648 7fde822e 740B fee 10000 ts 200 no hook | analyse_16 | 6 | 0 | 0 | -2.1% (6) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x1f3af76c ff734f50 1060B fee 3000 ts 60 no hook | analyse_16 | 6 | 2 | 0 | -0.7% (6) | -0.6% (3) | no-schedule | buys exist but both rules lose after two fees |
| POSM ac9650d8 1444B fee 600000 ts 6000 no hook | analyse_17 | 6 | 0 | 1 | -63.4% (6) | none | no-schedule | fee-farm pool, fee 60% a swap: two fees exceed any move |
| 0x5bd1fbe7 a80ac0c2 1284B fee 0 ts 200 hooked | analyse_17 | 6 | 5 | 0 | -5.1% (5) | -5.5% (5) | no-schedule | buys exist but both rules lose after two fees |
| 0x78ba8b21 7fde822e 772B fee 10000 ts 200 no hook | analyse_17 | 6 | 0 | 0 | -2.1% (6) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x80521fc9 7fde822e 772B fee 10000 ts 200 no hook | analyse_18 | 6 | 0 | 0 | -2.1% (6) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x815542e8 7c33638d 833B fee 30000 ts 200 no hook | analyse_18 | 6 | 0 | 0 | -6.0% (6) | -3.0% (4) | no-schedule | no buy of 0.0002 ETH or more in any pool |
| 0xcd1e2cbe 7fde822e 772B fee 10000 ts 200 no hook | analyse_18 | 6 | 0 | 0 | -2.1% (6) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xd912ed6c 7fde822e 772B fee 10000 ts 200 no hook | analyse_18 | 6 | 0 | 0 | -2.1% (6) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xdc416cab 7fde822e 804B fee 10000 ts 200 no hook | analyse_19 | 6 | 0 | 0 | -2.1% (6) | -2.5% (5) | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xe43be69c 7fde822e 740B fee 10000 ts 200 no hook | analyse_19 | 6 | 0 | 0 | -2.1% (6) | none | no-schedule | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x0000ffff ac9650d8 1508B fee 2500 ts 25 no hook | analyse_19 | 5 | 0 | 0 | -0.6% (5) | none in family | no-schedule | public token launchpad: no pull, organic first buys (analyse_19 notes) |
| 0x038ed9c7 f03e0011 292B fee 0 ts 200 hooked | analyse_19 | 5 | 0 | 0 | -2.6% (5) | -2.6% (2) | no-schedule | no buy of 0.0002 ETH or more in any pool |
| 0x1756c648 7fde822e 804B fee 10000 ts 200 no hook | analyse_20 | 5 | 0 | 0 | -2.1% (5) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x1eef016f 60956835 2980B fee 8388608 ts 8 hooked | analyse_20 | 5 | 2 | 0 | -3.0% (5) | +0.4% (2) | not stated | buys exist but both rules lose after two fees |
| 0x258dd351 7fde822e 772B fee 10000 ts 200 no hook | analyse_20 | 5 | 0 | 0 | -2.1% (5) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x2cf3de56 aad1232c 1252B fee 3000 ts 60 hooked | analyse_20 | 5 | 1 | 0 | -0.7% (5) | -0.7% (1) | not stated | buys exist but both rules lose after two fees |
| 0x458cdbed d181e93a 420B fee 0 ts 1 no hook | analyse_21 | 5 | 5 | 0 | -0.1% (5) | -0.1% (2) | no-schedule | buys exist but both rules lose after two fees |
| POSM ac9650d8 1444B fee 200000 ts 2000 no hook | analyse_21 | 5 | 2 | 1 | -24.1% (5) | -27.3% (1) | unprofitable | fee-farm pool, fee 20% a swap: two fees exceed any move |
| POSM ac9650d8 1444B fee 250000 ts 2500 no hook | analyse_21 | 5 | 1 | 1 | -27.5% (5) | -41.6% (1) | unprofitable | fee-farm pool, fee 25% a swap: two fees exceed any move |
| POSM ac9650d8 1444B fee 500000 ts 5000 no hook | analyse_21 | 5 | 0 | 1 | -60.7% (5) | none in family | unprofitable | fee-farm pool, fee 50% a swap: two fees exceed any move |
| POSM ac9650d8 1444B fee 590000 ts 60 no hook | analyse_22 | 5 | 3 | 0 | -74.9% (5) | -75.6% (3) | not stated | fee-farm pool, fee 59% a swap: two fees exceed any move |
| POSM ac9650d8 2020B fee 3000 ts 60 no hook | analyse_22 | 5 | 5 | 3 | -20.6% (5) | -20.6% (5) | not stated | buys exist but both rules lose after two fees |
| POSM ac9650d8 2020B fee 790000 ts 7900 no hook | analyse_22 | 5 | 0 | 0 | -87.7% (5) | none | not stated | fee-farm pool, fee 79% a swap: two fees exceed any move |
| POSM ac9650d8 2020B fee 800000 ts 8000 no hook | analyse_23 | 5 | 0 | 0 | -85.9% (5) | none | not stated | fee-farm pool, fee 80% a swap: two fees exceed any move |
| POSM ac9650d8 2020B fee 870000 ts 8700 no hook | analyse_23 | 5 | 0 | 0 | -93.3% (5) | none | not stated | fee-farm pool, fee 87% a swap: two fees exceed any move |
| 0x6d9ba28f aa7ec999 580B fee 0 ts 200 hooked | analyse_23 | 5 | 1 | 0 | -2.1% (5) | none | not stated | buys exist but both rules lose after two fees |
| 0x78ba8b21 7fde822e 740B fee 10000 ts 200 no hook | analyse_23 | 5 | 0 | 0 | -2.1% (5) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0x815542e8 7c33638d 833B fee 10000 ts 200 no hook | analyse_24 | 5 | 2 | 0 | -2.1% (5) | -2.1% (2) | not stated | buys exist but both rules lose after two fees |
| 0xb4038254 7fde822e 772B fee 10000 ts 200 no hook | analyse_24 | 5 | 0 | 0 | -2.1% (5) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xc97b9d2d 7fde822e 740B fee 10000 ts 200 no hook | analyse_24 | 5 | 0 | 0 | -2.1% (5) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xc97b9d2d 7fde822e 772B fee 10000 ts 200 no hook | analyse_24 | 5 | 0 | 0 | -2.1% (5) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xce4c6a28 7fde822e 836B fee 10000 ts 200 no hook | analyse_25 | 5 | 0 | 0 | -2.1% (5) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xd1e3060e 7fde822e 740B fee 10000 ts 200 no hook | analyse_25 | 5 | 0 | 0 | -2.1% (5) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xd1e3060e 7fde822e 772B fee 10000 ts 200 no hook | analyse_25 | 5 | 0 | 0 | -2.1% (5) | none | not stated | launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool |
| 0xe181b36e a25a9a3d 900B fee 10000 ts 200 no hook | analyse_25 | 5 | 0 | 0 | -2.1% (5) | none | not stated | no buy of 0.0002 ETH or more in any pool |

The eight families whose analysts (analyse_2, analyse_3) left no result file, with the census's counts (`report/work/a23_missing.txt`):

| family | analyst dir | launches in 48 h | pools with a buy >= 0.0002 ETH | first such buy, median offset | pulled by +3,000 | note |
|---|---|---|---|---|---|---|
| 0x16cf6788 4101659e 388B fee 0 ts 200 hooked | analyse_3 (no result file) | 32 | 1 | 0 | 0 | no liquidity at the launch price in 32 of 32; a real buy in 1 |
| POSM ac9650d8 2020B fee 3000 ts 60 hooked | analyse_3 (no result file) | 30 | 29 | 49 | 3 | inside analyse_27's G1 (all POSM 2,020-byte launches): front -55.4% (n 234), follow +4.9% mean, -0.7% median, 23% win (n 52) |
| POSM ac9650d8 2020B fee 600000 ts 6000 no hook | analyse_3 (no result file) | 30 | 1 | 833 | 0 | fee-farm pool, fee 60%; inside analyse_23's high-fee class (front -75.3%, n 167) |
| PM 6276cbbe 196B fee 500 ts 1 hooked | analyse_3 (no result file) | 23 | 21 | 115 | 0 | = analyse_26's F4b (operator C-2's hooked sibling, same crowd routers): follow +13.3% mean, +0.8% median, 62% win (n 21), 0 pulled by +3,000; the relay's sell reverted in an eth_call on 3 of 3 hooked pools, and on 1 hookless one, so the sellability test is inconclusive (analyse_26/honeypot_sim.json) |
| POSM f7020405 196B fee 10000 ts 200 hooked | analyse_2 (no result file) | 59 | 57 | 142 | 17 | per-pool hooks; buyers are 18 recurring wallets through the Universal Router; my ride replay -1.0% to -2.1% at holds 5-100, 0 pulled (report/work/f702_ride.json) |
| 0xfcd18241 6fe958d8 68B fee 30000 ts 200 hooked | analyse_2 (no result file) | 52 | 0 | none | 31 | no liquidity at the launch price; no real buy |
| POSM ac9650d8 1444B fee 790000 ts 60 no hook | analyse_2 (no result file) | 50 | 0 | none | 0 | fee-farm pool, fee 79%; no real buy |
| PM 6276cbbe 196B fee 836798 ts 9303 no hook | analyse_2 (no result file) | 35 | 0 | none | 0 | fee 83.7%; no real buy; inside analyse_26's F4c (front -66.5%) |

## Appendix B. Regroupings (across launch contracts, deployers or fee tiers)

| group | analyst dir | pools | front mean (n) | follow mean (n) |
|---|---|---|---|---|
| WIDE-7fde822e, the loose selector class | analyse_25 (also analyse_23 F4-WIDE, analyse_27 G4) | 490 | -2.1% (490) | -2.5% (5) |
| DEP-0x06cb3a68, all its 7fde822e launches | analyse_25 | 454 | -2.1% (454) | -2.5% (5) |
| launches through `0xce4c6a28`, `0xd1e3060e`, `0x78ba8b21`, `0xe181b36e` | analyse_25, analyse_23 | 20, 20, 20, 16 | -2.1% each | none |
| the high-fee POSM 2,020-byte class (fee 10% or more) | analyse_23 | 168 | -75.3% (167) | -46.2% (5) |
| all launches of the high-fee deployers (F1 4 wallets, `0xa5f090eb`, `0xc6641814`/`0x692f74bc`) | analyse_23 | 33, 9, 7 | -76.5%, -84.1%, -1.7% | -86.0% (1), none, -0.7% (1) |
| LAUNCHER:POSM `ac9650d8` 54,500 bytes (3 deployers, dust pools) | analyse_26 | 420 | -3.6% (420) | none |
| LAUNCHER:POSM `ac9650d8` 46,788 bytes (same 3 deployers) | analyse_26 | 180 | -3.7% (180) | none |
| LAUNCHER:PoolManager `6276cbbe` 196 bytes, all | analyse_26 | 336 | -17.8% (293) | +0.4% (222) |
| its fee 0.05% hooked part (F4b, C-2's sibling) | analyse_26 | 23 | -0.2% (23) | +13.3% mean, +0.8% median (21) |
| its remaining fees (F4c) | analyse_26 | 121 | -66.5% (78) | -18.2% (9) |
| LAUNCHER:POSM `ac9650d8` 2,020 bytes, any fee or hook (G1) | analyse_27 | 238 | -55.4% (234) | +4.9% mean, -0.7% median (52) |
| the bot's other sizes, POSM 1,444 bytes, fee 10001-10300 (G2) | analyse_27 | 97 | none: no ETH at the launch price | -2.1% (1) |
| SELECTOR:ec64ddcf, 196 bytes, fee 0, tick spacing 60, hooked | analyse_28 | 69 | -8.6% (69) | -15.2% (9) |
| CODEHASH:8ce82419, selector bc9d39fd, fee 0, hooked | analyse_28 | 28 | -1.9% (28) | -2.1% (25) |
| the small pot (opC-fee100, opC-fee500, with history) | analyse_5, analyse_22 | 17, 5, 35 | judged in 3.4 | judged in 3.4 |
| the hooked one-off (G3) | analyse_27 | 102 | judged in 3.3 | judged in 3.3 |

## Appendix C. Files

- The skeptics' full verdicts: `REPORT.md`; their scripts and outputs: `skeptic_0x58daec3116aae6d93017baaea7749052e8a04f/` (v3.0 in the root, C-1 in `f2276_100/`, the small pot in `f1444_100/`), `skeptic_0x8366a39cc670b4001a1121b8f6a443a643e409/` (C-2), `skeptic_CODEHASH_f07d1c5394b19c29a66c743b88203c9/` (the hooked one-off).
- The census: `census/README.md`, `census/load.py`, `census/families.json`, `census/other_dex.json`.
- The post-census chain read and tables, all in `report/work/`:
  - `headcheck3.py` / `headcheck3.json`: launches per family from the census head to 02:57 UTC Oct 11;
  - `f7_fetch.py`, `f8_analyse.py` / `f8_fresh.json`: copies of the v3.0 skeptic's fetch and replay run to the head, split at v2.433's last launch; the raw rows are in `fresh2/`;
  - `decoy3.py` / `decoy3.json`: the wallet `0x8cf143dd` in v3.0 pools;
  - `room_v3.py` / `room_v3.json`: the room ahead of the v3.0 bot's buy at minOut 0.95 and 0.99;
  - `router_scan.py` / `router_scan.json`: the bot's router in post-census pools (its counts are router buys, not distinct pools);
  - `newfp.py` / `newfp.json`: the new post-census launch price (the 7fde822e launchpad);
  - `c1_fresh.py` / `c1/c1_fresh.json`: C-1 after the census with the skeptic's ride replay;
  - `f702_ride.py`, `ride_family.py` / `f702_ride.json`, `ride_0x05d55239.json`: rides on two families no analyst priced;
  - `table.py` / `table.json`, `gen_appendix.py` / `appendix.md`, `a23_missing.txt`, `controls_dump.txt`: the tables of section 5 and the appendices.
- This merge's checks, all in `report/merge/`:
  - `verify_decoy.py` / `verify_decoy.txt`: `0x8cf143dd`'s sells ordered against the bot's buy, their returns, and pull minus bot by case;
  - `verify_decoy2.py` / `verify_decoy2.txt`: its buy offsets, sizes and sell offsets against the bot's offset;
  - `verify_f8.py` / `verify_f8.txt`: the 97 launches since its first pool, the 85 it entered, and the 48 pulled pools without it;
  - `order_cost.py` / `order_cost.json`: what its sell ahead of ours at bot+1 costs us;
  - `fee_check.py` / `fee_check.txt`: the engine's launch decoder and fee bound on the 889 census v3.0 launches, with `FEE_MAX_PPM` at its default and at 10000;
  - `tests_count.txt`: the engine's tests at 4dce46e and de88eb9, run from `git archive` copies in `t_4dce46e/` and `t_de88eb9/`.
- The critique this merge applied: `report/CRITIQUE.md`; its decode check of the 889 launches is `../critic_decode.py` (the scratchpad root, one level above the scanner directory).

## Appendix D. Corrections applied, and which side I took

| where | REPORT_owner.md said | the critic said | evidence opened | taken |
|---|---|---|---|---|
| 3.1, the fronter's sells | it "sells 24 of them back at +8..+10, right after the bot's buy"; "nobody has ever sold into this bot's buy" | 80 sells in 80 of 85 pools; 24 before the bot at -2.0%, 56 at or after it at +1.2% to +10.9%; pull at bot+3 after a bot+1 sell in 31 of 32 | `report/work/decoy3.json`, `report/work/fresh2/events.json`; recomputed in `report/merge/verify_decoy.txt` | the critic: reproduced exactly (median +7.85%) |
| 1 and 3, v3.0 value | about $600 a day at the post-census rate | about $400; the 654 a day rides a 1.6-hour burst | `report/work/headcheck3.json`, `s4_replay.json` slices | the critic: the first 7 post-census hours ran at 456 a day and the busiest census slice at 23.7 an hour |
| 3.1 halts | a halt after 5 consecutive non-bot or deadline exits, listed with settings | no such logic in the engine; needs code | `src/flip_engine.py` lines 132 and 136 and the exit code | the critic: no exit counter exists |
| 3.1 exit | "a take-profit high enough never to fire" | `FRONT_TAKE_PROFIT=9` | `src/flip_engine.py` lines 106, 129, 1003 | the critic |
| 3.2, C-1 value | $90 to $175 a day | $90 to $127 a day | `a2_census.json` slices, `a5_ride.json`, `report/work/c1/c1_fresh.json` | the critic: 89 a day outside the 92-launch slice matches the post-census 84 a day |
| 3.5, C-2 | 5 pulls exactly 4 blocks after an outsider | 8 of 25 | `reaction_ev.json` `census_delays` and `fresh_delays` | the critic: 5 in the census, 3 fresh |
| section 9 of REPORT_owner | "16.12 treats the 0.99 x round-number sizes as the operator's decoy signature" | that sentence is in 16.10 (line 952) | `docs/HANDOFF.md` | the critic; the correction now targets 16.10 (section 10, last item) |
| HANDOFF 16.12 fee bound | REPORT_owner: 16.12's settings trade nothing (fee 10000 above 9999) | agrees, reproduced on all 889 launches | `src/flip_engine.py` lines 103 and 494 | both; kept |
| HANDOFF 16.12 `FRONT_PIN` reason | not addressed | the 16 look-alikes are never armed (value match, line 1141) | `s1_basics.json` "v-other", `src/flip_engine.py` line 1141 | the critic |
| HANDOFF 16.12 order | REPORT_owner already ranks the small pot above C-2 | 16.12 should swap them | `reaction_ev.json`, `REPORT.md` | the critic; REPORT_owner was already right |
| HANDOFF 16.12 rates | REPORT_owner corrected v3.0's 510 a day only | v5.0's 270 is also the 3.25-hour count; 48-hour rate 217 | `s1_basics.json`, `REPORT.md` | the critic |

Omissions the critic listed, now carried: the 26% break-even (3.1), C-1's quick pulls 10 to 36 blocks after the planned sell (3.2), C-1's hold and landing variants (3.2), C-1's dry-run details and recogniser signature (3.2, 7.2), router `0x65050a9b` used by unrelated outsiders (3.1, section 10), the small pot's `0x5e6ec144` and failed follow variant (3.4), C-2's hooked sibling (5, section 10), the 0.006 ETH stake cap (3.1, 7.1), the empty REPORT_method.md (header, section 4), and the post-census evidence living only in this container (section 10, item 2).
One fact this merge adds: `0x8cf143dd`'s sells follow the launch (+8 to +10 in 75 of 80), not the bot's buy, like v2.433's decoys in HANDOFF 16.10 (`report/merge/verify_decoy2.txt`).
A second fact this merge adds: its sell ahead of ours at bot+1 costs 0.07 to 0.40 points (`report/merge/order_cost.json`).

## Appendix E. The owner's pasted output

- The paste shows `git pull` answering "Already up to date", 46 "ok" lines from `tests/test_engine.py`, and 0 "settle failed" lines in `/var/log/flip/engine.jsonl`.
- The tests of 4dce46e print 46 "ok" lines and those of de88eb9 print 51 (`report/merge/tests_count.txt`).
- So the paste is the box before the 02:50 UTC Oct 11 branch switch described in HANDOFF 11.2.
- After that switch the same test command should print 51; if it prints 46 after 02:50 UTC, the switch did not take.
- 0 "settle failed" lines agrees with HANDOFF's note that the settle crash never fired on Oct 10.
