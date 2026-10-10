"""Where do the sniper routers 0x65050a9b / 0xfd1b271f (selector 4d819a2a, 580-byte calldata) trade, and what do they make?
Buy -> sell matched by (pool, tx sender) within the first 8 swaps of each pool (the census has tx senders only there)."""
import sys, os, collections, statistics as st
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "census"))
from load import *
P = load_pools(); E = load_events(); T = load_txs()
SN = {"0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc", "0xfd1b271f235e5230eaee9d914ccb1af495bfb758"}
fam = collections.defaultdict(lambda: {"pools": set(), "buys": 0, "matched": 0, "pnl": [], "ret": [], "buy_off": [], "size": [], "hold": [], "sold_after_big": 0})
for pid, e in E.items():
    p = P[pid]; key = p["family"] if p["known"] == "none" else p["known"]
    open_ = {}
    for i, s in enumerate(e["swaps"]):
        t = T.get(s["tx"])
        if not t or t["to"] not in SN: continue
        f = fam[key]
        if s["a0"] < 0:
            f["pools"].add(pid); f["buys"] += 1; f["buy_off"].append(s["bn"] - p["launch_block"]); f["size"].append(-s["a0"])
            open_[t["from"]] = (s, i)
        elif t["from"] in open_:
            b, bi = open_.pop(t["from"])
            f["matched"] += 1; f["pnl"].append(s["a0"] + b["a0"]); f["ret"].append((s["a0"] + b["a0"]) / -b["a0"]); f["hold"].append(s["bn"] - b["bn"])
            big = [x for x in e["swaps"][bi + 1:i] if x["a0"] < 0 and -x["a0"] >= 2 * 10**15]
            if big: f["sold_after_big"] += 1
rows = sorted(fam.items(), key=lambda kv: -len(kv[1]["pools"]))
print("family | pools sniped / family count | buys | matched sells | sold after a >=0.002 ETH buy | ret p50 | pnl sum ETH | buy offset p10/50/90 | size p50/max | hold p50")
for k, f in rows[:30]:
    cnt = sum(1 for p in P.values() if (p["family"] if p["known"] == "none" else p["known"]) == k)
    r = sorted(f["ret"]); o = sorted(f["buy_off"]); sz = sorted(f["size"]); h = sorted(f["hold"])
    q = lambda v, x: v[int(x * (len(v) - 1))] if v else None
    print("%-75s %4d/%4d %5d %5d %5d %+7.2f%% %+.5f %s %.6f/%.6f %s" % (k[:75], len(f["pools"]), cnt, f["buys"], f["matched"], f["sold_after_big"], 100 * (q(r, .5) or 0), sum(f["pnl"]) / 1e18,
          [q(o, .1), q(o, .5), q(o, .9)], (q(sz, .5) or 0) / 1e18, (sz[-1] if sz else 0) / 1e18, q(h, .5)))
