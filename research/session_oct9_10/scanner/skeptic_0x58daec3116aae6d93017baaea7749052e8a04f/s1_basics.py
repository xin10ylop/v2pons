"""Skeptic step 1: the family's basic numbers from the raw census (pools, events, txs): sub-families by value, launch fingerprint,
the bot's first buy (router 0x1cbaf24d, c1120e3d) offset/size/minOut vs the launch-state quote, the pulls (offset, by whom), who buys before the bot."""
import sys, json, collections, statistics as st
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/src")
from load import *
import v4math
HERE = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/skeptic_0x58daec3116aae6d93017baaea7749052e8a04f"
K = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|10000|200|true"
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
P = load_pools(); F = load_families(); T = load_txs()
pids = F[K]["pids"]; E = load_events(set(pids))
def wd(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)
def q(v, ps=(0, .1, .5, .9, 1)):
    v = sorted(v); return [v[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))] for p in ps] if v else None
rows = []
for pid in pids:
    p = P[pid]; e = E[pid]; b0 = p["launch_block"]
    sub = {3 * 10**18: "v3.0", 5 * 10**18: "v5.0"}.get(p["launch_value_wei"], "v-other")
    sw = e["swaps"]
    seq = []
    for i, s in enumerate(sw):
        t = T.get(s["tx"])
        seq.append({"rank": i, "bn": s["bn"], "off": s["bn"] - b0, "li": s["li"], "buy": s["a0"] < 0, "eth": -s["a0"] / 1e18 if s["a0"] < 0 else s["a0"] / 1e18,
                    "a0": s["a0"], "a1": s["a1"], "sp": s["sqrt_p"], "L": s["liq"], "tx": s["tx"], "from": t["from"] if t else None, "to": t["to"] if t else None,
                    "sel": t["selector"] if t else None, "input": (t.get("input") or t.get("input512")) if t else None, "launch_tx": s["tx"] == p["launch_tx"]})
    bot = [x for x in seq if x["buy"] and x["to"] == ROUTER and x["sel"] == "c1120e3d"]
    fb = bot[0] if bot else None
    mo = wd(fb["input"], 4) if fb else None
    q0 = v4math.buy_out_int(p["sqrt_p0"], p["liq_launch"], -fb["a0"], p["fee"]) if fb else None
    pulls = e["pulls"]; pl = pulls[0] if pulls else None
    ptx = T.get(pl["tx"]) if pl else None
    rows.append({"pid": pid, "b0": b0, "ts": p["launch_ts"], "sub": sub, "value": p["launch_value_wei"], "from": p["launch_from"], "nonce": p["launch_nonce"],
                 "sp0": p["sqrt_p0"], "L0": p["liq_launch"], "tick0": p["tick0"], "fee": p["fee"], "token": p["token"],
                 "n_adds": len(e["adds"]), "buy_in_launch": p["buy_in_launch_tx"],
                 "bot_off": fb["off"] if fb else None, "bot_eth": fb["eth"] if fb else None, "bot_from": fb["from"] if fb else None, "bot_rank": fb["rank"] if fb else None,
                 "bot_minout": mo, "bot_q0": q0, "bot_n_in8": len(bot),
                 "pull_off": (pl["bn"] - b0) if pl else None, "pull_from": ptx["from"] if ptx else None, "pull_to": ptx["to"] if ptx else None, "pull_sel": ptx["selector"] if ptx else None,
                 "pull_dl": pl["dl"] if pl else None, "pull_full": (sum(a["dl"] for a in e["adds"]) + sum(x["dl"] for x in pulls) == 0) if pl else None,
                 "n_swaps": len(sw), "complete": e["complete"],
                 "pre_bot": [{k: x[k] for k in ("off", "eth", "buy", "from", "to", "sel", "rank", "tx")} for x in seq if fb is None or (x["bn"], x["li"]) < (fb["bn"], fb["li"])][:12],
                 "seq8": [{k: x[k] for k in ("off", "eth", "buy", "from", "to", "sel", "rank")} for x in seq[:12]]})
json.dump(rows, open(HERE + "/rows.json", "w"))
out = {}
for sub in ("v3.0", "v5.0", "v-other"):
    R = [r for r in rows if r["sub"] == sub]
    o = {"n": len(R), "sp0": collections.Counter(r["sp0"] for r in R).most_common(3), "L0": collections.Counter(r["L0"] for r in R).most_common(3),
         "values": collections.Counter(r["value"] for r in R).most_common(4), "n_from": len(set(r["from"] for r in R)),
         "nonce": q([r["nonce"] for r in R]), "nonce_eq3": sum(1 for r in R if r["nonce"] == 3), "buy_in_launch": sum(1 for r in R if r["buy_in_launch"]),
         "with_bot": sum(1 for r in R if r["bot_off"] is not None), "bot_off": q([r["bot_off"] for r in R if r["bot_off"] is not None], (0, .05, .1, .5, .9, .95, 1)),
         "bot_off_hist": sorted(collections.Counter(r["bot_off"] for r in R if r["bot_off"] is not None).items()),
         "bot_eth": q([r["bot_eth"] for r in R if r["bot_eth"]]), "bot_rank": collections.Counter(r["bot_rank"] for r in R if r["bot_rank"] is not None).most_common(8),
         "minout_ratio": q([r["bot_minout"] / r["bot_q0"] for r in R if r["bot_minout"]], (0, .01, .5, .99, 1)),
         "pulled3000": sum(1 for r in R if r["pull_off"] is not None), "pull_off": q([r["pull_off"] for r in R if r["pull_off"] is not None]),
         "pull_after_bot": q([r["pull_off"] - r["bot_off"] for r in R if r["pull_off"] is not None and r["bot_off"] is not None]),
         "pull_before_bot": sum(1 for r in R if r["pull_off"] is not None and (r["bot_off"] is None or r["pull_off"] < r["bot_off"])),
         "pull_eq_bot_blk": sum(1 for r in R if r["pull_off"] is not None and r["bot_off"] is not None and r["pull_off"] == r["bot_off"]),
         "pull_by_launch_wallet": sum(1 for r in R if r["pull_off"] is not None and r["pull_from"] == r["from"]),
         "pull_to_sel": collections.Counter(f'{r["pull_to"]}:{r["pull_sel"]}' for r in R if r["pull_off"] is not None).most_common(4),
         "pull_full": sum(1 for r in R if r["pull_full"]), "n_adds": collections.Counter(r["n_adds"] for r in R).most_common(4),
         "incomplete": sum(1 for r in R if not r["complete"])}
    out[sub] = o
for k, v in out.items(): print(k, json.dumps(v, default=str))
json.dump(out, open(HERE + "/s1_basics.json", "w"), indent=1, default=str)
