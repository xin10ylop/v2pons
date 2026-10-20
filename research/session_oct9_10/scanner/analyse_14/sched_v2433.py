import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_14")
from common14 import *
P0 = load_pools(); pids = [p["pid"] for p in P0.values() if p["known"] == "vbot-v2.433"]
ctx = Ctx(set(pids)); P, E, T = ctx.P, ctx.E, ctx.T
off, sz, frm = [], [], collections.Counter()
for pid in pids:
    p = P[pid]; e = E[pid]
    sb = next((s for s in e["swaps"] if s["a0"] < 0 and is_bot_buy(T.get(s["tx"]))), None)
    if not sb: continue
    off.append(sb["bn"] - p["launch_block"]); sz.append(-sb["a0"] / 1e18); frm[T[sb["tx"]]["from"]] += 1
r = {"n_with_bot_buy": len(off), "n": len(pids), "off_p10_50_90": pct(off), "eth_p10_50_90": pct(sz), "n_from": len(frm), "top_from": frm.most_common(3),
     "within_20": sum(1 for o in off if o <= 19)}
print(r); json.dump(r, open("sched_v2433.json", "w"))
