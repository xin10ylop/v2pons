#!/usr/bin/env python3
"""Does the PM1444 v3.0 deployer pull after an outside buy? (reaction_cache.pkl from reaction_fetch.py; pulls.json for times)
Buy classes: BOT = the volume bot (router 0x1cbaf24d, selector c1120e3d); DUST3 = 0xe71a69f4 (the dust buy at +3 on every pool);
DEPLOYER = the pool's deployer; OUTSIDE = anything else. For each pool: the first OUTSIDE buy, the pull, the delay between them."""
import sys, os, json, pickle, collections, statistics as st, bisect, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from chain import T_SWAP, W, sgn
from fetch import universe
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
C = pickle.load(open(os.path.join(HERE, "reaction_cache.pkl"), "rb")); TX = dict(C["tx"])
if os.path.exists(os.path.join(HERE, "reaction_new_tx.pkl")): TX.update(pickle.load(open(os.path.join(HERE, "reaction_new_tx.pkl"), "rb")))
ONLY = sys.argv[1] if len(sys.argv) > 1 else None          # 'new' / 'census': restrict
J = json.load(open(os.path.join(HERE, "pulls.json"))); tsm = J["ts_samples"]; ns = [x[0] for x in tsm]
def ts(b):
    i = max(1, min(len(ns) - 1, bisect.bisect_left(ns, b)))
    (n0, t0), (n1, t1) = tsm[i - 1], tsm[i]
    return t0 + (b - n0) * (t1 - t0) / (n1 - n0)
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"; DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
TSW = T_SWAP[-8:]
cen, nw = universe()
rows = []; missing = 0
for p in (nw if ONLY == "new" else cen if ONLY == "census" else cen + nw):
    ev = sorted(C["logs"].get(p["pid"], []), key=lambda x: (x[0], x[1]))
    pulls = [x for x in ev if not x[2].endswith(TSW) and sgn(W(x[4], 2)) < 0]
    pull = pulls[0] if pulls else None
    pb = pull[0] if pull else None
    dep = p["from"].lower()
    buys = []
    for x in ev:
        if pb is not None and (x[0], x[1]) > (pull[0], pull[1]): break
        if x[0] > p["b0"] + 400: break
        if x[2].endswith(TSW) and s128(W(x[4], 0)) < 0:
            t = TX.get(x[5])
            if t is None: missing += 1; cls = "?"
            elif t["to"] == ROUTER and t["sel"] == "0xc1120e3d": cls = "BOT"
            elif t["from"] == DUST: cls = "DUST3"
            elif t["from"] == dep: cls = "DEPLOYER"
            else: cls = "OUTSIDE"
            buys.append({"off": x[0] - p["b0"], "cls": cls, "eth": -s128(W(x[4], 0)) / 1e18, "from": t["from"] if t else None, "to": t["to"] if t else None,
                         "sel": t["sel"] if t else None, "nonce": t["nonce"] if t else None})
    pt = TX.get(pull[5]) if pull else None
    outs = [b for b in buys if b["cls"] == "OUTSIDE"]
    rows.append({"pid": p["pid"], "b0": p["b0"], "src": p["src"], "t": ts(p["b0"]), "pull_off": (pb - p["b0"]) if pb is not None else None,
                 "pull_by": ("deployer" if pt and pt["from"] == dep else (pt["from"] if pt else None)), "pull_via": (pt["to"][:10] + " " + pt["sel"]) if pt else None,
                 "first_out": outs[0] if outs else None, "n_out": len(outs), "n_bot": sum(1 for b in buys if b["cls"] == "BOT"), "buys": buys})
print("pools", len(rows), "buy txs missing", missing)
print("who pulls:", collections.Counter((r["pull_by"], r["pull_via"]) for r in rows if r["pull_off"] is not None).most_common(6))
# 1. pools with an outside buy before the pull (within 400): delay to the pull
with_out = [r for r in rows if r["first_out"]]
print(f"\npools with an OUTSIDE buy in [b0, min(pull, b0+400)]: {len(with_out)} of {len(rows)}")
d = [(r["pull_off"] - r["first_out"]["off"]) if r["pull_off"] is not None else None for r in with_out]
print("  delay first outside buy -> pull (blocks):", sorted(x for x in d if x is not None))
print("  of them never pulled within the logs:", sum(1 for x in d if x is None))
print("  pulled within 20 blocks of the first outside buy:", sum(1 for x in d if x is not None and x <= 20), "| within 60:", sum(1 for x in d if x is not None and x <= 60))
# 2. pools with NO outside buy before the pull: when pulled
no_out = [r for r in rows if not r["first_out"]]
po = [r["pull_off"] for r in no_out]
print(f"\npools with NO outside buy before the pull/+400: {len(no_out)}; pulled <= +45: {sum(1 for x in po if x is not None and x <= 45)}, <= +400: {sum(1 for x in po if x is not None and x <= 400)}, never/later: {sum(1 for x in po if x is None or x > 400)}")
# 3. outside buys: size, route, wallet; and the outside buys NOT followed by a pull within 60 blocks
print("\noutside buys by route:", collections.Counter((b["to"][:10], b["sel"]) for r in rows for b in r["buys"] if b["cls"] == "OUTSIDE").most_common(10))
print("outside wallets (pools):", collections.Counter(b["from"][:10] for r in rows for b in r["buys"] if b["cls"] == "OUTSIDE").most_common(12))
print("\nfirst outside buy, then pull delay, per pool (time, offset, eth, wallet, delay):")
for r in sorted(with_out, key=lambda r: r["b0"]):
    fo = r["first_out"]
    print(f"  {time.strftime('%m-%d %H:%M', time.gmtime(r['t']))} {r['src']:6s} out +{fo['off']:3d} {fo['eth']:.6f} ETH {fo['from'][:10]} n{fo['nonce']} via {fo['to'][:10]} {fo['sel']} -> pull {r['pull_off']} (delay {r['pull_off'] - fo['off'] if r['pull_off'] is not None else None}) bots before pull {r['n_bot']}")
json.dump(rows, open(os.path.join(HERE, "reaction.json"), "w"), default=str)
