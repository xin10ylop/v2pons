"""context for the 0x0000ffff 3236-byte family: the launcher's other families, the R75 router's footprint in the census"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common13 import *  # noqa
P = load_pools(); T = load_txs(); F = load_families()
L = "0x0000ffffbe8efe702c8703ae3477ff5de3d319c0"
fam = collections.defaultdict(list)
for pid, p in P.items():
    if p["launch_to"] == L: fam[p["family"]].append(p)
print("0x0000ffff families:")
for k, ps in sorted(fam.items(), key=lambda kv: -len(kv[1])):
    vals = collections.Counter(round(p["launch_value_eth"], 6) for p in ps).most_common(4)
    r75 = sum(1 for p in ps if R75 in (p["first8_swap_to"] or []))
    print(f"  {len(ps):3d} {k.split('|',1)[1]} vals {vals} buy_in_launch {sum(1 for p in ps if p['buy_in_launch_tx'])} r75 {r75} nonce0 {sum(1 for p in ps if p['launch_nonce']==0)} pulls {sum(1 for p in ps if p['first_pull_rel'] is not None)} fb {collections.Counter(p['first_buy_rel'] for p in ps).most_common(3)} nswaps_med {sorted(p['n_swaps'] for p in ps)[len(ps)//2]}")
# R75 in the census: pools where a first-8 swap tx goes to R75
ps75 = [p for p in P.values() if R75 in (p["first8_swap_to"] or [])]
print("pools with an R75 swap among the first 8:", len(ps75))
print("  by launch_to:", collections.Counter(p["launch_to"] for p in ps75).most_common(8))
print("  by family:", [(k.split('|')[0][:10] + '|' + '|'.join(k.split('|')[1:]), n) for k, n in collections.Counter(p["family"] for p in ps75).most_common(10)])
# the first R75 buy per pool: offset and size, across the census
E = load_events(set(p["pid"] for p in ps75))
rows = []
for p in ps75:
    e = E.get(p["pid"]) or {}
    for s in e.get("swaps", []):
        t = T.get(s["tx"])
        if t and t["to"] == R75 and s["a0"] < 0:
            rows.append((p["family"], s["bn"] - p["launch_block"], -s["a0"] / 1e18, t["from"], t["nonce"], p["buy_in_launch_tx"])); break
byf = collections.defaultdict(list)
for r in rows: byf[r[0]].append(r)
for k, rs in sorted(byf.items(), key=lambda kv: -len(kv[1]))[:12]:
    print(f"  {len(rs):3d} {k[:10]}|{'|'.join(k.split('|')[1:])} first R75 buy rel {q([r[1] for r in rs])} eth {q([r[2] for r in rs])} wallets {len(set(r[3] for r in rs))} nonce {q([r[4] for r in rs])} launchbuy {sum(1 for r in rs if r[5])}")
# the recurring small buyers of the 3236 family
k3 = json.load(open(os.path.join(HERE, "keys.json")))[2]
E3 = load_events(set(F[k3]["pids"]))
w = collections.Counter(); wp = collections.defaultdict(set)
for pid in F[k3]["pids"]:
    for s in E3[pid]["swaps"]:
        t = T.get(s["tx"])
        if t and s["a0"] < 0: wp[t["from"]].add(pid)
print("3236 buyers in >= 2 pools (first-8 swaps):", [(a[:10], len(b)) for a, b in sorted(wp.items(), key=lambda kv: -len(kv[1])) if len(b) >= 2])
