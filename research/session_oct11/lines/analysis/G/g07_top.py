"""dedupe the V-ranked families (a family whose pools are >= 80% the same set as a higher-ranked one, Jaccard, is its twin) and list the top 15
distinct lines: first those whose chosen rule has every 6-hour slice positive, then the rest by validated $/day"""
from common import *
res = json.load(open(os.path.join(G, "g06_results_q0.0058.json")))
kept = json.load(open(os.path.join(G, "families_kept.json")))
sets = {k: set(v) for k, v in kept.items()}
top = []; twins = {}
for o in res:
    if not o["V"]: continue
    s = sets[o["fam"]]
    tw = None
    for t in top:
        u = sets[t["fam"]]; j = len(s & u) / len(s | u)
        if j >= 0.8: tw = (t["fam"], round(j, 3)); break
    if tw: twins.setdefault(tw[0], []).append([o["fam"], tw[1]]); continue
    # containment (one family inside a bigger one) is reported but not merged
    inside = [[t["fam"], round(len(s & sets[t["fam"]]) / len(s), 3)] for t in top if len(s & sets[t["fam"]]) / len(s) >= 0.8]
    o["inside"] = inside; top.append(o)
for t in top: t["twins"] = twins.get(t["fam"], [])
json.dump(top, open(os.path.join(G, "g07_top.json"), "w"), indent=1)
for i, o in enumerate(top):
    V = o["V"]; v = V["val"]
    print(f"{i+1:2d} {o['fam'][:100]:100s} {o['tagV'][:12]:12s} sl {V['slices_all'][1]}/{V['slices_all'][0]} {V['rule']:20s} val n {v['n']} {v['mean']*100:+.1f}% ${V['val_usd_day']:.0f}/d twins {[(a[:40], j) for a, j in o['twins']]} inside {[(a[:40], j) for a, j in o['inside']]}")
json.dump([o["fam"] for o in top[:15]] + [a for o in top[:15] for a, j in o["twins"]], open(os.path.join(G, "top15_keys.json"), "w"))
