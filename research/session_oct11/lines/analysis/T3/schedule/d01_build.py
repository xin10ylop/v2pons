"""Build the dataset from logs/: per bot-served pool (launched in the window) L, line, fee, launch tx (sender, nonce), every swap with its
label (bot buy / bot pull / sentinel / other), pulls; and the global time-ordered list of bot actions (every PM->bot-router token transfer,
classified buy / pull by the pool's Swap / ModifyLiquidity log in the same tx; wallet from the router's forward transfer). -> data.pkl"""
import json, collections, pickle
from rpc import TxCache
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x, bits=256): return x - (1 << bits) if x >= (1 << (bits - 1)) else x
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"; SENT = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
meta = json.load(open("cache/logs/meta.json"))
init = {}
for l in open("cache/logs/init.jsonl"):
    x = json.loads(l); init["0x" + x["t"][3][-40:]] = x
pm2bot = [json.loads(l) for l in open("cache/logs/pm2bot.jsonl")]
fwd = {}
for l in open("cache/logs/bot2any.jsonl"):
    x = json.loads(l); fwd.setdefault(x["tx"], x)
pev = collections.defaultdict(lambda: {"sw": [], "ml": [], "tr": []})
pid2tok = {x["t"][1]: t for t, x in init.items()}
for l in open("cache/logs/pool.jsonl"):
    x = json.loads(l)
    if x["k"] in ("sw", "ml"): pev[pid2tok[x["t"][1]]][x["k"]].append(x)
    else: pev[x["addr"]]["tr"].append(x)
toks = sorted(set(x["addr"] for x in pm2bot) & set(t for t, x in init.items() if x["bn"] >= meta["start"]), key=lambda t: (init[t]["bn"], init[t]["li"]))
txc = TxCache("txcache.jsonl")
lt = txc.get([init[t]["tx"] for t in toks])
LINE = {2433328500000000000: "2.433", 3 * 10 ** 18: "3.0", 5 * 10 ** 18: "5.0"}
swtx = {}; mltx = {}
for t in toks:
    for s in pev[t]["sw"]: swtx[s["tx"]] = s
    for m in pev[t]["ml"]: mltx[m["tx"]] = m
acts = []
for x in pm2bot:
    s = swtx.get(x["tx"]); m = mltx.get(x["tx"]); f = fwd.get(x["tx"])
    kind = "buy" if s is not None and sgn(W(s["data"], 0)) < 0 else "pull" if m is not None and sgn(W(m["data"], 2)) < 0 else "?"
    acts.append({"bn": x["bn"], "ti": x["ti"], "li": x["li"], "tx": x["tx"], "token": x["addr"], "kind": kind,
                 "eth": abs(sgn(W(s["data"], 0))) / 1e18 if s is not None else None, "wallet": ("0x" + f["t"][2][-40:]) if f else None})
acts.sort(key=lambda a: (a["bn"], a["ti"]))
pools = []
for t in toks:
    x = init[t]; tx = lt.get(x["tx"]) or {}; d = x["data"]; L = x["bn"]
    bt = set(a["tx"] for a in acts if a["token"] == t)
    sw = []
    for s in sorted(pev[t]["sw"], key=lambda s: (s["bn"], s["li"])):
        a0 = sgn(W(s["data"], 0)); a1 = sgn(W(s["data"], 1))
        sw.append({"bn": s["bn"], "off": s["bn"] - L, "ti": s["ti"], "li": s["li"], "tx": s["tx"], "buy": a0 < 0, "q": abs(a0) / 1e18, "t": abs(a1),
                   "sp": W(s["data"], 2), "L": W(s["data"], 3), "bot": s["tx"] in bt})
    ml = [{"bn": m["bn"], "off": m["bn"] - L, "ti": m["ti"], "dL": sgn(W(m["data"], 2)), "tx": m["tx"], "bot": m["tx"] in bt} for m in sorted(pev[t]["ml"], key=lambda m: (m["bn"], m["li"]))]
    # recipients of token transfers out of the PM / UR in each swap tx (the buyer for non-bot buys)
    rcpt = collections.defaultdict(list)
    for r in pev[t]["tr"]: rcpt[r["tx"]].append(("0x" + r["t"][1][-40:], "0x" + r["t"][2][-40:], int(r["data"], 16)))
    bots = [s for s in sw if s["bot"] and s["buy"]]
    pulls = [m for m in ml if m["dL"] < 0]
    pools.append({"token": t, "pid": x["t"][1], "L": L, "Lti": x["ti"], "Lli": x["li"], "ltx": x["tx"], "fee": W(d, 0), "tsp": sgn(W(d, 1)), "sp0": W(d, 3),
                  "line": LINE.get(int(tx.get("value") or "0x0", 16), "?"), "posm": (tx.get("to") or "").lower() == POSM, "clen": (len(tx.get("input") or "0x") - 2) // 2,
                  "lfrom": (tx.get("from") or "").lower(), "lnonce": int(tx["nonce"], 16) if tx.get("nonce") else None, "lgas": tx.get("gasPrice"),
                  "sw": sw, "ml": ml, "rcpt": dict(rcpt), "T": bots[0]["off"] if bots else None, "Tbn": bots[0]["bn"] if bots else None,
                  "Tti": bots[0]["ti"] if bots else None, "Ttx": bots[0]["tx"] if bots else None, "Teth": bots[0]["q"] if bots else None,
                  "pull": pulls[0]["off"] if pulls else None, "pull_bot": pulls[0]["bot"] if pulls else None, "span": min(400, meta["head"] - L)})
pickle.dump({"meta": meta, "pools": pools, "acts": acts}, open("cache/data.pkl", "wb"))
print(len(pools), "pools:", collections.Counter((p["line"], p["fee"], p["tsp"], p["posm"], p["clen"]) for p in pools))
print("actions:", collections.Counter(a["kind"] for a in acts), "wallets:", len(set(a["wallet"] for a in acts if a["kind"] == "buy")))
print("pools with T:", collections.Counter((p["line"], p["T"] is not None) for p in pools))
print("first pulls by bot router:", collections.Counter((p["line"], p["pull_bot"]) for p in pools if p["pull"] is not None))
