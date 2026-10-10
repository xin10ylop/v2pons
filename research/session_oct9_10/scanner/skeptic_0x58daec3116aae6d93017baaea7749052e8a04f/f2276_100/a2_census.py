"""Skeptic f2276/100, step 2: the family's numbers recomputed from the raw census (all 245 pools; first-8-swap attribution only).
Prints the launch fingerprint, the first crowd buy (tx to 0xd6d35b56, e6cb474f) offsets with the 'never' pools split into truly-never
(fewer than 8 swaps without the crowd) and 'unknown' (8 visible swaps none of them the crowd: the census cannot see later txs), the pulls."""
import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "census"))
from load import *
K = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2276|100|1|true"
CROWD = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"
def q(v, ps=(0, .1, .5, .9, 1)):
    v = sorted(v); return [v[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))] for p in ps] if v else None
P = load_pools(); F = load_families(); T = load_txs(); B = load_blocks()
pids = F[K]["pids"]; E = load_events(set(pids))
out = {}
ts = [P[p]["launch_ts"] for p in pids]
out["n"] = len(pids); out["span_h"] = (max(ts) - min(ts)) / 3600; out["per_day"] = len(pids) / ((max(ts) - min(ts)) / 86400)
out["sp0"] = collections.Counter(P[p]["sqrt_p0"] for p in pids).most_common(3)
out["liq"] = collections.Counter(P[p]["liq_launch"] for p in pids).most_common(3)
out["nonce"] = collections.Counter(P[p]["launch_nonce"] for p in pids).most_common()
out["deployers"] = len(set(P[p]["launch_from"] for p in pids))
hours = collections.Counter(time_h // 21600 * 6 for time_h in [((t - min(ts)) // 3600) for t in ts])
import datetime
out["by_6h_utc"] = sorted(collections.Counter(datetime.datetime.utcfromtimestamp(t).strftime("%m-%d %H") [:-2] + "%02d" % (datetime.datetime.utcfromtimestamp(t).hour // 6 * 6) for t in ts).items())
rows = []
for pid in pids:
    p = P[pid]; e = E[pid]; b0 = p["launch_block"]
    sw = e["swaps"]; vis = [s for s in sw if s["tx"] in T]
    cr = [s for s in vis if T[s["tx"]]["to"] == CROWD and s["a0"] < 0]
    first_cr = cr[0]["bn"] - b0 if cr else None
    nvis = len(vis)
    status = "seen" if cr else ("never" if len(sw) <= 8 else "unknown")
    pull = e["pulls"][0]["bn"] - b0 if e["pulls"] else None
    rows.append({"pid": pid, "b0": b0, "cr": first_cr, "status": status, "nsw": len(sw), "pull": pull,
                 "cr_eth": -cr[0]["a0"] / 1e18 if cr else None,
                 "cr_block_eth": sum(-s["a0"] for s in vis if cr and s["bn"] == cr[0]["bn"] and T[s["tx"]]["to"] == CROWD) / 1e18 if cr else None,
                 "pull_full": (sum(x["dl"] for x in e["pulls"]) + sum(x["dl"] for x in e["adds"]) == 0) if e["pulls"] else None,
                 "pull_from": T[e["pulls"][0]["tx"]]["from"] if e["pulls"] and e["pulls"][0]["tx"] in T else None})
st_c = collections.Counter(r["status"] for r in rows)
out["crowd_status"] = st_c
out["crowd_first_off"] = q([r["cr"] for r in rows if r["cr"] is not None])
out["crowd_first_eth"] = q([r["cr_eth"] for r in rows if r["cr"] is not None])
out["pull_rate_3000"] = sum(1 for r in rows if r["pull"] is not None) / len(rows)
out["pull_off"] = q([r["pull"] for r in rows if r["pull"] is not None])
out["pull_minus_crowd"] = q([r["pull"] - r["cr"] for r in rows if r["pull"] is not None and r["cr"] is not None])
out["pull_full"] = collections.Counter(r["pull_full"] for r in rows)
out["pull_by_launcher"] = sum(1 for r in rows if r["pull_from"] and r["pull_from"] == P[r["pid"]]["launch_from"])
out["never_pull_off"] = q([r["pull"] for r in rows if r["status"] == "never" and r["pull"] is not None])
out["unknown_pull_off"] = q([r["pull"] for r in rows if r["status"] == "unknown" and r["pull"] is not None])
out["pull_before_crowd"] = sum(1 for r in rows if r["pull"] is not None and r["cr"] is not None and r["pull"] <= r["cr"])
for k, v in out.items(): print(k, json.dumps(v, default=str))
json.dump({"summary": out, "rows": rows}, open(os.path.join(HERE, "a2_census.json"), "w"), indent=1, default=str)
