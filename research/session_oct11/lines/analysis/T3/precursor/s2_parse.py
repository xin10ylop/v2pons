"""Stage 2: per pool, the swaps with their transactions (who/where/selector/nonce), T = the block offset of the bot's first buy (a buy whose tx calls
the bot's router 0x1cbaf24d with c1120e3d), its wallet, nonce, size; the bot's later buys; pulls (ModifyLiquidity with negative delta, offset and tx).
-> parsed.pkl (both lines; the 2.4333 pools are used only for the bot wallets' history and the cross-pool schedule)."""
import json, pickle, collections
from lib import *
D = json.load(open("pools.json")); kv_tx = KV("tx")
def word(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)
P = []
for p in D["pools"]:
    sw = []; ml = []
    for e in p["ev"]:
        t = kv_tx.d.get(e["tx"]) or {}
        base = {"bn": e["bn"], "off": e["bn"] - p["L"], "ti": e["ti"], "li": e["li"], "tx": e["tx"], "eoa": (t.get("from") or "").lower(), "to": (t.get("to") or "").lower(),
                "sel": (t.get("input") or "")[2:10], "nonce": int(t["nonce"], 16) if t.get("nonce") else None, "have_tx": bool(t)}
        if e["kind"] == "swap":
            a0 = sgn(W(e["data"], 0)); a1 = sgn(W(e["data"], 1))
            r = dict(base, buy=a0 < 0, q=abs(a0), t=abs(a1), sp=W(e["data"], 2), Lq=W(e["data"], 3))
            r["bot"] = r["buy"] and r["to"] == BOT and r["sel"] == "c1120e3d"
            if r["bot"] and len(t.get("input", "")) >= 10 + 64 * 5: r["args"] = [word(t["input"], i) for i in range(min(12, (len(t["input"]) - 10) // 64))]
            sw.append(r)
        else:
            ml.append(dict(base, dL=sgn(W(e["data"], 2))))
    bots = [s for s in sw if s["bot"]]
    pulls = [m for m in ml if m["dL"] < 0]
    q = dict(p); del q["ev"]
    q.update(sw=sw, ml=ml, T=bots[0]["off"] if bots else None, Tbn=bots[0]["bn"] if bots else None, Tti=bots[0]["ti"] if bots else None,
             buyer=bots[0]["eoa"] if bots else None, buyer_nonce=bots[0]["nonce"] if bots else None, Tq=bots[0]["q"] / 1e18 if bots else None,
             bot2=bots[1]["off"] if len(bots) > 1 else None, nbot=len(bots), pull=pulls[0]["off"] if pulls else None, pull_tx=pulls[0] if pulls else None)
    P.append(q)
pickle.dump({"head": D["head"], "head_ts": D["head_ts"], "bps": D["bps"], "pools": P}, open("parsed.pkl", "wb"))
for line in ("3.0", "2.433"):
    G = [p for p in P if p["line"] == line]; Ts = [p["T"] for p in G if p["T"] is not None]
    print(f"{line}: pools {len(G)}, with a bot buy {len(Ts)}, T p10/50/90 {pct(Ts,.1)}/{pct(Ts,.5)}/{pct(Ts,.9)} min {min(Ts) if Ts else None} max {max(Ts) if Ts else None}; "
          f"missing txs {sum(1 for p in G for s in p['sw'] if not s['have_tx'])}; pulled {sum(1 for p in G if p['pull'] is not None)}")
