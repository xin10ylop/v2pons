"""operator reaction (own code): every non-bot buy >= 0.0002 ETH before the pull, in the 24 h census + the window; lag to the pull"""
import sys, os, pickle, json, collections, statistics as st, datetime
SCR = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"; sys.path.insert(0, SCR)
from chain import T_SWAP, T_ML, W, sgn, batch
HERE = os.path.dirname(os.path.abspath(__file__))
C = pickle.load(open(os.path.join(HERE, "census_s.pkl"), "rb")); D = pickle.load(open(os.path.join(HERE, "data_s.pkl"), "rb"))
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
TXP = os.path.join(HERE, "txs_react.pkl")
txs = pickle.load(open(TXP, "rb")) if os.path.exists(TXP) else {}
txs.update(C["txs"]); txs.update(D["txs"])
fam = C["fam"] + [{"pid": x["pid"], "bn": x["bn"]} for x in D["fam"]]
by = collections.defaultdict(list)
for l in C["plogs"] + D["logs"]: by[l["topics"][1]].append(l)
def s128(v):
    v = sgn(v); return v - (1 << 128) if v >= (1 << 127) else v
t_of = lambda b: (datetime.datetime(2026, 10, 10, 8, 24, 24) + datetime.timedelta(seconds=(b - 84855917) * 0.1035)).strftime("%m-%d %H:%M")
P = []
for x in fam:
    seen = set(); ev = []
    for l in sorted(by[x["pid"]], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
        k = (l["transactionHash"], l["logIndex"])
        if k in seen: continue
        seen.add(k); bn = int(l["blockNumber"], 16)
        if l["topics"][0] == T_ML:
            if bn == x["bn"]: continue
            if sgn(W(l["data"], 2)) < 0: ev.append({"bn": bn, "kind": "pull"}); break
            continue
        a0 = s128(W(l["data"], 0))
        ev.append({"bn": bn, "kind": "buy" if a0 < 0 else "sell", "eth": abs(a0), "tx": l["transactionHash"]})
    P.append({"pid": x["pid"], "b0": x["bn"], "ev": ev})
need = sorted({e["tx"] for p in P for e in p["ev"] if e["kind"] == "buy" and e["eth"] >= int(0.0002e18) and e["tx"] not in txs})
print("fetch", len(need))
for i in range(0, len(need), 500):
    for h, t in zip(need[i:i+500], batch([("eth_getTransactionByHash", [h]) for h in need[i:i+500]])): txs[h] = t
    pickle.dump(txs, open(TXP, "wb"))
rows = []
for p in P:
    pull = next((e["bn"] for e in p["ev"] if e["kind"] == "pull"), None)
    fbot = None
    for e in p["ev"]:
        if e["kind"] != "buy": continue
        t = txs.get(e["tx"])
        bot = t is not None and (t["to"] or "").lower() == ROUTER and t["input"][:10] == "0xc1120e3d"
        if bot and fbot is None: fbot = e["bn"]
        if not bot and e["eth"] >= int(0.0002e18):
            rows.append({"pid": p["pid"][:10], "b0": p["b0"], "time": t_of(p["b0"]), "off": e["bn"] - p["b0"], "eth": e["eth"] / 1e18, "from": t["from"].lower(), "to": (t["to"] or "").lower(),
                         "prebot": fbot is None, "bot": (fbot - p["b0"]) if fbot else None, "pull": (pull - p["b0"]) if pull else None, "lag": (pull - e["bn"]) if pull else None})
print("non-bot buys >= 0.0002 ETH before the pull:", len(rows))
first = {}
for r in rows:
    first.setdefault(r["pid"], r)
fr = list(first.values())
print("pools with one:", len(fr))
lags = sorted(r["lag"] for r in fr if r["lag"] is not None)
print("first such buy -> pull lag: ", lags)
print("  <=15:", sum(1 for v in lags if v <= 15), "of", len(lags))
for r in fr: print("   ", r["pid"], r["time"], "buy +%d %.5f ETH from %s via %s" % (r["off"], r["eth"], r["from"][:10], r["to"][:10]), "prebot" if r["prebot"] else "after bot +%s" % r["bot"], "pull +%s lag %s" % (r["pull"], r["lag"]))
c = collections.Counter(r["from"][:10] for r in rows); print("buyers:", c.most_common(15))
json.dump(rows, open(os.path.join(HERE, "react_s.json"), "w"), indent=0)
