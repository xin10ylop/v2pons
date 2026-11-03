#!/usr/bin/env python3
"""c1exit.py HOURS: C-1's ride re-tested on its most recent pools (the last HOURS hours, default 24), for the exit only: the router's cadence
(the gaps between its buys), and the ride (entry at the router's first-buy block + 2, as the engine lands) with the quiet exit at Q blocks
(sell once the router has not bought for Q blocks; a buy behind ours restarts it) capped at H blocks after our buy, on the recorded pool
(each swap's price and liquidity from its Swap log; our own buy kept in the pool until we sell; the pool's fee; a pull before our sell
counts -100%). Read-only, Robinhood's public RPC."""
import sys, json, os, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../src"))
import hlib as H, v4math
from eth_utils import keccak
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 24
url = H.CH["rh"]["rpc"]; PM = H.CH["rh"]["pm"]; R = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"; POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
T_INIT4 = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP4 = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
sg = lambda h: (lambda x: x - (1 << 256) if x >= 1 << 255 else x)(int(h, 16))
STAKES = [int(float(x) * 1e18) for x in os.environ.get("STAKES", "0.0058").split(",")]; STAKE = STAKES[0]; GAS = int(0.000006e18)   # env STAKES: several stakes, the rides of each
head = int(H.rpc(url, "eth_blockNumber", []), 16); lo = head - int(HOURS * 36000)
logs = []
for a in range(lo, head + 1, 20000):
    logs += H.rpc(url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(min(head, a + 19999)), "address": PM, "topics": [T_INIT4]}]) or []
init = {l["transactionHash"]: l for l in logs if l["topics"][2] == "0x" + "0" * 64}           # native ETH pools only
txs = H.batch(url, [("eth_getTransactionByHash", [h]) for h in init], size=50, workers=4, tries=8)
pools = []
for t in txs:
    if t and (t.get("to") or "").lower() == POSM and (len(t["input"]) - 2) // 2 == 2276 and int(t["value"], 16) == 0:
        l = init[t["hash"]]; d = l["data"][2:]
        if int(d[0:64], 16) == 100 and int(d[64:128], 16) == 1 and int(d[128:192], 16) == 0:
            pools.append({"pid": l["topics"][1], "bn": int(t["blockNumber"], 16), "sp0": int(d[192:256], 16)})
print(f"last {HOURS:g} h: {len(pools)} classic C-1 launches", flush=True)
cache_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out/c1_tx.json")
try:
    tc = json.load(open(cache_p))
except (OSError, ValueError):
    tc = {}
for p in pools:
    hi = min(head, p["bn"] + 3000)
    sw = H.rpc(url, "eth_getLogs", [{"fromBlock": hex(p["bn"]), "toBlock": hex(hi), "address": PM, "topics": [T_SWAP4, p["pid"]]}]) or []
    ml = H.rpc(url, "eth_getLogs", [{"fromBlock": hex(p["bn"] + 1), "toBlock": hex(hi), "address": PM, "topics": [T_ML, p["pid"]]}]) or []
    p["pull"] = min((int(m["blockNumber"], 16) for m in ml if sg(m["data"][2 + 128:2 + 192]) < 0), default=None)
    need = [s["transactionHash"] for s in sw if s["transactionHash"] not in tc]
    for h, x in zip(need, H.batch(url, [("eth_getTransactionByHash", [h]) for h in need], size=50, workers=4, tries=8)):
        tc[h] = [x["from"].lower(), (x.get("to") or "").lower()] if x else [None, None]
    ev = []
    for s in sw:
        d = s["data"][2:]; a0 = sg(d[0:64]); sp = int(d[128:192], 16); L = int(d[192:256], 16); fee = int(d[320:384], 16) if len(d) >= 384 else 100
        ev.append((int(s["blockNumber"], 16), int(s["logIndex"], 16), -a0, sp, L, fee, tc.get(s["transactionHash"], [None, None])[1] == R))
    p["ev"] = sorted(ev)
json.dump(tc, open(cache_p, "w"))
gaps = []; rides = collections.defaultdict(list); first_off = []
QS = (20, 30, 40, 50, 60, 80); HS = (100, 200, 300)
for p in pools:
    rb = [e[0] for e in p["ev"] if e[6] and e[2] > 0]
    if not rb: continue
    first_off.append(rb[0] - p["bn"]); bl = sorted(set(rb)); gaps += [b - a for a, b in zip(bl, bl[1:])]
    entry = rb[0] + 2
    pre = [e for e in p["ev"] if e[0] < entry]                                                  # the pool when our buy lands (at the head of block entry)
    sp = pre[-1][3] if pre else p["sp0"]; L = (pre[-1][4] if pre else None) or max(e[4] for e in p["ev"]); fee = st.median([e[5] for e in p["ev"]]) or 100
    rbs = sorted(set(b for b in rb))
    for STK in STAKES:
        q = v4math.buy_out_int(sp, L, STK, fee)
        def ret_at(b):
            if p["pull"] is not None and p["pull"] <= b:
                return -1.0
            post = [e for e in p["ev"] if e[0] <= b]
            s2 = post[-1][3] if post and post[-1][0] >= entry else sp
            s2 = v4math.sqrt_after_buy(s2, L, STK * (10**6 - fee) // 10**6)                       # our buy is in the pool until we sell
            return (v4math.sell_out_int(int(s2), L, q, fee) - STK - GAS) / STK
        for Hh in HS:
            rides[(STK, "hold", Hh)].append(ret_at(entry + Hh))
            for Q in QS:
                last = rb[0]; ex = entry + Hh
                for b in range(entry, entry + Hh + 1):
                    if any(last < x <= b for x in rbs if x <= b):
                        last = max(x for x in rbs if x <= b)
                    if b - last >= Q:
                        ex = b; break
                rides[(STK, "quiet", Q, Hh)].append(ret_at(ex))
print(f"pumped by the router: {len(first_off)}; its first buy at + {st.median(first_off) if first_off else '-'} (median)")
if gaps:
    gs = sorted(gaps); print(f"gaps between the router's buy blocks: median {st.median(gs)}, p25 {gs[len(gs)//4]}, p75 {gs[3*len(gs)//4]}, p90 {gs[9*len(gs)//10]}; share over 20: {sum(g > 20 for g in gs)/len(gs):.0%}, over 40: {sum(g > 40 for g in gs)/len(gs):.0%}, over 60: {sum(g > 60 for g in gs)/len(gs):.0%}")
for STK in STAKES:
    print(f"ride at {STK/1e18:g} ETH (entry: first buy + 2), mean per trade / won / pulled before the sell; ETH a day at {len(first_off) / (HOURS / 24):.0f} pumped pools a day:")
    for k in sorted((k for k in rides if k[0] == STK), key=str):
        r = rides[k]; print(f"  {' '.join(map(str, k[1:])):16s} n {len(r):3d}  mean {st.mean(r):+.1%}  median {st.median(r):+.1%}  won {sum(x > 0 for x in r):3d}  pulled {sum(x <= -1 for x in r)}"
                            f"  -> {st.mean(r) * STK / 1e18 * len(r) / (HOURS / 24):+.4f} ETH/day")
