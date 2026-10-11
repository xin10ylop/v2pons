"""Copy of skeptic s8_fresh_analyse.py on report/work/fresh2 (census end to head), also split before/after v2.433 last launch (block 85,243,576, 19:28 UTC). Skeptic step 8: the fresh launches (after the census, to head): per sub-family the bot's first buy (offset, size, minOut / launch quote), who buys
ahead of it (decoys?), the pull, and the front replay (our 0.0058 at +1, sell at the head of bot+1)."""
import sys, json, collections, statistics as st
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10"); sys.path.insert(0, "/home/user/v2pons/src")
from chain import T_SWAP, T_ML, W, sgn
import v4math
HERE = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/report/work"
D = HERE + "/fresh2"
pools = json.load(open(D + "/pools.json")); ev = json.load(open(D + "/events.json")); txs = json.load(open(D + "/txs.json"))
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"; Q96 = 1 << 96
L0 = {"v3.0": 25725498245903809899643, "v5.0": 33218249502344340119344, "v2.433": 49279426163460954002188}
def s128(x): x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
def net(x, fee): return x - (x * fee + 999_999) // 1_000_000
def wd(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)
H = json.load(open(D + "/inits.json"))["head"]
res = collections.defaultdict(list)
for p in pools:
    b0 = p["b0"]; fee = p["fee"]; Lz = L0[p["sub"]]
    lg = sorted(ev[p["pid"]]["logs"], key=lambda x: (x["bn"], x["li"]))
    sw = []
    for x in lg:
        if x["t"] != T_SWAP: continue
        d = x["data"]; t = txs.get(x["tx"])
        sw.append({"bn": x["bn"], "off": x["bn"] - b0, "a0": s128(W(d, 0)), "sp": W(d, 2), "L": W(d, 3), "tx": x["tx"], "from": t["from"] if t else None, "to": t["to"] if t else None,
                   "sel": t["input"][2:10] if t else None, "input": t["input"] if t else None})
    pulls = [x for x in lg if x["t"] == T_ML and sgn(W(x["data"], 2)) < 0]
    pull = pulls[0]["bn"] if pulls else None
    ptx = txs.get(pulls[0]["tx"]) if pulls else None
    fb = next((s for s in sw if s["a0"] < 0 and s["to"] == ROUTER and s["sel"] == "c1120e3d"), None)
    pre = [s for s in sw if fb is None or s["bn"] < fb["bn"] or (s["bn"] == fb["bn"] and s is not fb and sw.index(s) < sw.index(fb))]
    row = {"pid": p["pid"], "b0": b0, "window": min(H, b0 + 3000) - b0, "bot_off": fb["off"] if fb else None, "bot_eth": -fb["a0"] / 1e18 if fb else None,
           "minout_ratio": wd(fb["input"], 4) / v4math.buy_out_int(p["sp0"], Lz, -fb["a0"], fee) if fb else None,
           "pull_off": (pull - b0) if pull else None, "pull_by": (ptx["to"], ptx["input"][2:10]) if ptx else None,
           "pre": [(s["off"], round(-s["a0"] / 1e18 if s["a0"] < 0 else s["a0"] / 1e18, 7), "B" if s["a0"] < 0 else "S", (s["from"] or "?")[:10], (s["to"] or "?")[:10]) for s in pre][:6]}
    # replay
    if fb and pull is None or (fb and pull and pull > fb["bn"] + 1):
        X = int(0.0058e18); B = b0 + 1
        preB = [s for s in sw if s["bn"] <= B]
        spB, LB = (preB[-1]["sp"], preB[-1]["L"]) if preB else (p["sp0"], Lz)
        tokens = v4math.buy_out_int(spB, LB, X, fee)
        S = fb["bn"] + 1 if fb["off"] <= 20 else b0 + 20
        s = Q96 / (Q96 / spB + net(X, fee) / LB); prev = spB; L = LB; drop = 0
        for x in sw:
            if x["bn"] <= B: continue
            if x["bn"] >= S: break
            L = x["L"]
            if x["a0"] < 0:
                d_inv = Q96 / x["sp"] - Q96 / prev
                if x["to"] == ROUTER and x["sel"] == "c1120e3d" and v4math.buy_out_int(int(s), L, -x["a0"], fee) < wd(x["input"], 4): drop += 1; prev = x["sp"]; continue
                s = Q96 / (Q96 / s + d_inv)
            else: s = s + (x["sp"] - prev)
            prev = x["sp"]
        if pull and pull <= S: row["ret"] = -1.0
        else: row["ret"] = (v4math.sell_out_int(int(s), L, tokens, fee) - X - 4_200_000_000_000) / X
        row["drop"] = drop
    res[p["sub"]].append(row)
    res[p["sub"] + (" before 19:28" if b0 <= 85243576 else " after 19:28")].append(row)
out = {}
for sub, R in res.items():
    pre_c = collections.Counter((x[3], x[4], x[2]) for r in R for x in r["pre"])
    pre_eth = collections.defaultdict(list)
    for r in R:
        for x in r["pre"]: pre_eth[(x[3], x[4], x[2])].append(x[1])
    v = [r["ret"] for r in R if r.get("ret") is not None]
    out[sub] = {"n": len(R), "with_bot": sum(1 for r in R if r["bot_off"] is not None), "bot_off": sorted(collections.Counter(r["bot_off"] for r in R).items(), key=lambda x: (x[0] is None, x[0] or 0)),
                "bot_eth_med": st.median([r["bot_eth"] for r in R if r["bot_eth"]]) if any(r["bot_eth"] for r in R) else None,
                "minout_ratio_minmax": [min(r["minout_ratio"] for r in R if r["minout_ratio"]), max(r["minout_ratio"] for r in R if r["minout_ratio"])] if any(r["minout_ratio"] for r in R) else None,
                "pulled": sum(1 for r in R if r["pull_off"] is not None), "pull_after_bot": sorted(r["pull_off"] - r["bot_off"] for r in R if r["pull_off"] is not None and r["bot_off"] is not None)[:15],
                "pull_by": collections.Counter(str(r["pull_by"]) for r in R if r["pull_by"]).most_common(3),
                "pre_bot_traders": [(k, n, min(pre_eth[k]), max(pre_eth[k])) for k, n in pre_c.most_common(12)],
                "front_n": len(v), "front_mean%": round(100 * st.mean(v), 2) if v else None, "front_median%": round(100 * st.median(v), 2) if v else None,
                "front_win": round(sum(1 for a in v if a > 0) / len(v), 3) if v else None, "dropped": sum(1 for r in R if r.get("drop")),
                "first_b0": min(r["b0"] for r in R), "last_b0": max(r["b0"] for r in R)}
print(json.dumps(out, indent=1, default=str))
json.dump({"summary": out, "rows": res}, open(HERE + "/f8_fresh.json", "w"), indent=1, default=str)
