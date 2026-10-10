"""Skeptic f2276/100 shared pieces: the sample (60 seeded census pools + every fresh post-census launch) with EVERY swap's transaction,
and an exact single-range replay of a ride (our buy at the end of block B, our sell at the head of block S)."""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "census"))
sys.path.insert(0, "/home/user/v2pons/src")
from load import *
import v4math
Q96 = 1 << 96
K = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2276|100|1|true"
CROWD = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"
DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
STAKE = int(0.0058e18); GAS_ETH = 0.012 / 15 * 0.0058   # $0.012 of gas a round trip, in ETH
T_SWAP = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"
def sgn(x, bits=256): return x - (1 << bits) if x >= (1 << (bits - 1)) else x
def W(d, i): return int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def q(v, ps=(0, .1, .5, .9, 1)):
    v = sorted(x for x in v if x is not None); return [v[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))] for p in ps] if v else None

def load_sample():
    TX = {}
    for line in open(os.path.join(D, "txs.jsonl")):
        t = json.loads(line); TX[t["hash"]] = t
    P = load_pools(); samp = json.load(open(os.path.join(D, "census_sample.json"))); E = load_events(set(samp))
    pools = []
    for pid in samp:
        p = P[pid]; e = E[pid]
        pools.append({"pid": pid, "src": "census", "b0": p["launch_block"], "ts0": p["launch_ts"], "launcher": p["launch_from"], "nonce": p["launch_nonce"],
                      "sp0": p["sqrt_p0"], "L0": p["liq_launch"], "token": p["token"],
                      "swaps": [dict(s, buy=s["a0"] < 0) for s in e["swaps"]], "pulls": e["pulls"], "adds": e["adds"]})
    fresh = json.load(open(os.path.join(D, "fresh_launches.json"))); ev = json.load(open(os.path.join(D, "fresh_logs.json")))
    for c in fresh:
        sw, pu, ad = [], [], []
        for l in ev.get(c["pid"], []):
            bn = int(l["blockNumber"], 16)
            if bn > c["bn"] + 3000: continue
            d = l["data"]; li = int(l["logIndex"], 16); ti = int(l["transactionIndex"], 16)
            if l["topics"][0] == T_SWAP:
                a0 = sgn(W(d, 0)); a1 = sgn(W(d, 1))
                sw.append({"bn": bn, "ti": ti, "li": li, "sender": "0x" + l["topics"][2][-40:], "a0": a0, "a1": a1, "sqrt_p": W(d, 2), "liq": W(d, 3),
                           "tick": sgn(W(d, 4)), "fee": W(d, 5), "tx": l["transactionHash"], "buy": a0 < 0})
            else:
                dl = sgn(W(d, 2)); row = {"bn": bn, "ti": ti, "li": li, "lo": sgn(W(d, 0)), "hi": sgn(W(d, 1)), "dl": dl, "tx": l["transactionHash"]}
                (pu if dl < 0 else ad).append(row) if dl != 0 else None
        sw.sort(key=lambda s: (s["bn"], s["li"])); pu.sort(key=lambda s: (s["bn"], s["li"])); ad.sort(key=lambda s: (s["bn"], s["li"]))
        L0 = sum(a["dl"] for a in ad if a["tx"] == c["tx"])
        pools.append({"pid": c["pid"], "src": "fresh", "b0": c["bn"], "ts0": None, "launcher": c["from"], "nonce": c["nonce"], "sp0": c["sp0"], "L0": L0,
                      "token": c["token"], "swaps": sw, "pulls": pu, "adds": ad})
    for pl in pools:
        for s in pl["swaps"]:
            t = TX.get(s["tx"]); s["from"] = t["from"] if t else None; s["to"] = t["to"] if t else None
            s["sel"] = t["input"][2:10] if t else None; s["input"] = t["input"] if t else None
            s["eth"] = abs(s["a0"])
            s["crowd"] = s["to"] == CROWD
        for x in pl["pulls"]:
            t = TX.get(x["tx"]); x["from"] = t["from"] if t else None; x["to"] = t["to"] if t else None; x["sel"] = t["input"][2:10] if t else None
            x["input"] = t["input"] if t else None
        pl["pull_bn"] = pl["pulls"][0]["bn"] if pl["pulls"] else None
        cr = [s for s in pl["swaps"] if s["crowd"] and s["buy"]]
        pl["crowd1"] = cr[0]["bn"] if cr else None
        pl["missing_tx"] = sum(1 for s in pl["swaps"] if s["from"] is None)
    return pools, TX

def replay(pl, B, S, stake=STAKE, drop=lambda s: False):
    """our buy at the END of block B, our sell at the HEAD of block S. Every other swap is replayed by its own shift (buys: Q96/sqrtP
    += its own delta; sells: sqrtP += its own delta) from the pool's start state; `drop(s)` removes a swap (e.g. our relay's own).
    Returns (ret, why): a pull in a block <= S loses the stake (-1); a pull <= B: no trade."""
    if pl["pull_bn"] is not None and pl["pull_bn"] <= B: return None, "pulled_before_buy"
    prev = pl["sp0"]; L = pl["L0"]; s_cf = float(pl["sp0"]); bought = False; tokens = 0
    for x in pl["swaps"]:
        if not bought and x["bn"] > B:
            fee = x["fee"]; tokens = v4math.buy_out(s_cf, L, stake * (1 - fee / 1e6))
            s_cf = v4math.sqrt_after_buy(s_cf, L, stake * (1 - fee / 1e6)); bought = True; feeb = fee
        if bought and x["bn"] >= S: break
        if not drop(x):
            if x["buy"]: s_cf = Q96 / (Q96 / s_cf + (Q96 / x["sqrt_p"] - Q96 / prev))
            else: s_cf = s_cf + (x["sqrt_p"] - prev)
        prev = x["sqrt_p"]; L = x["liq"]
    if not bought:
        fee = pl["swaps"][-1]["fee"] if pl["swaps"] else 100
        tokens = v4math.buy_out(s_cf, L, stake * (1 - fee / 1e6)); s_cf = v4math.sqrt_after_buy(s_cf, L, stake * (1 - fee / 1e6)); feeb = fee
    if pl["pull_bn"] is not None and pl["pull_bn"] <= S: return -1.0 - GAS_ETH * 1e18 / stake, "pulled"
    out = v4math.sell_out(s_cf, L, tokens * (1 - feeb / 1e6))
    return out / stake - 1 - GAS_ETH * 1e18 / stake, "sold"
