"""Out-of-sample family launches (after the census): schedule, crowd, outsiders, pulls, and the claimed rules replayed."""
import sys, os, datetime; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from replay_s import *
from chain import T_SWAP, T_ML, W, sgn
D = os.path.join(HERE, "fresh"); fr = json.load(open(os.path.join(D, "fresh.json"))); TX = json.load(open(os.path.join(D, "txs.json")))
head = fr["head"]
by = collections.defaultdict(lambda: {"swaps": [], "adds": [], "pulls": []})
for e in fr["events"]:
    pid = e["topics"][1]; d = e["data"]; bn = int(e["blockNumber"], 16); li = int(e["logIndex"], 16); tx = e["transactionHash"]
    if e["topics"][0] == T_SWAP:
        by[pid]["swaps"].append({"bn": bn, "li": li, "a0": sgn(W(d, 0)), "a1": sgn(W(d, 1)), "sqrt_p": W(d, 2), "liq": W(d, 3), "tick": sgn(W(d, 4)), "fee": W(d, 5), "tx": tx, "sender": "0x" + e["topics"][2][-40:]})
    else:
        dl = sgn(W(d, 2)); row = {"bn": bn, "li": li, "lo": sgn(W(d, 0)), "hi": sgn(W(d, 1)), "dl": dl, "tx": tx}
        if dl > 0: by[pid]["adds"].append(row)
        elif dl < 0: by[pid]["pulls"].append(row)
rows = []; trades = collections.defaultdict(list)
for c in fr["fam"]:
    e = by[c["pid"]]
    for k in e: e[k].sort(key=lambda x: (x["bn"], x["li"]))
    if not e["adds"]: rows.append({"pid": c["pid"][:12], "status": "no add yet", "age": head - c["bn"]}); continue
    ad = e["adds"][0]; at = TX[ad["tx"]]; a = ad["bn"]
    sw = []
    for s in e["swaps"]:
        t = TX.get(s["tx"]); cl = classify({"from": t["from"], "to": t["to"]}) if t else "nofetch"
        sw.append({"off": s["bn"] - a, "buy": s["a0"] < 0, "eth": abs(s["a0"]) / 1e18, "cls": cl, "from": t["from"] if t else None, "to": t["to"] if t else None, "len": t["len"] if t else None})
    cb = [x for x in sw if x["cls"] == "crowd" and x["buy"]]
    oth = [(x["off"], round(x["eth"], 6), x["from"][:10], x["to"][:10]) for x in sw if x["buy"] and x["cls"] == "other"]
    pull = (e["pulls"][0]["bn"] - a) if e["pulls"] else None
    pt = TX.get(e["pulls"][0]["tx"]) if e["pulls"] else None
    r = {"pid": c["pid"][:12], "ts": None, "add_off": a - c["bn"], "add_from_is_dep": at["from"] == c["from"], "add_sel": at["sel"], "add_len": at["len"], "value": at["value"] / 1e18,
         "nonce": c["nonce"], "age_from_add": head - a, "crowd1": cb[0]["off"] if cb else None, "crowd_routers": sorted({x["to"][:10] for x in cb}),
         "crowd_n": len(cb), "outsider_buys": oth[:8], "pull": pull, "pull_by_dep": (pt["from"] == c["from"]) if pt else None, "sniper": sum(1 for x in sw if x["cls"] == "sniper")}
    rows.append(r)
    pl = Pool({"sqrt_p0": c["sqrt_p0"], "tick0": c["tick0"], "fee": 500}, {"adds": e["adds"], "swaps": e["swaps"], "pulls": e["pulls"]})
    if head - a >= 240:
        trades["ride +1->+180"].append(pl.trade(a + 1, a + 180))
        if r["crowd1"] is not None:
            trades["follow crowd1+1 hold 100"].append(pl.trade(a + r["crowd1"] + 1, a + r["crowd1"] + 101))
            trades["front +1 -> crowd1+1"].append(pl.trade(a + 1, a + min(r["crowd1"] + 1, 220)))
for r in rows: print(r)
for k, v in trades.items(): print(k, summ(v))
json.dump({"rows": rows, "trades": {k: summ(v) for k, v in trades.items()}}, open(os.path.join(HERE, "fresh_summary.json"), "w"), indent=1)
