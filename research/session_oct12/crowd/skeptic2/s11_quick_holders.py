"""since Oct 10: are the quick post-trigger pulls (within 30 of the trigger) holder pools? Triggered pools split by an outside holding (>= 0.0005 ETH,
still held) at the trigger: non-bot, the + 1 bot only, none; and by the outside ETH held at the trigger."""
from common import *
BOT1 = "0x776e5a2a72f9711ed818e2a0535d3d01cf8ed3d6"; MIN = 5 * 10 ** 14; OCT10 = 1791590400
P = {p["pool"]: p for p in json.load(open(J("s04_pools.json")))}
R = {}
for l in open(J("../reaction/r04_pools_cache.jsonl")):
    r = json.loads(l); R[r["pool"]] = r
def held(sw, at):
    W = {}
    for s in sw:
        if s["off"] >= at: break
        if s["k"] != "other" or not s["from"]: continue
        w = W.setdefault(s["from"], [0, 0, 0])
        if s["dq"] > 0: w[0] += s["dq"]; w[1] += -s["dt"]
        else: w[2] += s["dt"]
    nb = sum(w[0] for a, w in W.items() if a != BOT1 and w[0] >= MIN and w[1] and w[2] < 0.5 * w[1]) / 1e18
    bt = any(a == BOT1 and w[0] >= MIN and w[1] and w[2] < 0.5 * w[1] for a, w in W.items())
    return nb, bt
for lab, f in (("Oct 3-9", lambda p: p["ts"] < OCT10), ("Oct 10-12", lambda p: p["ts"] >= OCT10)):
    G = {"non-bot holder": [0, 0, 0], "the +1 bot only": [0, 0, 0], "no outside holder": [0, 0, 0]}
    for pool, p in P.items():
        if p["trig"] is None or not f(p): continue
        pull = p["pull"]["off"] if p["pull"] else R[pool]["pull_off"]
        nb, bt = held(R[pool]["sw"], p["trig"])
        k = "non-bot holder" if nb > 0 else "the +1 bot only" if bt else "no outside holder"
        G[k][0] += 1; G[k][1] += pull is not None and pull - p["trig"] <= 30; G[k][2] += pull is not None and pull - p["trig"] <= 20
    print(lab, {k: f"n {v[0]}, pulled within 30 of the trigger {v[1]}, within 20 {v[2]}" for k, v in G.items()})
