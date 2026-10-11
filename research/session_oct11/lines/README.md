# Oct 11 2026: the search for other lines (census 2, three analysts, the adversarial verifier)

Question (the owner, 15:xx UTC): "find a way to trade it, for every line ... there must be plenty"; later "review 2.43 and 3.0" and the
method that found front (gather every launch, group by launch shape, test the rule grid, validate on later slices). Method: a 7-day behaviour-first census of
every new ETH/WETH/USDG pool on Robinhood Chain (v4, V2, V3), then three Opus analysts replaying candidate lines against our exact trade
mechanics (BRIEF.md), then an adversarial verifier on the one candidate both v4 analysts ranked first. Reports: REPORT_census.md (the census
builder's hand-back; the data files it names are in census/, the 216 MB pools.jsonl and the 3 GB cache were not kept), REPORT_A.md (the
PositionManager-multicall launches without the volume bot), REPORT_B.md (every other v4 launcher), REPORT_C.md (V2 and V3), REPORT_V.md (the
verifier on C-1), REPORT_R.md (the ride on the 2.4333 and 3.0 lines: none, the operator pulls ~9 blocks after any stranger buy), REPORT_W.md
(scoping the V3 crowd line: buildable in ~12 h, +5.2% mean / +0.17% median today, ~$65/day, forward-test first), REPORT_H.md (the hooked pump
line: sells unverifiable, every pool pulled within hours, parked), REPORT_G.md (the owner's method brute force: 123 families x 2,574 rules,
no new large safe line; the 2.433 line is the calibration and passes). Scripts and their outputs: analysis/<letter>/ (files over 1 MB dropped). The engine change that came out of it: the wave
family mode (src/flip_engine.py, tests 20f, RUNBOOK 4g, HANDOFF 16.15).

Outcome in one line: 64,416 pools, 184 token families with 5+ launches; 122 of the 163 families with 10+ launches have a real buyer in under
5% of launches; one v4 candidate (C-1, a follow-type line, ~100 launches/day, replay +16%/78% win/3% pulled, ~$200/day at $15) survived
three analysts and the verifier's recomputation but failed its forward test (the edge is the operator's own buying and fell to +1.8% in the
2.6 h after the census): built as a dry-run family, to be probed live only after 24 h of dry data; one V3 line (the "crowd" line, ~$185/day
at $15, new trading path) and one hooked v4 pump line (hook risk, sell simulation first) as later projects; everything else rejected on numbers.
