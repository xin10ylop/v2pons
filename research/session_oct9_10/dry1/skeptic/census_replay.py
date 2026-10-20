"""no-reaction replay of the 0.9 front rules on every v2.433 family pool of the 24 h before the window + the window (own code)"""
import sys, os, pickle, json, collections, statistics as st, datetime
SCR = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"; sys.path.insert(0, SCR); sys.path.insert(0, "/home/user/v2pons/src")
from chain import T_SWAP, T_ML, W, sgn, batch
import v4math
HERE = os.path.dirname(os.path.abspath(__file__))
C = pickle.load(open(os.path.join(HERE, "census_s.pkl"), "rb")); D = pickle.load(open(os.path.join(HERE, "data_s.pkl"), "rb"))
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"; Q96 = 1 << 96
SP0 = 1604517591721945638372359205383840; L0 = 49279426163460954002188; FEE = 2500; X = int(0.0012e18); BF = 20_000_000
txs = dict(C["txs"]); txs.update(D["txs"])
fam = C["fam"] + [{"pid": x["pid"], "bn": x["bn"], "sp0": x["sp0"]} for x in D["fam"]]
assert all(x["sp0"] == SP0 for x in fam)
by = collections.defaultdict(list)
for l in C["plogs"] + D["logs"]: by[l["topics"][1]].append(l)
def s128(v):
    v = sgn(v); return v - (1 << 128) if v >= (1 << 127) else v
