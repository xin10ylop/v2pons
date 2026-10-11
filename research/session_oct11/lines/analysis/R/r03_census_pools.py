"""Census: label every swap of the v2.433 / v3.0 pools (first 12 swaps from their transactions; later swaps by router + size heuristic),
find the bot's first buy T, its later buys and sells, the pulls -> cpools.pkl (list of per-pool dicts)."""
import json, pickle, collections
from common import *
R = [json.loads(l) for l in open("vrows.jsonl")]
R = [r for r in R if r["known_fp"] in ("vbot-v2.433", "vbot-v3.0")]
E = pickle.load(open("ev.pkl", "rb"))
botw = set(s[3] for r in R for s in r.get("swaps12") or [] if s[4] == BOT)
# repeat actors: (eoa) seen buying in >= 20 line pools (not bot, not ours): the operator's dust/decoy crowd or repeat bots
cnt = collections.Counter()
for r in R:
    for e in set(s[3] for s in r.get("swaps12") or [] if s[1] == "B" and s[4] != BOT): cnt[e] += 1
repeat = {e for e, n in cnt.items() if n >= 20 and e != OURS}
out = []
for r in R:
    o = E[r["pool"]]; lb = r["launch_block"]; sw = o["sw"]; s12 = r.get("swaps12") or []
    for i, s in enumerate(sw):
        s["off"] = s["bn"] - lb
        if i < len(s12):
            x = s12[i]; s["eoa"] = x[3]; s["to"] = x[4]; s["src"] = "tx"
            if x[4] == BOT and s["buy"]: s["who"] = "bot"
            elif (not s["buy"]) and x[3] in botw: s["who"] = "botsell"
            elif x[3] == OURS or x[4] == RELAY: s["who"] = "ours"
            elif x[3] in repeat: s["who"] = "rep"
            else: s["who"] = "x"
        else:
            s["eoa"] = None; s["to"] = None; s["src"] = "heur"
            if s["router"] == RELAY: s["who"] = "ours"
            elif s["router"] == UR and s["buy"] and s["q"] >= 0.021e18: s["who"] = "bot"
            elif s["router"] == UR and (not s["buy"]) and s["q"] >= 0.0002e18: s["who"] = "botsell"
            elif s["router"] == UR: s["who"] = "x?"           # a small Universal Router swap of unknown wallet
            else: s["who"] = "r?"                               # a swap through another contract router (decoy/dust routers, other bots)
    bots = [s for s in sw if s["who"] == "bot"]
    T = bots[0]["off"] if bots and bots[0]["src"] == "tx" else (bots[0]["off"] if bots else None)
    pulls = sorted(p["bn"] - lb for p in o["pulls"])
    add = o["adds"][0] if o["adds"] else None
    out.append({"pool": r["pool"], "line": "2.433" if r["known_fp"] == "vbot-v2.433" else "3.0", "lb": lb, "ts": r["launch_ts"],
                "day": int((r["launch_ts"] - CENSUS_START) // 86400), "fee": r["fee"], "sp0": r["sqrt_p0"], "L0": add["L"] if add else 0,
                "ev_to_off": o["ev_to"] - lb, "complete": r["ev_complete"], "n12": len(s12), "sw": sw, "T": T, "T_src": bots[0]["src"] if bots else None,
                "pulls": pulls, "pull": pulls[0] if pulls else None, "ours": bool(r.get("ours")) or any(s["who"] == "ours" for s in sw)})
pickle.dump(out, open("cpools.pkl", "wb"))
print(len(out), "pools; bot wallets", len(botw), "; repeat actors", len(repeat))
c = collections.Counter((p["line"], p["T_src"]) for p in out); print(c)
