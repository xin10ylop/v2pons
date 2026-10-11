"""Parse the 3.0 pools: swaps (buy/sell, ETH, tokens, sqrtP and liquidity after), liquidity calls (adds / pulls), each event's transaction
(from, to, selector, nonce), and a class per swap:
  bot      a buy through the bot's router 0x1cbaf24d (selector c1120e3d); its from = a bot wallet
  botsell  a sell from a bot wallet
  sentinel 0xe71a69f4 (the operator's +3 dust)
  ours     our wallet 0xab5a34c3 or our relay 0x2abb5653
  out      everything else (outside buys / sells)
-> cache/parsed.pkl (list of pool dicts)."""
import json, os, pickle, collections
from lib import *
E = json.load(open(os.path.join(CACHE, "events.json"))); kv_tx = KV("tx"); TX = kv_tx.d
def s128(x):
    x = x & ((1 << 256) - 1); x = sgn(x)
    return x
pools = []; botw = set(); miss = collections.Counter()
for p in E["pools"]:
    L = p["L"]; sw = []; ml = []
    for e in p["ev"]:
        t = TX.get(e["tx"])
        if t is None: miss[e["kind"] + ("-bot" if e["sender"] == BOT else "")] += 1
        info = {"from": (t["from"] or "").lower(), "to": (t.get("to") or "").lower(), "sel": (t["input"] or "")[2:10], "nonce": int(t["nonce"], 16),
                "value": int(t["value"], 16), "ilen": (len(t["input"]) - 2) // 2, "input": t["input"]} if t else None
        d = e["data"]
        if e["kind"] == "swap":
            a0 = s128(W(d, 0)); a1 = s128(W(d, 1))
            sw.append({"bn": e["bn"], "off": e["bn"] - L, "li": e["li"], "ti": e["ti"], "tx": e["tx"], "sender": e["sender"], "buy": a0 < 0, "q": abs(a0), "t": abs(a1),
                       "sp": W(d, 2), "L": W(d, 3), "tick": sgn(W(d, 4)), "fee": W(d, 5), "txi": info})
        else:
            ml.append({"bn": e["bn"], "off": e["bn"] - L, "li": e["li"], "ti": e["ti"], "tx": e["tx"], "sender": e["sender"], "lo": sgn(W(d, 0)), "hi": sgn(W(d, 1)),
                       "delta": sgn(W(d, 2)), "txi": info})
    for s in sw:
        i = s["txi"]
        if s["buy"] and s["sender"] == BOT and (i is None or (i["to"] == BOT and i["sel"] == "c1120e3d")):
            s["cls"] = "bot"
            if i: botw.add(i["from"])
    pools.append({k: p[k] for k in ("pid", "token", "L", "lti", "ts", "launch_tx", "launcher", "launcher_nonce", "span")} | {"sw": sw, "ml": ml})
for p in pools:
    for s in p["sw"]:
        if s.get("cls") == "bot": continue
        i = s["txi"]
        if i is None: s["cls"] = "?"
        elif i["from"] == SENTINEL: s["cls"] = "sentinel"
        elif i["from"] == OURS or i["to"] == RELAY or s["sender"] == RELAY: s["cls"] = "ours"
        elif i["from"] in botw: s["cls"] = "botbuy-other" if s["buy"] else "botsell"
        elif i["from"] == p["launcher"]: s["cls"] = "launcher"
        else: s["cls"] = "out"
    bots = [s for s in p["sw"] if s["cls"] == "bot"]
    p["T"] = bots[0]["off"] if bots else None
    p["bot_offs"] = [s["off"] for s in bots]
    pulls = [m for m in p["ml"] if m["delta"] < 0]; adds = [m for m in p["ml"] if m["delta"] > 0]
    p["pulls"] = pulls; p["adds"] = adds
    p["pull"] = pulls[0]["off"] if pulls else None
pickle.dump({"pools": pools, "botw": sorted(botw), "head": E["head"]}, open(os.path.join(CACHE, "parsed.pkl"), "wb"))
print("pools", len(pools), "bot wallets", len(botw), "missing txs by kind", dict(miss))
print("classes:", collections.Counter((s["cls"], s["buy"]) for p in pools for s in p["sw"]))
