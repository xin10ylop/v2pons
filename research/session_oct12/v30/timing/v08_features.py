"""No RPC: does anything known at or soon after L predict T-L? (launcher class, deploy->L gap, sentinel / 0x7ae81404 offsets, launch tx index,
the previous pool's T-L, T-L of the pool launched just before, launch second phase). Pearson r and the best +-1 share inside each group."""
import vc, json, collections, statistics as S
P = json.load(open(vc.p("v03_pools.json"))); P.sort(key=lambda o: o["L"])
def r(x, y):
    mx, my = S.mean(x), S.mean(y); sx = sum((a - mx) ** 2 for a in x) ** .5; sy = sum((b - my) ** 2 for b in y) ** .5
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else 0
def best1(ds):
    c = collections.Counter(ds); return max(sum(c[k + j] for j in (-1, 0, 1)) for k in range(min(ds), max(ds) + 1)) / len(ds)
feat = {}
for i, o in enumerate(P):
    sent = [x["d"] for x in o["pre"] if (x["from"] or "")[:10] == vc.SENTINEL]
    a7 = [x["d"] for x in o["pre"] if (x["from"] or "")[:10] == "0x7ae81404"]
    feat.setdefault("sentinel_d", []).append((sent[0] if sent else None, o["d"]))
    feat.setdefault("7ae81404_d", []).append((a7[0] if a7 else None, o["d"]))
    feat.setdefault("deploy_gap", []).append((o["L"] - o["deploy"], o["d"]))
    feat.setdefault("launch_idx", []).append((o["idx"], o["d"]))
    feat.setdefault("nonce_lo", []).append((int(o["nonce"] < 50), o["d"]))
    feat.setdefault("prev_pool_d", []).append((P[i - 1]["d"] if i else None, o["d"]))
    feat.setdefault("gap_prev_L", []).append((o["L"] - P[i - 1]["L"] if i else None, o["d"]))
    feat.setdefault("L_mod_10", []).append((o["L"] % 10, o["d"]))
for k, v in feat.items():
    v = [(a, b) for a, b in v if a is not None]
    g = collections.defaultdict(list)
    for a, b in v: g[a].append(b)
    big = sorted(((a, len(b), best1(b)) for a, b in g.items() if len(b) >= 15), key=lambda z: -z[2])[:3]
    print("%-12s n %3d r %+.3f  best groups (value, n, best+-1 share): %s" % (k, len(v), r([a for a, _ in v], [b for _, b in v]), [(a, n, round(s, 2)) for a, n, s in big]))
