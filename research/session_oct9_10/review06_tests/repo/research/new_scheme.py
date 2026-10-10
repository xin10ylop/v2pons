#!/usr/bin/env python3
"""The operator's scheme from Oct 8 14:59, read from the chain: every ETH pool launched in a window, the operator's found by its
launch call (0x2fcb9108: from 14:59 each launch has a freshly deployed launcher, the same 6,984 bytes of code), the block of its
crowd's burst, and two trades priced on every pool (no reaction to us assumed):
  follow  our buy 2 blocks after the first real-size buy, sold on the first buy behind ours worth 1% or by our buy + 4 (release 0.3)
  seat    our buy at the head of launch + k, ahead of the burst, sold on the burst (at the latest 12 blocks after our buy)
On Oct 8 14:45-16:45: the follow trade -0.5% on all 42 operator launches (its first three buys land in one block, nothing behind
them); the seat +8.9% at $3, 42 of 42; no other family has the old pattern.

    python3 research/new_scheme.py 83394000 [last_block]
"""
import json, sys, time, collections, statistics as st, urllib.request, urllib.error, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from eth_utils import keccak
RPC = "https://rpc.mainnet.chain.robinhood.com"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; UR = "8876789976decbfcbbbe364623c63652db8c0904"; OP = "3194e32622c5d860a0572c74edda99dcfd8fc827"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16)
def sgn(x): return x - (1 << 256) if x >= (1 << 255) else x
def post(body):
    for i in range(10):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(body).encode(), H), timeout=90))
        except urllib.error.HTTPError as e: time.sleep(4 * (i + 1) if e.code == 429 else 2)
        except Exception: time.sleep(2 + i)
    raise RuntimeError("rpc")
def rpc(m, p):
    r = post({"jsonrpc": "2.0", "id": 1, "method": m, "params": p})
    if "error" in r: raise RuntimeError(str(r["error"])[:200])
    return r["result"]
def batch(calls):
    out = []
    for i in range(0, len(calls), 50):
        ch = calls[i:i+50]
        r = post([{"jsonrpc": "2.0", "id": j, "method": m, "params": p} for j, (m, p) in enumerate(ch)])
        r = sorted(r, key=lambda x: x["id"]); out += [x.get("result") for x in r]
    return out
def logs(flt, a, b):
    try: return rpc("eth_getLogs", [dict(flt, fromBlock=hex(a), toBlock=hex(b))])
    except RuntimeError as e:
        if b <= a: raise
        m = (a + b) // 2; return logs(flt, a, m) + logs(flt, m + 1, b)
import v4math
Q96 = 1 << 96; STAKE = int(0.0012e18); GAS = 250_000 * 22_000_000
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
head = int(sys.argv[2]) if len(sys.argv) > 2 else int(rpc("eth_blockNumber", []), 16)
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, int(sys.argv[1]), head)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
P = {}
for l, t in zip(inits, txs):
    d = l["data"]
    if d[2+64*2+24:2+64*3] != "0"*40: continue                                   # hooked pools: the relay trades no-hook only
    fam = "operator (0x2fcb9108)" if t["input"][:10] == "0x2fcb9108" else f"{t['to'][:10]} {t['input'][:10]}"
    P[l["topics"][1]] = {"b0": int(l["blockNumber"], 16), "fee": W(d, 0), "sp0": W(d, 3), "tick0": sgn(W(d, 4)), "fam": fam}
pids = sorted(P, key=lambda p: P[p]["b0"]); ev = collections.defaultdict(list)
for i in range(0, len(pids), 60):
    bt = pids[i:i+60]; lo = min(P[p]["b0"] for p in bt); hi = min(max(P[p]["b0"] for p in bt) + 1500, head)
    for a in range(lo, hi + 1, 99999):
        for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], bt]}, a, min(a + 99998, hi)): ev[l["topics"][1]].append(l)
