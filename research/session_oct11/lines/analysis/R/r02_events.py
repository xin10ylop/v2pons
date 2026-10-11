"""Load census events for the vbot line pools (v2.433, v3.0) -> ev.pkl {pool: {lb, ev_to, sw, adds, pulls}} via evload.norm"""
import sys, json, pickle
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census"
sys.path.insert(0, CEN); from load import load_events
from evload import norm
R = {}
for l in open("vrows.jsonl"):
    r = json.loads(l)
    if r["known_fp"] in ("vbot-v2.433", "vbot-v3.0"): R[r["pool"]] = r
E = load_events(set(R))
out = {}
for pid, o in E.items():
    r = R[pid]
    raw = {(e[1], e[3]): e for e in o["ev"]}
    sw, adds, pulls = norm(r, o)
    for s in sw:                                   # attach the v4 Swap's sqrtPriceX96, liquidity (rows "s": [.., sqrtP idx 8, liq idx 9])
        e = raw[(s["bn"], s["li"])]; s["sp"] = e[8]; s["L"] = e[9]; s["a0"] = e[6]
    out[pid] = {"lb": o["lb"], "ev_to": o["ev_to"], "sw": sw, "adds": adds, "pulls": pulls}
pickle.dump(out, open("ev.pkl", "wb"))
print(len(R), "pools;", len(out), "with events")
