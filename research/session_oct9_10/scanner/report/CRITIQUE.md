# Critique of REPORT_owner.md, REPORT_method.md and HANDOFF 16.12

Written Oct 11, 2026 by the critic.
Paths are relative to the scanner directory `/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/` unless they start with `src/` or `docs/` (the repository at `/home/user/v2pons`).
Recomputations below used the census rows through `census/load.py`, the fresh rows in `report/work/fresh2/`, and `src/flip_engine.py` imported read-only.
My scripts are `../critic_decode.py` (the engine's decoder on census launches) and inline `python3 -I` reads of the JSON files named.

## Summary

- The ranking survives: v3.0 first, C-1 second, nothing else tradeable.
- REPORT_owner.md misreads its own `report/work/decoy3.json`: someone has now sold into the v3.0 bot's buy in 56 pools, and the operator's answer is visible.
- REPORT_owner.md's "$600 a day" for v3.0 rests on a 1.6-hour burst; the steady figure is about $400.
- Both documents list a "5 consecutive non-bot or deadline exits" halt that `src/flip_engine.py` does not have.
- REPORT_owner.md's fee-bound finding against HANDOFF 16.12 is correct, and I reproduced it on all 889 census v3.0 launches.
- REPORT_method.md holds no method report.

## Errors

### 1. REPORT_owner.md 4.1, lines 99 and 101: the 0x8cf143dd sells (high)

The report says `0x8cf143dd` "sells 24 of them back at +8..+10, right after the bot's buy" and, two lines above, that "nobody has ever sold into this bot's buy, so the operator's answer to a seller is unobserved".
`report/work/decoy3.json` holds 80 sells by `0x8cf143dd`, one in each of 80 of its 85 v3.0 pools, at launch +8 to +14.
The 24 is `report/work/f8_fresh.json`'s count of its sells that came before the bot's buy (its `pre_bot_traders` list only holds swaps ahead of the bot).
Ordered against the bot's buy by block and log index in `report/work/fresh2/events.json`: 24 sells before the bot's buy, 18 in the bot's block after it, 32 at bot+1, 6 later.
The 24 sells before the bot returned -2.0% each (sell ETH over buy ETH, `decoy3.json`).
The 56 sells at or after the bot's buy returned +1.2% to +10.9%, median +7.8% (`decoy3.json`).
So a seller into this bot's buy has existed since 01:57 UTC Oct 11, at 0.000099 to 0.00495 ETH.
In the 32 pools where it sold at bot+1, our planned sell block, the pull came at bot+3 in 31 and bot+4 in 1 (`fresh2/events.json`).
In the 18 pools where it sold in the bot's own block, the pull came at bot+3 in 17 and bot+4 in 1.
In the 5 pools where it held, the pull came at bot+3 in all 5.
The operator's answer to a seller is therefore observed: the same bot+3 pull it gives a holder, which a bot+1 sell survived every time by 2 blocks.
That makes the open question for stage 2 the 2-block margin under live feed timing (the v2.433 loss of Oct 10 14:28 in HANDOFF 16.10), not an unknown reaction.

### 2. HANDOFF 16.12, "What the engine needs": the fee bound (high)

The settings given would not trade a single v3.0 launch.
I ran `decode_launch`, `front_mismatch` and `front_fingerprint` from `src/flip_engine.py` on the 889 census v3.0 launch transactions with 16.12's `FRONT_FEE`, `FRONT_TICK_SPACING`, `FRONT_SQRT_P` and `FRONT_LIQ`.
With the default `FEE_MAX_PPM` 9999 (`src/flip_engine.py` line 103), all 889 return "fee 10000" from `front_mismatch` (line 494).
With `FEE_MAX_PPM=10000`, all 889 decode, pass `front_mismatch`, and show no fingerprint difference.
REPORT_owner.md section 9 states this correctly; HANDOFF 16.12 still lacks it.

### 3. HANDOFF 16.12, caveats (b) and (c): superseded by the chain since 01:57 UTC (medium)

16.12 says nobody has ever sold into this bot's buy, and that v3.0's fresh pools have no decoys yet.
From 01:57 UTC Oct 11, `0x8cf143dd` bought ahead of the bot in 85 of 97 v3.0 launches (`report/work/f8_fresh.json`, recomputed from its rows).
It sold into the bot's buy in 56 of them (error 1).
77 of the 83 of those pools that were pulled were pulled at exactly bot+3 (`f8_fresh.json`).
The 48 post-19:28 v3.0 pools without it that were pulled were all pulled at bot+21 or later (`f8_fresh.json`).
None of this is in the repository: `research/session_oct9_10/scanner/report/` holds only the headcheck files, and the evidence lives in this container's `report/work/`.

### 4. REPORT_owner.md sections 1 and 3: v3.0 "about $600 a day at the rate since the census" is a burst (medium)

`report/work/headcheck3.json` gives v3.0 launches per hour from 18:20 UTC: 21, 28, 18, 14, 22, 16, 14, 60, 38 (the last bucket 37 minutes).
The first 7 hours hold 133 launches, 19 an hour or 456 a day, the same as the census's 444 a day (`skeptic_0x58daec3116aae6d93017baaea7749052e8a04f/s1_basics.json`, 889 in 48 hours).
The 654 a day comes from 98 launches in the last 1.62 hours.
The census's busiest 6-hour slice held 142 v3.0 launches, 23.7 an hour (census rows), so 60 an hour has no precedent in the 48 hours.
That burst began at 01:20 UTC and overlaps the fronter's arrival at 01:57.
The figure to plan on is about $400 a day (`s4_replay.json`, $0.904 a trade at 444 a day).

### 5. REPORT_owner.md 4.1 "Halts" and HANDOFF 16.12 gates: the 5-exit halt is not in the engine (medium)

Both list a halt after 5 consecutive exits that are not the bot's buy, or are deadline exits.
`src/flip_engine.py` has the front pull-first halt (`FRONT_HALT_FILE`, line 132) and follow's near-miss halt (line 136), and no counter of consecutive exits by reason.
That halt needs code, and neither document lists it among the code changes.

### 6. HANDOFF 16.12, same halt (medium)

16.12 writes "Halt after 5 consecutive non-bot or deadline exits (the decoy signal)" next to engine settings, which reads as a setting.
No such setting or logic exists in `src/flip_engine.py` (as in error 5).

### 7. REPORT_owner.md and HANDOFF 16.12: the take-profit setting is not given (low)

The skeptic says to turn off the take-profit for v3.0 (`REPORT.md`, v3.0 live_test, EXIT).
`FRONT_TAKE_PROFIT` defaults to 0.01 (`src/flip_engine.py` line 129), and `take_profit` sells whenever a buy behind ours prices the sell at that return (line 1003).
REPORT_owner.md says "a take-profit high enough never to fire" without a value, and 16.12 gives no setting.
The engine's own convention is 9 for off (the `TAKE_PROFIT` comment, line 106), so the line the owner needs is `FRONT_TAKE_PROFIT=9`.

### 8. REPORT_owner.md 3 and 4.2: C-1's "$175 a day (census)" leans on one 6-hour burst (low)

The 124 a day is the 48-hour mean of 245 launches (`skeptic_0x58daec3116aae6d93017baaea7749052e8a04f/f2276_100/a2_census.json`).
Its 6-hour slices are 16, 15, 25, 92, 38, 13, 8, 38 (`a2_census.json`), so one slice holds 38% of the launches.
The other seven slices run at 89 a day, and the 8.7 hours after the census ran at 84 a day (`report/work/c1/c1_fresh.json`).
At 89 a day, 203 of 245 with a router buy and $1.73 a trade (`a5_ride.json`), the census-side figure is about $127 a day, not $175.

### 9. HANDOFF 16.12 item 1: v3.0 and v5.0 daily rates from a 3.25-hour window (low)

16.12 writes "889 v3.0 launches in 48 h (about 510 a day" and "434 v5.0 (about 270 a day)".
889 and 434 in 48 hours are 444 and 217 a day (`s1_basics.json`).
510 and 270 are the skeptic's 3.25-hour post-census counts, 69 and 37 (`REPORT.md`, v3.0 recomputed).
16.12's own $400 and $57 a day use the 48-hour rates.
REPORT_owner.md section 9 corrects the v3.0 figure and not the v5.0 one.

### 10. HANDOFF 16.12 item 4 and REPORT_owner.md 4.5: C-2's 4-block pulls are 8, not 5 (low)

Both say 5 of the outsider buys were followed by a pull exactly 4 blocks later.
`skeptic_0x8366a39cc670b4001a1121b8f6a443a643e409/reaction_ev.json` lists 5 delays of 4 in `census_delays` and 3 more in `fresh_delays`, so 8 of 25.
The skeptic's own "4-5 block reactions only, 8 of 25" case says the same (`reaction_ev.json`, `REPORT.md`).
This strengthens the trap verdict; it does not change it.

### 11. HANDOFF 16.12: the order of C-2 and the small pot (low)

16.12 says its list is "ranked by what it is worth to the owner" and puts C-2 fourth and the small pot fifth.
C-2 with its observed reaction is -95.8% a trade, about -$1,379 a day (`reaction_ev.json`).
The small pot with an early holder of our size is -30.1% a trade, about -$50 a day at 11 launches a day (`REPORT.md`, small-pot verdict; REPORT_owner.md section 3).
By value the small pot ranks above C-2; both are no-trade, so nothing operational changes.

### 12. HANDOFF 16.12: "FRONT_PIN 1 (16 value-0 look-alikes must be rejected)" (low)

The 16 non-bot launches have value 0 (15) or 1e-6 ETH (1) (`s1_basics.json`, "v-other").
The engine arms a front launch only when `value == FRONT_VALUE_WEI` (`src/flip_engine.py` line 1141), so with 3.0 ETH set they are never armed.
`FRONT_PIN` only rejects a 3.0 ETH launch whose fee, tick spacing, sqrtP or liquidity differ (lines 502-522).
The pin is harmless; the reason given for it is wrong.

### 13. HANDOFF 16.12: no confidence levels (low)

The skeptic gave v3.0 "real_candidate=True confidence=medium" and called it "a downgrade to 'conditional'" (`REPORT.md`).
16.12's heading and closing line state v3.0 as "the one real front candidate" and "the only other place the exact edge exists" without that qualifier.
The repository's `research/session_oct9_10/scanner/README.md` carries "candidate, conditional (medium)"; 16.12 does not.

### 14. REPORT_owner.md section 9: a misattribution (low)

It says "16.12 treats the 0.99 x round-number sizes as the operator's decoy signature".
16.12 says nothing about sizes.
The sentence is in 16.10 (`docs/HANDOFF.md` line 952: "the decoys and the bot share the 0.99 x round-number sizes").

## What I checked and found right

- REPORT_owner.md's `FEE_MAX_PPM`, `FRONT_BOT_MINOUT`, `FRONT_AHEAD_MAX_ETH` (others' buys plus our stake, line 1035) and the 0.006 ETH stake cap (line 128) match `src/flip_engine.py`.
- The v3.0 replay figures (+6.03% mean, +6.09% median, 99.2% win, 7 deadline exits, $401.9 a day) match `s4_replay.json`.
- The bot-offset share of 92% (819 of 889 at +6..+10) matches `s1_basics.json`.
- The room ahead of the v3.0 bot (0.0794 to 0.0817 ETH at minOut 0.95, 0.0154 to 0.0158 at 0.99) matches `report/work/room_v3.json`.
- The fronter replay (+6.48% mean, +7.75% median, 85 of 85 positive) matches `f8_fresh.json` rows.
- `0x8cf143dd` is a buyer in 83 operator A launches in `research/session_oct9_10/origins/eras/p2_buyercnt.json`.
- The C-1 ride figures match `a5_ride.json` and `c1_fresh.json`.
- The control figures in REPORT_owner.md section 10 match `analyse_10/calib.json` and `analyse_26/results.json`.
- The 97 not-flagged strict families with 1,422 pools reproduce from `census/families.json` (98 non-flagged, non-control families with 1,428 pools, less operator A's 6-pool family).
- The relayed shell paste (46 "ok" lines, "Already up to date") matches the box's state before the 02:50 UTC branch switch that HANDOFF 11.2 describes: the code of 4dce46e prints 46 "ok" lines in my run, and the code of de88eb9 prints 51.

## What none of the three documents carries

- The v3.0 break-even: "about 26% of trades need the real bot buy to fill" (`REPORT.md`, v3.0 strongest_objection). On v2.433 at $15 the operator's decoys made the bot's buy revert in about 72% of pools (HANDOFF 16.10), which would put v3.0 near that line if it repeats the move.
- C-1: the six quick pulls after an outsider came 60 to 86 blocks after the outsider's buy, only 10 to 36 blocks after the planned 50-block sell (`REPORT.md`, C-1 objection).
- C-1: hold and landing variants: 20 blocks +6.8% mean with a -0.1% median, 100 blocks +21.9% with 16 stakes lost, landing at c1+2 +10.5% and c1+3 +10.0% (`a5_ride.json`).
- C-1: the skeptic's dry-run details: price our buy at minOut 0.97 of the quote, and log two shadow exits (at +40, and an early sell if no router buy follows within 20 blocks) (`REPORT.md`, C-1 live_test).
- C-1: a recogniser detail: all 5,763 router calls carry gas limit 1,000,000 and gas price equal to the tip, with minOut 0 (`REPORT.md`).
- Router `0x65050a9b`: the C-1 and small-pot skeptics found it used by unrelated outsiders (15 buys and 9 sells in 66 C-1 pools; rugged outsiders in small-pot pools) (`REPORT.md`). HANDOFF section 1 (line 96) still lists it as the volume bot's own decoy router. The v3.0 skeptic counted its presence in 215 v5.0 pools as an operator link. This bears on whether `0x8cf143dd` is a competitor or a decoy.
- Small pot: wallet `0x5e6ec144` already runs this hold at about 0.0003 ETH (about $0.40 a trade), the size the operator tolerates. The follow variant also fails: with a mid-crowd outsider of 0.002 ETH or more, the crowd reached 10 buys in 2 of 17 cases (`REPORT.md`, small-pot verdict).
- C-2's hooked sibling (`PM 6276cbbe 196B fee 500 hooked`, 23 pools) uses C-2's crowd routers (`REPORT.md`, C-2 identity). REPORT_owner.md section 6 lists it as a near-miss at +13.3% follow without saying C-2's 24-of-25 outsider-pull reaction likely applies.
- HANDOFF 16.12 says the stake curve is flat to 0.075 ETH; it does not say the engine caps the front stake at 0.006 ETH in code (`src/flip_engine.py` line 128). REPORT_owner.md does say it.

## REPORT_method.md

It is a 540-byte stub saying a safety check stopped the response.
It contains no method report, no family table and no engine requirements.
The method content exists only in REPORT_owner.md sections 8 and 10.

## Verdict changes

- v3.0 keeps rank 1 at medium confidence. Its caveat "the operator's answer to a seller is unobserved" should become "observed since 01:57 UTC Oct 11: the pull at bot+3 after 56 sells into the bot's buy, 2 blocks after a bot+1 sell". Its value should be quoted at about $400 a day, not $600.
- C-1 keeps rank 2. Its value range should read about $90 to $127 a day, not $90 to $175.
- In HANDOFF 16.12, the small pot (about -$50 a day) belongs above C-2 (about -$1,379 a day); both stay no-trade.
