import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_14")
from common14 import *
P0 = load_pools(); pids = [p["pid"] for p in P0.values() if p["known"] == "vbot-v2.433"]
ctx = Ctx(set(pids)); P, E, T = ctx.P, ctx.E, ctx.T
c = collections.Counter(); sizes = collections.defaultdict(list)
pre_pull = [0, 0, 0, 0]
for pid in pids:
    p = P[pid]; e = E[pid]
    sb = next((s for s in e["swaps"] if s["a0"] < 0 and is_bot_buy(T.get(s["tx"]))), None)
    if not sb: continue
    outs = [s for s in e["swaps"] if s["a0"] < 0 and s["tx"] != p["launch_tx"] and s["sender"] != RELAY and (s["bn"], s["li"]) < (sb["bn"], sb["li"])]
    for s in outs:
        t = T.get(s["tx"]); key = (t["to"][:10], t["selector"], t["from"][:10] if t["to"] != "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc" else "fresh")
        if -s["a0"] >= 1e13 and (t["to"] != "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc"):
            c[key] += 1; sizes[key].append(-s["a0"] / 1e18)
print(c.most_common(15))
for k, v in c.most_common(6): print(k, sorted(set(round(x, 6) for x in sizes[k]))[:8])
