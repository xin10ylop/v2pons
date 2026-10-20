"""Parse chain_raw.json + txcache.jsonl into per-pool records shaped like the census ones (cpools.pkl) -> chpools.pkl.
Labels: bot (buy whose tx calls the bot's router 0x1cbaf24d from a recurring bot wallet), botsell (a sell from a bot wallet),
ours (our wallet / relay), sentinel (0xe71a69f4), else the wallet itself (classified later)."""
import json, pickle, collections
from common import *
raw = json.load(open("chain_raw.json"))
tx = {}
for l in open("txcache.jsonl"):
    x = json.loads(l); tx[x["hash"]] = x
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x, bits=256): return x - (1 << bits) if x >= (1 << (bits - 1)) else x
def word(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)
pools = []
for p in raw["pools"]:
    e = raw["ev"][p["pid"]]; lb = p["lb"]
    sw = []
    for s in sorted(e["sw"], key=lambda s: (s["bn"], s["li"])):
        d = s["data"]; a0 = sgn(W(d, 0)); a1 = sgn(W(d, 1)); t = tx.get(s["tx"]) or {}
        r = {"bn": s["bn"], "off": s["bn"] - lb, "li": s["li"], "ti": s["ti"], "tx": s["tx"], "buy": a0 < 0, "q": abs(a0), "t": abs(a1), "sp": W(d, 2), "L": W(d, 3),
             "fee_ev": W(d, 5), "router": s["sender"], "eoa": (t.get("from") or "").lower(), "to": (t.get("to") or "").lower(), "nonce": int(t["nonce"], 16) if t.get("nonce") else None,
             "sel": (t.get("input") or "")[2:10], "clen": (len(t.get("input") or "0x") - 2) // 2, "minout": None}
        if r["to"] == BOT and r["sel"] == "c1120e3d" and len(t.get("input", "")) >= 10 + 64 * 5: r["minout"] = word(t["input"], 4)
        sw.append(r)
    ml = []
    for m in sorted(e["ml"], key=lambda s: (s["bn"], s["li"])):
        d = m["data"]; t = tx.get(m["tx"]) or {}
        ml.append({"bn": m["bn"], "off": m["bn"] - lb, "lo": sgn(W(d, 0)), "hi": sgn(W(d, 1)), "dL": sgn(W(d, 2)), "eoa": (t.get("from") or "").lower(),
                   "to": (t.get("to") or "").lower(), "sel": (t.get("input") or "")[2:10], "tx": m["tx"]})
    adds = [m for m in ml if m["dL"] > 0]; pulls = [m for m in ml if m["dL"] < 0]
    pools.append(dict(p, sw=sw, ml=ml, L0=adds[0]["dL"] if adds else 0, pulls=[m["off"] for m in pulls], pull=pulls[0]["off"] if pulls else None,
                      pull_tx=pulls[0] if pulls else None, span=min(400, raw["head"] - lb)))
# bot wallets: wallets that bought through the bot's router in >= 3 pools of this window
c = collections.Counter()
for p in pools:
    for w in set(s["eoa"] for s in p["sw"] if s["to"] == BOT and s["buy"]): c[w] += 1
botw = {w for w, n in c.items() if n >= 3}
print("wallets buying through the bot router:", len(c), "recurring (>=3 pools):", len(botw), "one/two-pool:", sorted((w[:10], n) for w, n in c.items() if n < 3)[:20])
for p in pools:
    for s in p["sw"]:
        if s["eoa"] == OURS or s["to"] == RELAY: s["who"] = "ours"
        elif s["buy"] and s["to"] == BOT and s["eoa"] in botw: s["who"] = "bot"
        elif (not s["buy"]) and s["eoa"] in botw: s["who"] = "botsell"
        elif s["eoa"] == SENTINEL: s["who"] = "sentinel"
        else: s["who"] = "w"
    bots = [s for s in p["sw"] if s["who"] == "bot"]
    p["T"] = bots[0]["off"] if bots else None
    p["ours"] = any(s["who"] == "ours" for s in p["sw"])
    p["day"] = 7; p["fee"] = p["fee"]
    p["regime"] = (("2.433 fee2500" if p["fee"] == 2500 else ("2.433 fee5000<16:28" if p["ts"] < DECOY_FILL else "2.433 fee5000>=16:28")) if p["line"] == "2.433" else "3.0 new")
pickle.dump({"pools": pools, "botw": botw, "head": raw["head"], "head_ts": raw["head_ts"], "bps": raw["bps"], "start": raw["start"]}, open("chpools.pkl", "wb"))
print(len(pools), "pools;", collections.Counter((p["regime"], p["ours"], p["T"] is not None) for p in pools))
print("fees:", collections.Counter((p["line"], p["fee"], p["ts_"]) for p in pools))
