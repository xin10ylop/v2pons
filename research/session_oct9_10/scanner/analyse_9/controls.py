import sys, json, collections
sys.path.insert(0, "."); from common9 import *
F = load_families(); P = load_pools(); T = load_txs(); M = load_blocks_meta()
groups = {"vbot-v2.433": [p for p in P if P[p]["known"] == "vbot-v2.433"], "operator-A": [p for p in P if P[p]["known"] == "operator-A"]}
E = load_events(set(groups["vbot-v2.433"]) | set(groups["operator-A"]))
out = {}
for g, pids in groups.items():
    pools = [Pool(P[p], E.get(p), T, M) for p in pids]
    sched = (lambda x: x["to"] == VBOT_ROUTER) if g == "vbot-v2.433" else (lambda x: x["eth"] >= MIN_REAL)
    fa = [(pl, (pl.buys() or [None])[0]) for pl in pools]
    fs = [(pl, next((x for x in pl.buys() if sched(x)), None)) for pl in pools]
    d = lambda lst: {"frac": round(sum(1 for _, x in lst if x) / len(lst), 3), "off": q([x["bn"] - pl.b0 for pl, x in lst if x]), "eth": q([x["eth"] / 1e18 for pl, x in lst if x], nd=6),
                     "to": collections.Counter((x["to"] or "?")[:10] for _, x in lst if x).most_common(3), "n_from": len(set(x["from"] for _, x in lst if x))}
    pulled = [pl for pl in pools if pl.pull_bn]
    out[g] = {"n": len(pools), "per_day": round(len(pools) / WINDOW_DAYS, 1), "first_any": d(fa), "first_sched": d(fs),
              "pull_frac": round(len(pulled) / len(pools), 3), "pull_off_launch": q([pl.pull_bn - pl.b0 for pl in pulled]),
              "pull_off_sched": q([pl.pull_bn - x["bn"] for pl, x in fs if x and pl.pull_bn]),
              "pull_from_launch_wallet": round(sum(1 for pl in pulled if (T.get(pl.pulls[0]["tx"]) or {}).get("from") == pl.p["launch_from"]) / max(1, len(pulled)), 3),
              "outsider_pools_before_sched": round(sum(1 for pl, x in fs if x and any((y["bn"], y["li"]) < (x["bn"], x["li"]) for y in pl.buys())) / len(pools), 3)}
    print(g, json.dumps(out[g]))
json.dump(out, open("controls.json", "w"), indent=1)
