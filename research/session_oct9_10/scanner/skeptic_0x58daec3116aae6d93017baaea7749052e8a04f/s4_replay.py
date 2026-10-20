"""Skeptic step 4: my own exact replay of the front rule on this family (independent of analyse_0's code).
Our buy of X wei lands at launch+LAND after every swap of that block; every later swap is replayed by its own shift (exact-in: a buy moves
1/sqrtP by x_net/L, a sell moves sqrtP by y_net/L, independent of the starting price); the bot's buys (to 0x1cbaf24d, c1120e3d) whose output with
our buy ahead falls under their calldata minOut (word 4) are dropped (revert). Our sell is priced at the head of block bot_first+1+EXTRA
(or launch+20 if the bot has not bought by then); a pull at or before the sell block = the stake lost. Gas: (103,861 + 103,894) x the launch block's base fee."""
import sys, json, random, collections, statistics as st
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/src")
from load import *
import v4math
HERE = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/skeptic_0x58daec3116aae6d93017baaea7749052e8a04f"
Q96 = 1 << 96; ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"; ETH_USD = 15 / 0.0058
rows = {r["pid"]: r for r in json.load(open(HERE + "/rows.json"))}
pids = [p for p, r in rows.items() if r["sub"] in ("v3.0", "v5.0")]
E = load_events(set(pids)); T = load_txs(); M = load_blocks_meta()
def net(x, fee): return x - (x * fee + 999_999) // 1_000_000
def wd(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)

def trade(pid, X, land=1, extra=0, deadline=20, pull_shift=None):
    r = rows[pid]; e = E[pid]; b0 = r["b0"]; fee = r["fee"]; sw = e["swaps"]
    B = b0 + land
    pull = e["pulls"][0]["bn"] if e["pulls"] else None
    if pull is not None and pull <= B: return {"exit": "pulled_before_buy", "ret": None}
    pre = [s for s in sw if s["bn"] <= B]
    spB, LB = (pre[-1]["sqrt_p"], pre[-1]["liq"]) if pre else (r["sp0"], r["L0"])
    tokens = v4math.buy_out_int(spB, LB, X, fee)
    # the bot's first buy behind ours
    bots = [s for s in sw if s["bn"] > B and s["a0"] < 0 and T.get(s["tx"]) and T[s["tx"]]["to"] == ROUTER and T[s["tx"]]["selector"] == "c1120e3d"]
    fb = bots[0] if bots else None
    S = (fb["bn"] + 1 + extra) if fb and fb["bn"] - b0 <= deadline else b0 + deadline
    S = max(S, B + 1)
    if pull_shift is not None and fb: pull = min(pull or 10**12, fb["bn"] + pull_shift)
    if pull is not None and pull <= S:
        gas = (103861 + 135200) * M[b0][1]
        return {"exit": "pull_first", "ret": (-X - gas) / X, "S": S - b0, "pull": pull - b0}
    s = Q96 / (Q96 / spB + net(X, fee) / LB); prev = spB; L = LB; dropped = 0; fill = None
    for x in sw:
        if x["bn"] <= B: continue
        if x["bn"] >= S: break
        L = x["liq"]
        if x["a0"] < 0:
            d_inv = Q96 / x["sp"] - Q96 / prev if False else Q96 / x["sqrt_p"] - Q96 / prev
            t = T.get(x["tx"])
            if t and t["to"] == ROUTER and t["selector"] == "c1120e3d":
                mo = wd(t["input"], 4)
                out_us = v4math.buy_out_int(int(s), L, -x["a0"], fee)
                if x is fb: fill = out_us / mo
                if out_us < mo: dropped += 1; prev = x["sqrt_p"]; continue
            s = Q96 / (Q96 / s + d_inv)
        else:
            s = s + (x["sqrt_p"] - prev)
        prev = x["sqrt_p"]
    eth_out = v4math.sell_out_int(int(s), L, tokens, fee)
    gas = (103861 + 103894) * M[b0][1]
    return {"exit": "bot" if fb and fb["bn"] - b0 <= deadline else "deadline", "ret": (eth_out - X - gas) / X, "gross": (eth_out - X) / X,
            "S": S - b0, "dropped": dropped, "fill": fill, "gas_eth": gas / 1e18}

def summ(rs, X):
    v = [x["ret"] for x in rs if x["ret"] is not None]
    if not v: return None
    m = st.mean(v)
    return {"n": len(v), "mean%": round(100 * m, 3), "median%": round(100 * st.median(v), 3), "min%": round(100 * min(v), 2), "win": round(sum(1 for a in v if a > 0) / len(v), 4),
            "pull_first": sum(1 for x in rs if x["exit"] == "pull_first"), "deadline": sum(1 for x in rs if x["exit"] == "deadline"),
            "bot_dropped": sum(1 for x in rs if x.get("dropped")), "usd_trade": round(m * X / 1e18 * ETH_USD, 3), "usd_day": round(m * X / 1e18 * ETH_USD * len(v) / 2.0, 1)}

random.seed(20261010)
out = {}
for sub in ("v3.0", "v5.0"):
    allp = [p for p in pids if rows[p]["sub"] == sub]
    samp = random.sample(allp, min(300, len(allp)))
    X = int(0.0058e18)
    out[sub] = {"all": summ([trade(p, X) for p in allp], X), "sample300": summ([trade(p, X) for p in samp], X),
                "land+2": summ([trade(p, X, land=2) for p in allp], X),
                "sell_bot+2": summ([trade(p, X, extra=1) for p in allp], X),
                "sell_bot+3": summ([trade(p, X, extra=2) for p in allp], X),
                "if_pull_at_bot+3_always_sell+1": summ([trade(p, X, pull_shift=3) for p in allp], X),
                "if_pull_at_bot+3_always_sell+3": summ([trade(p, X, extra=2, pull_shift=3) for p in allp], X),
                "if_pull_at_bot+2_always_sell+1": summ([trade(p, X, pull_shift=2) for p in allp], X)}
    out[sub]["stake"] = {}
    for st_eth in (0.0029, 0.0058, 0.012, 0.025, 0.05, 0.07, 0.075, 0.08, 0.1):
        Xs = int(st_eth * 1e18); rs = [trade(p, Xs) for p in allp]
        out[sub]["stake"][st_eth] = summ(rs, Xs)
    # fill ratio of the bot's first buy with our 0.0058 ahead, and the room: largest X ahead with fill >= 1
    fills = sorted(x["fill"] for x in (trade(p, X) for p in allp) if x.get("fill"))
    out[sub]["bot_fill_with_0.0058"] = [round(fills[0], 5), round(fills[len(fills)//2], 5), round(fills[-1], 5)]
    # by 6-h slice
    by = collections.defaultdict(list)
    for p in allp: by[(rows[p]["ts"] - 1759947648) // 21600].append(trade(p, X))
    out[sub]["slices"] = {int(k): summ(v, X) for k, v in sorted(by.items())}
for k, v in out.items(): print(k, json.dumps(v, indent=0)[:6000])
json.dump(out, open(HERE + "/s4_replay.json", "w"), indent=1)
