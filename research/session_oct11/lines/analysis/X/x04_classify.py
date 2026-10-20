"""Question 2 groundwork: classify every pool's buyers ahead of the bot's first buy (T) and record the operator's reaction.
Buyer classes (for buys strictly ahead of the bot's first buy in chain order; the dust sentinel 0xe71a69f4 and bot wallets excluded):
  ours      our relay
  decoy     a fresh wallet (nonce 0 or 1 at that buy) buying 0.0046-0.0053 ETH
  dust      under 0.00003 ETH
  stranger  anyone else (with the wallet's own pool count and size, so recurring small wallets can be told apart later)
Pool class: ours > stranger > decoy-only > nobody.  Reaction: first pull offset, pull - T, pull - first stranger/our buy, the bot's
2nd buy (offset), the bot's first-buy size, and whether the stranger sold before the pull (and when, relative to T).
Writes x04_pools.json (one compact row per pool) and x04_buys.json (every non-bot buy ahead of T and up to T+60)."""
import json, pickle, collections
from xcommon import *
D = pickle.load(open("x02_pools.pkl", "rb")); pools = D["pools"]
DEC_LO, DEC_HI, DUST = int(0.0046e18), int(0.0053e18), int(0.00003e18)
wallet_pools = collections.Counter()
for p in pools:
    for w in set(s["eoa"] for s in p["sw"] if s["who"] == "w" and s["buy"]): wallet_pools[w] += 1
def bclass(s):
    if s["who"] == "ours": return "ours"
    if s["q"] < DUST: return "dust"
    if DEC_LO <= s["q"] <= DEC_HI and (s["nonce"] is not None and s["nonce"] <= 1): return "decoy"
    return "stranger"
rows, buys = [], []
for p in pools:
    sw = p["sw"]; T = p["T"]; Tli = p["T_li"]
    ahead = [s for s in sw if s["buy"] and s["who"] in ("ours", "w") and (Tli is None or (s["bn"], s["li"]) < Tli) and s["off"] <= (T if T is not None else 60)]
    late = [s for s in sw if s["buy"] and s["who"] in ("ours", "w") and Tli is not None and (s["bn"], s["li"]) > Tli and s["off"] <= T + 60]
    cls = [bclass(s) for s in ahead]
    pc = "ours" if "ours" in cls else "stranger" if "stranger" in cls else "decoy" if "decoy" in cls else "nobody"
    first_str = next((s for s, c in zip(ahead, cls) if c in ("ours", "stranger")), None)
    bb = p["bot_buys"]
    second = bb[1][0] if len(bb) > 1 else None
    pull = p["pull"]
    # sells by the ahead buyers (their own wallet) before the pull
    sells = {}
    for s in sw:
        if not s["buy"] and s["who"] in ("ours", "w"):
            sells.setdefault("ours" if s["who"] == "ours" else s["eoa"], []).append(s["off"])
    for s, c in zip(ahead, cls):
        key = "ours" if c == "ours" else s["eoa"]
        so = sells.get(key, [None])[0]
        buys.append({"pid": p["pid"], "line": p["line"], "ts": p["ts"], "period": p["period"], "fee": p["fee"], "where": "ahead", "cls": c, "eoa": s["eoa"], "to": s["to"], "sel": s["sel"],
                     "nonce": s["nonce"], "off": s["off"], "q": s["q"], "T": T, "pull": pull, "sell_off": so, "wallet_pools": wallet_pools.get(s["eoa"], 0), "pc": pc, "ti": s["ti"], "bn": s["bn"],
                     "tip": s["tip"], "gas": s["gas"], "clen": s["clen"], "sender": s["sender"]})
    for s in late:
        c = bclass(s); key = "ours" if c == "ours" else s["eoa"]
        buys.append({"pid": p["pid"], "line": p["line"], "ts": p["ts"], "period": p["period"], "fee": p["fee"], "where": "after", "cls": c, "eoa": s["eoa"], "to": s["to"], "sel": s["sel"],
                     "nonce": s["nonce"], "off": s["off"], "q": s["q"], "T": T, "pull": pull, "sell_off": sells.get(key, [None])[0], "wallet_pools": wallet_pools.get(s["eoa"], 0), "pc": pc,
                     "ti": s["ti"], "bn": s["bn"], "tip": s["tip"], "gas": s["gas"], "clen": s["clen"], "sender": s["sender"]})
    rows.append({"pid": p["pid"], "line": p["line"], "ts": p["ts"], "period": p["period"], "lb": p["lb"], "fee": p["fee"], "tsp": p["tsp"], "T": T, "T_q": p["T_q"], "n_bot": len(bb),
                 "second": second, "pull": pull, "pull_to": p["pull_m"]["to"] if p["pull_m"] else None, "pull_sel": p["pull_m"]["sel"] if p["pull_m"] else None,
                 "pc": pc, "n_decoy": cls.count("decoy"), "n_stranger": cls.count("stranger"), "ours": "ours" in cls, "ours_any": p["ours"],
                 "first_str_off": first_str["off"] if first_str else None, "first_str_q": first_str["q"] if first_str else None, "first_str_who": ("ours" if first_str and first_str["who"] == "ours" else first_str["eoa"]) if first_str else None,
                 "late_stranger": [(s["off"], s["q"], s["eoa"][:10]) for s in late if bclass(s) == "stranger"], "span": p["span"],
                 "decoy_offs": [s["off"] for s, c in zip(ahead, cls) if c == "decoy"], "ahead_eth": sum(s["q"] for s in ahead) / 1e18,
                 "launcher_nonce": p["nonce"], "launcher": p["from"]})
json.dump(rows, open("x04_pools.json", "w")); json.dump(buys, open("x04_buys.json", "w"))
print("pools", len(rows), collections.Counter((r["line"], r["pc"]) for r in rows))