def trade(p, B, exit_rule):
    """$3 at the head of block B; exit_rule(sw_after) -> landing block; -100% if the pull lands first"""
    q = P[p]; ls = sorted(ev[p], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    adds = [(sgn(W(l["data"], 0)), sgn(W(l["data"], 1)), sgn(W(l["data"], 2))) for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) > 0 and int(l["blockNumber"], 16) < B]
    liq0 = v4math.active_liquidity(q["tick0"], adds)
    sw = [(int(l["blockNumber"], 16), s128(W(l["data"], 0)), W(l["data"], 2), W(l["data"], 3)) for l in ls if l["topics"][0] == T_SWAP]
    pulls = [int(l["blockNumber"], 16) for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0]; pull = min(pulls) if pulls else None
    if pull is not None and pull <= B or liq0 <= 0: return None
    prev = [x for x in sw if x[0] < B]; sp, L = (prev[-1][2], prev[-1][3]) if prev else (q["sp0"], liq0)
    if L < 1e21: return None
    fee = q["fee"]; tok = v4math.buy_out_int(sp, L, STAKE, fee); xn = STAKE - (STAKE * fee + 999_999) // 1_000_000
    ret_at = lambda spc, Lc: (v4math.sell_out_int(int(Q96 / (Q96 / spc + xn / Lc)), Lc, tok, fee) - STAKE - GAS) / STAKE
    land = exit_rule(B, [x for x in sw if x[0] >= B], ret_at)
    if pull is not None and pull <= land: return -1.0
    pv = [x for x in sw if x[0] <= land - 1]; spl, Ll = (pv[-1][2], pv[-1][3]) if pv else (sp, L)
    return ret_at(spl, Ll)
def tp_rule(maxwait):
    def r(B, after, ret_at):
        for x in after:
            if x[0] - B <= maxwait and x[1] < 0 and ret_at(x[2], x[3]) >= 0.01: return x[0] + 2
        return B + maxwait + 2
    return r

offs = collections.Counter()
for p in pids:
    if not P[p]["fam"].startswith("operator"): continue
    sw = sorted((int(l["blockNumber"], 16), s128(W(l["data"], 0))) for l in ev[p] if l["topics"][0] == T_SWAP)
    real = [x for x in sw if x[1] <= -2e14]
    if real: offs[real[0][0] - P[p]["b0"]] += 1
print(f"blocks {sys.argv[1]}-{head}: {len(P)} no-hook ETH pools, {sum(1 for p in P if P[p]['fam'].startswith('operator'))} by the operator's launch call")
print("the burst's block after the launch:", sorted(offs.items()))
print("\nTHE SEAT on the operator's launches: $X at launch + k, sold on the burst")
for stake_eth in (0.00015, 0.0005, 0.0012, 0.005):
    STAKE = int(stake_eth * 1e18)
    for k in (5, 7):
        v = [r for p in pids if P[p]["fam"].startswith("operator") for r in [trade(p, P[p]["b0"] + k, tp_rule(12))] if r is not None]
        if v: print(f"   ${stake_eth*2570:5.2f} landing at launch +{k}: n {len(v)}, mean {st.mean(v):+.1%} (gas in), worst {min(v):+.1%}, positive {sum(1 for x in v if x > 0)}/{len(v)}")
STAKE = int(0.0012e18)
print("\nTHE FOLLOW TRADE on every launch family (land first real buy + 2, take profit, out by + 4)")
fam = collections.defaultdict(list)
for p in pids:
    sw = sorted((int(l["blockNumber"], 16), s128(W(l["data"], 0))) for l in ev[p] if l["topics"][0] == T_SWAP)
    real = [x for x in sw if x[1] <= -2e14 and x[0] - P[p]["b0"] <= 150]
    if not real: continue
    r = trade(p, real[0][0] + 2, tp_rule(2))
    if r is not None: fam[P[p]["fam"]].append(r)
for f, v in sorted(fam.items(), key=lambda kv: -len(kv[1])):
    print(f"   {f:28s} n {len(v):3d}: mean {st.mean(v):+.2%}, positive {sum(1 for x in v if x > 0)}/{len(v)}, worst {min(v):+.1%}")
