"""Generalised: a non-dust outsider HOLDING in the pool at T+62 (bought >= 0.001 ETH anywhere from launch to T+62, before the pull, and had not
sold by T+62 or the pull), our relay's fills, and the rest. Share pulled by T+62 / T+120 / T+200, Fisher one-sided p against the rest; whether the
router bought after T+62; every holder pool listed. (offline, c05)"""
from common import *
from math import comb
D = json.load(open(J("c05_pools.json"))); P = D["pools"]
OUT = ("recurring", "oneoff")
TP = [p for p in P if p["T"] is not None and p["age"] >= p["T"] + 300]
def fisher_greater(a, n1, b, n2):
    K = a + b; N = n1 + n2
    return sum(comb(K, x) * comb(N - K, n1 - x) for x in range(a, min(K, n1) + 1)) / comb(N, n1)
G = {"ours": [], "holder": [], "sold": [], "none": []}; detail = []
for p in TP:
    end = min(p["T"] + 62, p["pull"] if p["pull"] is not None else 1 << 40)
    ours = any(s["cls"] == "ours" and s["buy"] for s in p["sw"])
    hs = []; sold = []
    for s in p["sw"]:
        if not (s["buy"] and s["cls"] in OUT and s["eth"] >= 0.001 and s["off"] <= p["T"] + 62): continue
        if p["pullpos"] and (s["bn"], s["li"]) > tuple(p["pullpos"]): continue
        sl = [x for x in p["sw"] if not x["buy"] and x.get("from") == s["from"] and (x["bn"], x["li"]) > (s["bn"], s["li"]) and x["off"] <= end]
        (sold if sl else hs).append(s)
    g = "ours" if ours else ("holder" if hs else ("sold" if sold else "none"))
    G[g].append(p)
    if g == "holder":
        s = hs[0]; nra = sum(1 for x in p["sw"] if x["buy"] and x["cls"] == "router" and x["off"] > p["T"] + 62 and (p["pull"] is None or x["off"] < p["pull"]))
        detail.append(f"  {utc(p['ts'])} {p['pid'][:12]} T +{p['T']} outsider {s['from'][:10]} ({s['cls']}) {s['eth']:.5f} at T{s['off'] - p['T']:+d} | pull T+{None if p['pull'] is None else p['pull'] - p['T']} | router buys after T+62: {nra}")
print("pools triggered and >= T+300 old:", {k: len(v) for k, v in G.items()})
for X in (62, 120, 200):
    k = lambda g: sum(1 for p in g if p["pull"] is not None and p["pull"] - p["T"] <= X)
    print(f"pulled by T+{X:3d}: " + ", ".join(f"{g} {k(v)}/{len(v)} ({k(v) / max(1, len(v)):.1%})" for g, v in G.items())
          + f" | Fisher holder vs none p {fisher_greater(k(G['holder']), len(G['holder']), k(G['none']), len(G['none'])):.2g}; ours vs none p {fisher_greater(k(G['ours']), len(G['ours']), k(G['none']), len(G['none'])):.2g}")
nra = lambda g: sum(1 for p in g if not any(x["buy"] and x["cls"] == "router" and x["off"] > p["T"] + 62 and (p["pull"] is None or x["off"] < p["pull"]) for x in p["sw"]))
print("router never buys after T+62 (before the pull): " + ", ".join(f"{g} {nra(v)}/{len(v)}" for g, v in G.items()))
print("holder pools:"); print("\n".join(detail))
