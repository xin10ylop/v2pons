"""validation against REPORT_W's forward test (analysis/W/w05_recent_8h_forward.json, Oct 11): the same pools here, their first real buy
(>= 0.005 ETH, any buyer; and the crowd's, from r04 when built), pull offset and the rule's exit, compared pool by pool."""
from common import *
from wcommon import compact
W = json.load(open("/home/user/v2pons/research/session_oct11/lines/analysis/W/w05_recent_8h_forward.json"))
L = {x["pool"]: x for x in json.load(open(J("r01_launches.json")))}
E = {e["pool"]: e for e in jl(J("r02_events_cache.jsonl"))}
B = {x["pool"]: x for x in jl(J("r02_burns_cache.jsonl"))}
R4 = {}
if os.path.exists(J("r04_pools_cache.jsonl")):
    from rlib import summ
    for line in open(J("r04_pools_cache.jsonl")):
        p = json.loads(line)
        if p["pool"] in {w["pool"] for w in W}: R4[p["pool"]] = summ(p)
ok = n = okc = nc = okp = np_ = 0
for w in W:
    e = E.get(w["pool"]); x = L.get(w["pool"])
    if not e: print("missing here", w["pool"]); continue
    lb = x["lb"]; qs = x["qs"]
    ev = sorted([c for c in (compact(l) for l in e["logs"]) if c], key=lambda c: (c[1], c[3]))
    fb = next((c[1] - lb for c in ev if c[0] == "s" and (c[7] if qs == 0 else c[8]) >= 5e15), None)
    pl = [c[1] - lb for c in ev if c[0] == "b" and c[8] > 0] or [c[1] - lb for c in (compact(l) for l in (B.get(w["pool"]) or {}).get("burns", [])) if c and c[8] > 0]
    pull = min(pl) if pl else None
    n += 1; ok += fb == w["frb_off"]
    if w["pull"] is not None: np_ += 1; okp += pull == w["pull"]
    if w["pool"] in R4: nc += 1; okc += R4[w["pool"]]["frb"] == w["frb_off"]
    if fb != w["frb_off"] or (w["pull"] is not None and pull != w["pull"]): print("  differs:", w["pool"][:10], "W frb", w["frb_off"], "here", fb, "W pull", w["pull"], "here", pull)
print(f"W's forward pools {len(W)}: first real buy equal {ok}/{n}; pull equal {okp}/{np_} (W's pulls seen by its head); crowd frb (r04) equal to W's {okc}/{nc}")
