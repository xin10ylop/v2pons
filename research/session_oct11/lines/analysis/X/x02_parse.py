"""Parse x01's raw logs + txcache into per-pool records (x02_pools.pkl) and our trades (x02_trades.json).
Per swap: offset from launch, buy/sell, ETH (q), tokens (t), sqrtP/L after, the tx's from/to/nonce/selector/tip; who:
ours (relay is the Swap sender or our wallet sent it), bot (a buy whose tx calls the bot's router with c1120e3d), botsell (a sell by a bot
buyer wallet), sentinel (0xe71a69f4 dust bot), else 'w' (classified later). Pools: T (the bot's first buy), its size, its later buys,
first pull (a ModifyLiquidity with negative liquidity) and the pull tx's shape."""
import json, pickle, collections, os, sys
from xcommon import *
meta = json.load(open("x01_meta.json")); pools = json.load(open("x01_pools.json")); ev = json.load(open("x01_ev.json")); ours_logs = json.load(open("x01_ours.json"))
tx = {}
for l in open("txcache.jsonl"):
    x = json.loads(l); tx[x["hash"]] = x
TXSPAN = 400
head = meta["head"]
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
out = []
for p in pools:
    es = sorted(ev.get(p["pid"], []), key=lambda e: (e["bn"], e["li"]))
    sw, ml = [], []
    for e in es:
        t = tx.get(e["tx"]) or {}
        base = {"bn": e["bn"], "off": e["bn"] - p["lb"], "li": e["li"], "ti": e["ti"], "tx": e["tx"], "sender": e["sender"].lower(), "eoa": (t.get("from") or "").lower(),
                "to": (t.get("to") or "").lower(), "nonce": int(t["nonce"], 16) if t.get("nonce") else None, "sel": (t.get("input") or "")[2:10],
                "clen": (len(t.get("input") or "0x") - 2) // 2, "tip": int(t["maxPriorityFeePerGas"], 16) if t.get("maxPriorityFeePerGas") else None,
                "gp": int(t["gasPrice"], 16) if t.get("gasPrice") else None, "gas": int(t["gas"], 16) if t.get("gas") else None, "value": int(t["value"], 16) if t.get("value") else 0,
                "has_tx": bool(t)}
        d = e["data"]
        if e["k"] == "sw":
            a0 = s128(W(d, 0)); a1 = s128(W(d, 1))
            r = dict(base, buy=a0 < 0, q=abs(a0), t=abs(a1), sp=W(d, 2), L=W(d, 3), tick=sgn(W(d, 4)), fee_ev=W(d, 5), minout=None)
            inp = t.get("input") or ""
            if r["to"] == BOT and r["sel"] == "c1120e3d" and len(inp) >= 10 + 64 * 5: r["minout"] = word(inp, 4)
            r["mentions_us"] = (OURS[2:] in inp.lower()) or (RELAY[2:] in inp.lower())
            sw.append(r)
        else:
            ml.append(dict(base, lo=sgn(W(d, 0)), hi=sgn(W(d, 1)), dL=sgn(W(d, 2))))
    adds = [m for m in ml if m["dL"] > 0]; pulls = [m for m in ml if m["dL"] < 0]
    out.append(dict(p, sw=sw, ml=ml, L0=adds[0]["dL"] if adds else 0, pull=pulls[0]["off"] if pulls else None, pull_m=pulls[0] if pulls else None,
                    span=min(1200, head - p["lb"])))
# bot buyer wallets: wallets that bought through the bot's router (c1120e3d) in >= 3 pools
c = collections.Counter()
for p in out:
    for w in set(s["eoa"] for s in p["sw"] if s["to"] == BOT and s["sel"] == "c1120e3d" and s["buy"]): c[w] += 1
botw = {w for w, n in c.items() if n >= 3}
for p in out:
    for s in p["sw"]:
        if s["sender"] == RELAY or s["eoa"] == OURS or s["to"] == RELAY: s["who"] = "ours"
        elif s["buy"] and s["to"] == BOT and s["sel"] == "c1120e3d": s["who"] = "bot"
        elif s["eoa"] in botw: s["who"] = "botsell" if not s["buy"] else "botother"
        elif s["eoa"] == SENTINEL: s["who"] = "sentinel"
        elif not s["has_tx"]: s["who"] = "notx"
        else: s["who"] = "w"
    bots = [s for s in p["sw"] if s["who"] == "bot"]
    p["T"] = bots[0]["off"] if bots else None; p["T_q"] = bots[0]["q"] if bots else None
    p["T_li"] = (bots[0]["bn"], bots[0]["li"]) if bots else None
    p["bot_buys"] = [(s["off"], s["q"]) for s in bots]
    p["ours"] = any(s["who"] == "ours" for s in p["sw"])
    p["period"] = period(p["ts"])
pickle.dump({"pools": out, "botw": sorted(botw), "botw_counts": dict(c), "meta": meta}, open("x02_pools.pkl", "wb"))
print(len(out), "pools;", collections.Counter((p["line"], p["period"]) for p in out))
print("bot buyer wallets (>=3 pools):", len(botw), "; wallets with 1-2 pools via the bot router:", sum(1 for w, n in c.items() if n < 3))
print("fees/ts:", collections.Counter((p["line"], p["fee"], p["tsp"]) for p in out))
# our trades from the relay's swap logs
pb = {p["pid"]: p for p in out}
rows = []
for l in ours_logs:
    t = tx.get(l["transactionHash"]) or {}; d = l["data"]
    rows.append({"bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "ti": int(l["transactionIndex"], 16), "pid": l["topics"][1], "a0": s128(W(d, 0)), "a1": s128(W(d, 1)),
                 "sp": W(d, 2), "L": W(d, 3), "fee_ev": W(d, 5), "tx": l["transactionHash"], "eoa": (t.get("from") or "").lower(), "nonce": int(t["nonce"], 16) if t.get("nonce") else None,
                 "sel": (t.get("input") or "")[2:10]})
rows.sort(key=lambda r: (r["bn"], r["li"]))
tr = collections.OrderedDict()
for r in rows:
    x = tr.setdefault(r["pid"], {"pid": r["pid"], "buys": [], "sells": []})
    (x["buys"] if r["a0"] < 0 else x["sells"]).append(r)
trades = []
for pid, x in tr.items():
    p = pb.get(pid)
    b = x["buys"][0] if x["buys"] else None; s = x["sells"][0] if x["sells"] else None
    trades.append({"pid": pid, "line": p["line"] if p else "other", "lb": p["lb"] if p else None, "ts": p["ts"] if p else None, "fee": p["fee"] if p else None,
                   "buy_bn": b["bn"] if b else None, "buy_li": b["li"] if b else None, "sell_bn": s["bn"] if s else None, "sell_li": s["li"] if s else None,
                   "eth_in": -b["a0"] if b else 0, "eth_out": s["a0"] if s else None, "tok": b["a1"] if b else None, "tok_sold": -s["a1"] if s else None,
                   "n_buys": len(x["buys"]), "n_sells": len(x["sells"]), "eoa": b["eoa"] if b else None, "buy_tx": b["tx"] if b else None, "sell_tx": s["tx"] if s else None})
json.dump(trades, open("x02_trades.json", "w"), indent=0)
print("our relay trades:", len(trades), collections.Counter(t["line"] for t in trades))
