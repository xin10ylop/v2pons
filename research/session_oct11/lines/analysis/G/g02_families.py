"""group v4 pools by the launch-shape key and by the token skeleton; keep families with >= 20 launches in 7 days and >= 8 in the last 48 h"""
from common import *
rows = load_rows()
fams = {"shape": C.defaultdict(list), "tok": C.defaultdict(list)}
for r in rows:
    fams["shape"][shape_key(r)].append(r["pool"])
    fams["tok"][tok_key(r)].append(r["pool"])
byid = {r["pool"]: r for r in rows}
kept = {}
for g, d in fams.items():
    n20 = [k for k, v in d.items() if len(v) >= 20]
    k48 = [k for k in n20 if sum(byid[p]["launch_ts"] >= LAST48 for p in d[k]) >= 8]
    print(f"{g}: families {len(d)}, >=20 launches {len(n20)} ({sum(len(d[k]) for k in n20)} pools), and >=8 in last 48h {len(k48)} ({sum(len(d[k]) for k in k48)} pools)")
    for k in k48: kept[g + "=" + k] = sorted(d[k], key=lambda p: byid[p]["launch_block"])
allp = set(p for v in kept.values() for p in v)
print("kept families", len(kept), "distinct pools", len(allp))
json.dump(kept, open(os.path.join(G, "families_kept.json"), "w"))
for k, v in sorted(kept.items(), key=lambda kv: -len(kv[1])):
    rs = [byid[p] for p in v]
    n48 = sum(r["launch_ts"] >= LAST48 for r in rs)
    kf = C.Counter(r["known_fp"] for r in rs).most_common(2)
    print(f"{len(v):6d} {n48:5d} {k[:130]} {kf}")
