"""skeptic replay: sequential integer simulation of each family pool with our 0.0012 ETH buy inserted (own code)."""
import sys, os, pickle, json, statistics as st
SCR = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"; sys.path.insert(0, SCR); sys.path.insert(0, "/home/user/v2pons/src")
from chain import T_SWAP, T_ML, W, sgn
import v4math
Q96 = 1 << 96
HERE = os.path.dirname(os.path.abspath(__file__))
D = pickle.load(open(os.path.join(HERE, "data_s.pkl"), "rb"))
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
X = int(0.0012e18); FEE = 2500; TP = 0.01; HOLD = 12; GAS_B, GAS_S = 104_000, 104_000

def s128(v):
    v = sgn(v); return v - (1 << 128) if v >= (1 << 127) else v
def net(x, fee=FEE): return x - (x * fee + 999_999) // 1_000_000
def buy_new_sqrt(s, L, eth_in, fee=FEE):
    x = net(eth_in, fee); num = L * s; den = L + (x * s) // Q96; return (num + den - 1) // den
def sell_new_sqrt(s, L, tok_in, fee=FEE):
    return s + (net(tok_in, fee) * Q96) // L
def wd(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)

txs = D["txs"]; blocks = D["blocks"]
bf = lambda n: int(blocks[n]["baseFeePerGas"], 16) if n in blocks else None
bylog = {}
for l in D["logs"]: bylog.setdefault(l["topics"][1], []).append(l)

