#!/usr/bin/env python3
"""Deployer funding, two hops, from the full-block scan 84431185-84443384: for each family launch in the window, the plain ETH transfers
into its deployer before the launch (hop 1) and into each hop-1 sender before it sent (hop 2); where each deployer's ETH went after its pull."""
import sys, os, json, pickle, collections; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
P, TX, M = load(); BOTW, cls = classifier(TX); DEPS = {v["dep"]: v for v in P.values()}
B = pickle.load(open(os.path.join(HERE, "scan_84431185_84476185.pkl"), "rb")); lo, hi = min(B), max(B)
inc = collections.defaultdict(list); out = collections.defaultdict(list)
for bn, (ts, txs) in sorted(B.items()):
    for t in txs:
        h, f, to, val, nonce, sel, inlen, prio = t
        out[f].append((bn, to, val, nonce, sel, inlen))
        if val > 0 and sel in ("0x", ""): inc[to].append((bn, f, val, nonce))
def role(a):
    if a in DEPS: return f"deployer({DEPS[a]['fam']},n{DEPS[a]['nonce']})"
    if a in BOTW: return "bot-wallet"
    return "other"
def hop(a, before):
    xs = [x for x in inc[a] if x[0] < before]
    g = collections.defaultdict(lambda: [0, 0.0])
    for bn, f, val, n in xs: r = role(f); g[r][0] += 1; g[r][1] += val / 1e18
    big = [(bn, f, round(val / 1e18, 4), role(f)) for bn, f, val, n in xs if val > 1e18]
    return dict((k, (c, round(s, 4))) for k, (c, s) in g.items()), big
rows = []
for v in sorted(P.values(), key=lambda v: v["b0"]):
    if not (lo + 400 <= v["b0"] <= hi): continue
    h1, big1 = hop(v["dep"], v["b0"])
    h2 = [(b[1][:10], hop(b[1], b[0])[0]) for b in big1]
    after = [(bn - v["b0"], to[:10], round(val / 1e18, 4), role(to)) for bn, to, val, n, sel, il in out[v["dep"]] if bn > v["b0"] and val > 0]
    rows.append({"fam": v["fam"], "b0": v["b0"], "dep": v["dep"], "nonce": v["nonce"], "pull": v["pull"], "hop1": h1, "hop1_big": big1, "hop2": h2, "after_pull": after})
    print(f"{v['fam']:6s} {v['b0']} dep {v['dep'][:10]} n{v['nonce']} pull +{v['pull']}\n   hop1 {h1}\n   hop1 >1 ETH {big1}\n   hop2 {h2}\n   out after launch {after}")
json.dump(rows, open(os.path.join(HERE, "chains.json"), "w"), indent=1)
lanes = collections.Counter((role(f), role(t)) for a in inc for (bn, f, val, n) in inc[a] for t in [a] if val > 1e18)
print("transfers > 1 ETH by role:", lanes)
