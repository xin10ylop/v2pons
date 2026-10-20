import sys, os, pickle, json, collections, statistics as st
SCR = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"; sys.path.insert(0, SCR)
from chain import T_SWAP, T_ML, W, sgn
HERE = os.path.dirname(os.path.abspath(__file__))
C = pickle.load(open(os.path.join(HERE, "census_s.pkl"), "rb"))
D = pickle.load(open(os.path.join(HERE, "data_s.pkl"), "rb"))
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
def s128(v):
    v = sgn(v); return v - (1 << 128) if v >= (1 << 127) else v
txs = dict(C["txs"]); txs.update(D["txs"])
fam = C["fam"] + [{"pid": x["pid"], "bn": x["bn"], "tx": x["tx"], "from": x["from"].lower()} for x in D["fam"]]
by = collections.defaultdict(list)
for l in C["plogs"] + D["logs"]: by[l["topics"][1]].append(l)
rows = []
for x in fam:
    seen = set(); ev = []
    for l in sorted(by[x["pid"]], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
        k = (l["transactionHash"], l["logIndex"])
        if k in seen: continue
        seen.add(k); ev.append(l)
    b0 = x["bn"]; pull = None; fbot = None; pre = []; first_any_ge = None
    for l in ev:
        bn = int(l["blockNumber"], 16)
        if l["topics"][0] == T_ML:
            if sgn(W(l["data"], 2)) < 0:
                t = txs.get(l["transactionHash"]); pull = (bn, t["from"].lower() if t else None); break
            continue
        a0 = s128(W(l["data"], 0))
        if a0 >= 0: 
            if fbot is None: pre.append((bn - b0, "SELL", a0 / 1e18, None, None))
            continue
        t = txs.get(l["transactionHash"])
        isbot = t is not None and (t["to"] or "").lower() == ROUTER and t["input"][:10] == "0xc1120e3d"
        if fbot is None:
            if isbot: fbot = bn
            else: pre.append((bn - b0, "BUY", -a0 / 1e18, t["from"].lower()[:10] if t else "?", (t["to"] or "").lower()[:10] if t else "?"))
    rows.append({"pid": x["pid"], "b0": b0, "launcher": x["from"], "pull": pull[0] - b0 if pull else None, "pull_by_launcher": (pull[1] == x["from"]) if pull else None,
                 "bot": fbot - b0 if fbot else None, "pre": pre})
rows.sort(key=lambda r: r["b0"])
n = len(rows); print("family pools", n, "first b0", rows[0]["b0"], "last", rows[-1]["b0"])
pulled = [r for r in rows if r["pull"] is not None]
print("pulled", len(pulled), "pulled by the launcher", sum(1 for r in pulled if r["pull_by_launcher"]))
early = [r for r in pulled if r["pull"] <= 15]; print("pulls <= 15 blocks after launch:", [(r["pid"][:10], r["b0"], r["pull"], r["bot"], r["pre"]) for r in early])
nobot = [r for r in rows if r["bot"] is None]; print("pools with no bot buy before pull:", [(r["pid"][:10], r["b0"], r["pull"], r["pre"][:6]) for r in nobot])
pl = sorted(r["pull"] for r in pulled); q = lambda a, f: a[int(f * (len(a) - 1))]
print("pull - launch: min", pl[0], "q05", q(pl, .05), "q25", q(pl, .25), "median", q(pl, .5), "q75", q(pl, .75), "max", pl[-1])
print("pull - launch <= 30:", sum(1 for v in pl if v <= 30), " <= 60:", sum(1 for v in pl if v <= 60), " <= 90:", sum(1 for v in pl if v <= 90))
pb = sorted(r["pull"] - r["bot"] for r in pulled if r["bot"] is not None)
print("pull - bot first buy: min", pb[0], "q05", q(pb, .05), "q25", q(pb, .25), "median", q(pb, .5), "q75", q(pb, .75), "max", pb[-1], "n", len(pb))
print("pull - bot <= 15:", [(r["pid"][:10], r["b0"], r["bot"], r["pull"]) for r in pulled if r["bot"] is not None and r["pull"] - r["bot"] <= 15])
print("pull - bot <= 50:", sum(1 for v in pb if v <= 50))
bots = collections.Counter(r["bot"] for r in rows); print("bot first buy offset", sorted(bots.items(), key=lambda z: (z[0] is None, z[0] or 0)))
# pre-bot buys
pre_all = [(r["pid"][:10], r["b0"], p, r["bot"], r["pull"]) for r in rows for p in r["pre"]]
big = [z for z in pre_all if z[2][1] == "BUY" and z[2][2] >= 0.0002]
print("pre-bot non-bot buys >= 0.0002 ETH:", len(big))
for z in big: print("   ", z[0], z[1], "buy at +%d %.6f ETH from %s via %s" % (z[2][0], z[2][2], z[2][3], z[2][4]), "bot +", z[3], "pull +", z[4], "pull-after-buy", (z[4] - z[2][0]) if z[4] is not None else None)
sells = [z for z in pre_all if z[2][1] == "SELL"]; print("pre-bot sells:", len(sells), sells[:5])
cnt = collections.Counter((z[2][4], round(z[2][2], 7)) for z in pre_all if z[2][1] == "BUY"); print("pre-bot small buys by (via, size):", cnt.most_common(12))
gaps = sorted(rows[i + 1]["b0"] - rows[i]["b0"] for i in range(n - 1)); print("launch gaps: median", q(gaps, .5), "min", gaps[0])
json.dump(rows, open(os.path.join(HERE, "census_s.json"), "w"), indent=0, default=str)
