import sys, json, collections, datetime
sys.path.insert(0, "."); from common9 import *
F = load_families(); P = load_pools(); T = load_txs(); M = load_blocks_meta()
rows = [p for p in P.values() if p["launch_to"] == "0x0000ffffbe8efe702c8703ae3477ff5de3d319c0" or p["launch_from"] == "0x26e8134ecc3af5cce32f34b03e7bd2f318b25158"]
E = load_events(set(p["pid"] for p in rows))
agg = collections.defaultdict(lambda: {"n": 0, "real": 0, "pulled": 0, "eth": 0.0, "froms": collections.Counter(), "vals": collections.Counter(), "fb_rel": [], "pull_rel": [], "ts": []})
for p in rows:
    pl = Pool(p, E.get(p["pid"]), T, M); a = agg[p["family"]]
    a["n"] += 1; a["froms"][p["launch_from"][:10]] += 1; a["vals"][p["launch_value_eth"]] += 1; a["ts"].append(p["launch_ts"])
    rb = pl.buys(MIN_REAL)
    if rb: a["real"] += 1; a["fb_rel"].append(rb[0]["bn"] - pl.b0)
    a["eth"] += sum(x["eth"] for x in pl.buys()) / 1e18
    if pl.pull_bn: a["pulled"] += 1; a["pull_rel"].append(pl.pull_bn - pl.b0)
for k, a in sorted(agg.items(), key=lambda kv: -kv[1]["n"]):
    print(k, a["n"], "real-buy pools", a["real"], "pulled", a["pulled"], "eth_in", round(a["eth"], 4), dict(a["froms"]), dict(a["vals"].most_common(3)), "fb", q(a["fb_rel"]), "pull", q(a["pull_rel"]),
          datetime.datetime.utcfromtimestamp(min(a["ts"])).strftime("%m-%d %H:%M"), datetime.datetime.utcfromtimestamp(max(a["ts"])).strftime("%m-%d %H:%M"))