def pool(x):
    pid = x["pid"]; b0 = x["bn"]; rec = D["recs"][x["tx"]]
    adds = [(sgn(W(l["data"], 0)), sgn(W(l["data"], 1)), sgn(W(l["data"], 2))) for l in rec["logs"] if l["topics"] and l["topics"][0] == T_ML and l["topics"][1] == pid]
    L0 = v4math.active_liquidity(x["tick0"], adds)
    token = x["c1"][-40:]
    ev = []
    for l in sorted(bylog.get(pid, []), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
        bn = int(l["blockNumber"], 16); t = txs[l["transactionHash"]]; d = l["data"]
        base = {"bn": bn, "li": int(l["logIndex"], 16), "ti": int(l["transactionIndex"], 16), "tx": l["transactionHash"], "to": (t["to"] or "").lower(), "from": t["from"].lower(),
                "input": t["input"], "value": int(t["value"], 16)}
        if l["topics"][0] == T_SWAP:
            base.update(kind="swap", a0=s128(W(d, 0)), a1=s128(W(d, 1)), sp=W(d, 2), L=W(d, 3), fee=W(d, 5))
            base["bot"] = base["to"] == ROUTER and t["input"][:10] == "0xc1120e3d"
        else:
            base.update(kind="ml", lo=sgn(W(d, 0)), hi=sgn(W(d, 1)), dl=sgn(W(d, 2)))
        ev.append(base)
    return {"pid": pid, "b0": b0, "L0": L0, "sp0": x["sp0"], "token": token, "ev": ev, "launcher": x["from"].lower(), "launch_tx": x["tx"], "launch_ti": x["txi"]}

def validate(p):
    """recompute every swap from its input amount; compare to the logged sqrtP"""
    s = p["sp0"]; L = p["L0"]; worst = 0.0; n = 0
    for e in p["ev"]:
        if e["kind"] == "ml":
            if e["bn"] == p["b0"]: continue
            break
        if e["fee"] != FEE: return ("fee", e["fee"])
        if e["L"] != L: return ("L changed", e["bn"] - p["b0"])
        s2 = buy_new_sqrt(s, L, -e["a0"]) if e["a0"] < 0 else sell_new_sqrt(s, L, -e["a1"])
        worst = max(worst, abs(s2 - e["sp"]) / e["sp"]); n += 1; s = e["sp"]
    return ("ok", n, worst)

def feed_buys(p, lo, hi):
    """engine feed: txs with value>0, >=20 bytes, carrying the token, to != token (from the full blocks b0..b0+16)"""
    tb = p["token"]; out = []
    for k in range(lo, hi + 1):
        b = blocks.get(k)
        if b is None: continue
        for t in b["transactions"]:
            inp = t["input"][2:].lower(); v = int(t["value"], 16); to = (t["to"] or "").lower()
            if to == "0x58daec3116aae6d93017baaea7749052e8a04fa7" and v == 2433328500000000000 and len(inp) // 2 == 1444: continue
            if v == 0 or len(inp) // 2 < 20: continue
            if tb in inp and to[2:] != tb:
                out.append({"bn": k, "ti": int(t["transactionIndex"], 16), "value": v, "to": to, "from": t["from"].lower(), "hash": t["hash"], "input": t["input"]})
    return out

def engine_dry(p, fb):
    """dry run: fire at end of b0 (skip if eth ahead + stake > 0.008 or a >=0.04 buy at/before b0), virtual buy at the head of b0+2, TP on later feed buys"""
    b0 = p["b0"]; L = p["L0"]; sp = float(p["sp0"]); ahead = 0
    for f in fb:
        if f["bn"] > b0: break
        if f["value"] >= int(0.04e18): return {"skip": "bot first"}
        sp = v4math.sqrt_after_buy(sp, L, net(f["value"])); ahead += f["value"]
    if ahead + X > int(0.008e18): return {"skip": "ahead"}
    B = b0 + 2
    for f in fb:
        if b0 < f["bn"] < B: sp = v4math.sqrt_after_buy(sp, L, net(f["value"]))
    feed_tokens = v4math.buy_out_int(int(sp), L, X, FEE)
    bot_seen = False
    for f in fb:
        if f["bn"] < B: continue
        if f["bn"] > B + HOLD: break
        if f["value"] >= int(0.04e18) and not bot_seen:
            bot_seen = True
            q0 = v4math.buy_out_int(p["sp0"], L, f["value"], FEE); spu = v4math.sqrt_after_buy(sp, L, net(X)); q1 = v4math.buy_out_int(int(spu), L, f["value"], FEE)
            if q1 < q0 * 0.99: return {"send": f["bn"], "why": "bot reverts", "B": B}
        sp = v4math.sqrt_after_buy(sp, L, net(f["value"]))
        spu = v4math.sqrt_after_buy(sp, L, net(X))
        eth = v4math.sell_out_int(int(spu), L, feed_tokens, FEE)
        r = (eth - X - bf(f["bn"]) * 250_000) / X
        if r >= TP: return {"send": f["bn"], "why": "tp", "tp_ret": r, "B": B, "trig_value": f["value"], "trig_to": f["to"]}
    return {"send": B + HOLD, "why": "deadline", "B": B}

def chain_trade(p, B, pos, send, lag, at):
    """our buy in block B at `pos` ('head' or 'tail'); every later swap re-run from its input; bot buys under their minOut drop; sell at the head/tail of send+lag"""
    L = p["L0"]; s = p["sp0"]; S = send + lag; dropped = []; pull = None
    evs = [e for e in p["ev"] if not (e["kind"] == "ml" and e["bn"] == p["b0"] and e["dl"] > 0)]
    inserted = False; tokens = None
    def ins():
        nonlocal s, tokens
        tokens = v4math.buy_out_int(s, L, X, FEE); s = buy_new_sqrt(s, L, X)
    for e in evs:
        key_before_us = e["bn"] < B or (e["bn"] == B and pos == "tail")
        if not inserted and not key_before_us: ins(); inserted = True
        in_window = e["bn"] < S or (e["bn"] == S and at == "tail")
        if inserted and not in_window: break
        if e["kind"] == "ml":
            if e["dl"] < 0: return {"pulled": e["bn"] - p["b0"], "ret": -1.0}
            raise RuntimeError("liquidity add mid-trade")
        if not inserted:
            s = e["sp"]; continue
        if e["a0"] < 0:
            if e["bot"]:
                mo = wd(e["input"], 4); o = v4math.buy_out_int(s, L, -e["a0"], FEE)
                if o < mo: dropped.append(e["bn"] - p["b0"]); continue
            s = buy_new_sqrt(s, L, -e["a0"])
        else:
            s = sell_new_sqrt(s, L, -e["a1"])
    if not inserted: ins()
    eth = v4math.sell_out_int(s, L, tokens, FEE)
    gas = GAS_B * bf(B) + GAS_S * (bf(S) or bf(B))
    return {"tokens": tokens, "eth_out": eth, "gross": (eth - X) / X, "ret": (eth - X - gas) / X, "dropped": dropped, "S": S - p["b0"]}

rows = []
for x in D["fam"]:
    p = pool(x); b0 = p["b0"]
    val = validate(p)
    swaps = [e for e in p["ev"] if e["kind"] == "swap"]
    mls = [e for e in p["ev"] if e["kind"] == "ml"]
    pulls = [e for e in mls if e["dl"] < 0]
    pull = pulls[0] if pulls else None
    bots = [e for e in swaps if e["bot"] and e["a0"] < 0]
    fbot = bots[0] if bots else None
    # bot first buy: calldata minOut vs launch quote and vs actual
    bi = None
    if fbot:
        mo = wd(fbot["input"], 4); q0 = v4math.buy_out_int(p["sp0"], p["L0"], -fbot["a0"], FEE)
        pre = [e for e in swaps if (e["bn"], e["li"]) < (fbot["bn"], fbot["li"])]
        s_pre = pre[-1]["sp"] if pre else p["sp0"]
        s_pre_us = buy_new_sqrt(s_pre, p["L0"], X)
        bi = {"blk": fbot["bn"] - b0, "eth": -fbot["a0"] / 1e18, "minout_over_q0": mo / q0, "actual_over_minout": fbot["a1"] / mo,
              "with_us_over_minout": v4math.buy_out_int(s_pre_us, p["L0"], -fbot["a0"], FEE) / mo, "value": fbot["value"] / 1e18}
    # non-bot buys/sells (outsiders) before pull
    lim = pull["bn"] if pull else 10**12
    outs = [(e["bn"] - b0, round(-e["a0"] / 1e18, 7), e["from"][2:10], e["to"][2:10]) for e in swaps if e["a0"] < 0 and not e["bot"] and e["bn"] <= lim]
    sells = [(e["bn"] - b0, round(e["a0"] / 1e18, 7), e["from"][2:10], e["to"][2:10], e["bot"]) for e in swaps if e["a0"] > 0 and e["bn"] <= lim]
    prebot = [o for o in outs if fbot is None or o[0] < fbot["bn"] - b0 or (o[0] == fbot["bn"] - b0)]
    fb = feed_buys(p, b0, b0 + 16)
    eng = engine_dry(p, fb)
    r = {"pid": p["pid"], "b0": b0, "launcher": p["launcher"][:10], "valid": val, "L0": p["L0"], "bot": bi, "n_bot_buys_before_pull": sum(1 for e in bots if e["bn"] <= lim),
         "pull": (pull["bn"] - b0) if pull else None, "pull_from_launcher": (pull["from"] == p["launcher"]) if pull else None, "pull_to": pull["to"][:10] if pull else None,
         "pull_minus_bot": (pull["bn"] - fbot["bn"]) if (pull and fbot) else None,
         "other_ml": [(e["bn"] - b0, e["dl"]) for e in mls if e["bn"] != b0 and e["dl"] > 0],
         "outsider_buys": outs, "sells": sells[:8], "n_sells": len(sells), "prebot_outsiders": prebot,
         "feed_b0_to_16": [(f["bn"] - b0, round(f["value"] / 1e18, 7), f["to"][2:10], f["from"][2:10]) for f in fb], "engine": eng}
    if "send" in eng:
        res = {}
        for B in (b0 + 1, b0 + 2):
            for pos in ("head", "tail"):
                for lag in (1, 2):
                    for at in ("head", "tail"):
                        res[f"B+{B-b0}{pos[0]}|S+{lag}{at[0]}"] = chain_trade(p, B, pos, eng["send"], lag, at)
        r["chain"] = res
        # engine minOut on our buy at fire (feed through b0)
        sp = float(p["sp0"])
        for f in fb:
            if f["bn"] <= b0: sp = v4math.sqrt_after_buy(sp, p["L0"], net(f["value"]))
        minout = int(v4math.buy_out_int(int(sp), p["L0"], X, FEE) * 0.97)
        r["our_tokens_over_minout_min"] = min(v["tokens"] / minout for v in res.values() if "tokens" in v)
    rows.append(r)
json.dump(rows, open(os.path.join(HERE, "ana_s.json"), "w"), indent=1, default=str)
for r in rows:
    e = r["engine"]; c = r.get("chain", {})
    k1 = c.get("B+2h|S+1h", {}); k2 = c.get("B+2t|S+2t", {}); k3 = c.get("B+1t|S+1h", {})
    rets = [v["ret"] for v in c.values()]
    print(f"{r['pid'][:10]} b0 {r['b0']} valid {r['valid']} bot {r['bot'] and (r['bot']['blk'], round(r['bot']['eth'],6), round(r['bot']['minout_over_q0'],6), round(r['bot']['actual_over_minout'],5), round(r['bot']['with_us_over_minout'],5))} "
          f"pull +{r['pull']} (launcher {r['pull_from_launcher']}) pull-bot {r['pull_minus_bot']} | eng {e.get('why')} send +{e.get('send', 0) - r['b0']} tp {round(e.get('tp_ret', 0), 4)} | "
          f"B2h/S1h {k1.get('ret', 0):+.4f} B2t/S2t {k2.get('ret', 0):+.4f} B1t/S1h {k3.get('ret', 0):+.4f} range [{min(rets):+.4f},{max(rets):+.4f}] drop {set(tuple(v.get('dropped', [])) for v in c.values())} tok/minout {r.get('our_tokens_over_minout_min', 0):.4f}")