def net(x): return x - (x * FEE + 999_999) // 1_000_000
def bns(s, eth): x = net(eth); num = L0 * s; den = L0 + (x * s) // Q96; return (num + den - 1) // den
def sns(s, tok): return s + (net(tok) * Q96) // L0
def wd(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)
pools = []
for x in fam:
    seen = set(); ev = []
    for l in sorted(by[x["pid"]], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
        k = (l["transactionHash"], l["logIndex"])
        if k in seen: continue
        seen.add(k); bn = int(l["blockNumber"], 16)
        if l["topics"][0] == T_ML:
            if bn == x["bn"]: continue
            ev.append({"bn": bn, "kind": "ml", "dl": sgn(W(l["data"], 2)), "tx": l["transactionHash"]})
        else:
            ev.append({"bn": bn, "kind": "swap", "a0": s128(W(l["data"], 0)), "a1": s128(W(l["data"], 1)), "sp": W(l["data"], 2), "L": W(l["data"], 3), "tx": l["transactionHash"]})
        if bn > x["bn"] + 40: break
    pools.append({"pid": x["pid"], "b0": x["bn"], "ev": ev})
# fetch txs of buys >= 0.04 ETH within +40 (bot identification + minOut)
miss = sorted({e["tx"] for p in pools for e in p["ev"] if e["kind"] == "swap" and -e["a0"] >= int(0.04e18) and e["tx"] not in txs})
print("fetch", len(miss))
for i in range(0, len(miss), 500):
    for h, t in zip(miss[i:i+500], batch([("eth_getTransactionByHash", [h]) for h in miss[i:i+500]])): txs[h] = t
def isbot(e):
    t = txs.get(e["tx"]); return t is not None and (t["to"] or "").lower() == ROUTER and t["input"][:10] == "0xc1120e3d"
def run(p, Boff, lag):
    b0 = p["b0"]; ev = p["ev"]; B = b0 + Boff
    # engine skip rules at the fire (end of b0)
    pre = [e for e in ev if e["bn"] <= b0]
    if any(e["kind"] == "ml" and e["dl"] < 0 for e in pre): return {"exit": "pulled_before_fire"}
    ahead = sum(-e["a0"] for e in pre if e["kind"] == "swap" and e["a0"] < 0)
    if any(e["kind"] == "swap" and -e["a0"] >= int(0.04e18) for e in pre): return {"exit": "skip_bot_first"}
    if ahead + X > int(0.008e18): return {"exit": "skip_ahead"}
    # chain up to and including block B (our buy at its tail)
    s = SP0
    for e in ev:
        if e["bn"] > B: break
        if e["kind"] == "ml":
            if e["dl"] < 0: return {"exit": "pull_before_buy", "ret": -(104000 * 2 * BF) / X}
            continue
        s = e["sp"]
    tokens = v4math.buy_out_int(s, L0, X, FEE); s = bns(s, X)
    # engine copy (buys only, by amount) for TP; dry-run style our tokens from the feed copy at B
    sp_e = float(SP0)
    for e in ev:
        if e["bn"] > B: break
        if e["kind"] == "swap" and e["a0"] < 0: sp_e = v4math.sqrt_after_buy(sp_e, L0, net(-e["a0"]))
    ftok = v4math.buy_out_int(int(sp_e), L0, X, FEE); sp_e = v4math.sqrt_after_buy(sp_e, L0, net(X))
    send = None; why = "deadline"; botseen = False
    for e in ev:
        if e["bn"] <= B or e["kind"] != "swap" or e["a0"] >= 0: continue
        if e["bn"] > B + 12: break
        if -e["a0"] >= int(0.04e18) and not botseen:
            botseen = True
            q0 = v4math.buy_out_int(SP0, L0, -e["a0"], FEE); q1 = v4math.buy_out_int(int(sp_e), L0, -e["a0"], FEE)
            if q1 < q0 * 0.99: send = e["bn"]; why = "bot_reverts"; break
        sp_e = v4math.sqrt_after_buy(sp_e, L0, net(-e["a0"]))
        r = (v4math.sell_out_int(int(sp_e), L0, ftok, FEE) - X - BF * 250000) / X
        if r >= 0.01: send = e["bn"]; why = "tp"; break
    if send is None: send = B + 12
    S = send + lag
    # chain from after B to the head of S
    for e in ev:
        if e["bn"] <= B: continue
        if e["bn"] > S: break
        if e["kind"] == "ml":
            if e["dl"] < 0: return {"exit": "PULL_FIRST", "ret": (-X - 104000 * 2 * BF) / X, "send": send - b0, "S": S - b0, "pull": e["bn"] - b0, "same_block": e["bn"] == S}
            continue
        if e["bn"] == S: continue   # sell at the head of S
        if e["a0"] < 0:
            if isbot(e) and v4math.buy_out_int(s, L0, -e["a0"], FEE) < wd(txs[e["tx"]]["input"], 4): continue
            s = bns(s, -e["a0"])
        else: s = sns(s, -e["a1"])
    eth = v4math.sell_out_int(s, L0, tokens, FEE)
    return {"exit": why, "ret": (eth - X - 104000 * 2 * BF) / X, "send": send - b0, "S": S - b0}
res = {}
for Boff in (1, 2):
    for lag in (1, 2):
        out = [run(p, Boff, lag) for p in pools]
        ex = collections.Counter(o["exit"] for o in out); v = [o["ret"] for o in out if "ret" in o]
        print(f"buy +{Boff} sell lag {lag}: n {len(v)} exits {dict(ex)} mean {st.mean(v):+.4f} median {st.median(v):+.4f} min {min(v):+.4f}")
        pf = [(p["pid"][:10], p["b0"], o) for p, o in zip(pools, out) if o["exit"] in ("PULL_FIRST", "pull_before_buy")]
        for z in pf: print("     ", z)
        res[f"{Boff}|{lag}"] = out
# the window-only subset
win = [i for i, p in enumerate(pools) if p["b0"] >= D["start"]]
for k, out in res.items():
    v = [out[i]["ret"] for i in win if "ret" in out[i]]; print("window", k, len(v), f"{st.mean(v):+.4f}")
json.dump({"pools": [p["pid"] for p in pools], "res": res}, open(os.path.join(HERE, "census_replay.json"), "w"), default=str)
