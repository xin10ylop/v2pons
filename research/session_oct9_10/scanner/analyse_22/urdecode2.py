"""decode the 2-ETH operator's crowd buys (UR execute, 1,284 bytes, nonce-0 wallets): commands 0x10 (V4_SWAP) + 0x04 (SWEEP); V4_SWAP actions
07 0b 0e = SWAP_EXACT_IN, SETTLE, TAKE; SWAP_EXACT_IN params = ExactInputParams(currencyIn, PathKey[] path, [uint256[] maxHopSlippage,]
uint128 amountIn, uint128 amountOutMinimum) (word layout checked by urraw.py). Prints amountIn, amountOutMinimum, minOut / the output the chain gave,
and the room: the ETH that can be bought ahead of the FIRST crowd buy (from the chain state just before it) before its output falls under its minOut."""
import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
from eth_abi import decode
T = load_txs(); T.update(json.load(open("extra_txs.json")))
K = json.load(open("keys.json")); F = load_families(); P = load_pools()
F100 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true"
pids = F[K[0]]["pids"] + F[F100]["pids"]
E = load_events(set(pids))
PK = "(address,uint24,int24,address,bytes)"
def swap_in(p):
    for types in (["(address,%s[],uint256[],uint128,uint128)" % PK],):   # (currencyIn, path, maxHopSlippage, amountIn, amountOutMinimum): checked word by word (urraw.py)
        try:
            v = decode(types, p)[0]; return v[-2], v[-1], len(v)
        except Exception: pass
    return None
rows = []
for pid in pids:
    for s in E[pid]["swaps"]:
        t = T.get(s["tx"])
        if not t or t["to"] != "0x8876789976decbfcbbbe364623c63652db8c0904" or t["calldata_len"] != 1284 or t["nonce"] != 0 or s["a0"] >= 0: continue
        b = bytes.fromhex(t["input"][10:])
        cmds, inputs, dl = decode(["bytes", "bytes[]", "uint256"], b)
        actions, params = decode(["bytes", "bytes[]"], inputs[0])
        r = swap_in(params[0])
        if r is None: print("fail", pid[:10], cmds.hex(), actions.hex()); continue
        amt, mo, nf = r
        rows.append((pid[:10], s["bn"] - P[pid]["launch_block"], amt / 1e18, -s["a0"] / 1e18, mo, s["a1"], (mo / s["a1"]) if s["a1"] else None, cmds.hex(), actions.hex(), nf, dl - P[pid]["launch_ts"]))
for r in rows[:6]: print(r)
ratios = sorted(r[6] for r in rows if r[6] is not None)
print("n", len(rows), "minOut/actual output: min", ratios[0], "median", ratios[len(ratios)//2], "max", ratios[-1], "zero minOut", sum(1 for r in rows if r[4] == 0))

sys.path.insert(0, "/home/user/v2pons/src"); sys.path.insert(0, ".")
from common22 import Pool, room, load_blocks_meta, Q96
import v4math, statistics as st
M = load_blocks_meta(); caps = []; caps_launch = []
for pid in pids:
    pl = Pool(P[pid], E[pid], T, M)
    c = next((x for x in pl.seq if x["buy"] and x["to"] == "0x8876789976decbfcbbbe364623c63652db8c0904" and x["clen"] == 1284 and x["nonce"] == 0), None)
    if not c: continue
    b = bytes.fromhex(c["input"][10:]); cmds, inputs, dl = decode(["bytes", "bytes[]", "uint256"], b); actions, params = decode(["bytes", "bytes[]"], inputs[0])
    amt, mo, nf = swap_in(params[0])
    s_pre, L = pl.state_through(None, upto_li=(c["bn"], c["li"]))
    s0, L0 = pl.launch_state()
    caps.append(room(s_pre, L, c["eth"], c["fee"], mo)); caps_launch.append(room(s0, L0, c["eth"], c["fee"], mo))
    print(pid[:10], "first crowd +%d" % (c["bn"] - pl.b0), "Y %.5f" % (c["eth"] / 1e18), "minOut/out %.4f" % (mo / c["a1"]), "room from pre-buy state %.4f ETH" % caps[-1], "from launch state %.4f" % caps_launch[-1])
print("room p10/50/90 (pre-buy state)", sorted(caps)[len(caps)//10], st.median(caps), sorted(caps)[int(len(caps)*.9)])
print("room p10/50/90 (launch state)", sorted(caps_launch)[len(caps_launch)//10], st.median(caps_launch), sorted(caps_launch)[int(len(caps_launch)*.9)])
json.dump({"minout_over_actual_output": {"n": len(rows), "min": ratios[0], "median": ratios[len(ratios)//2], "max": ratios[-1]},
           "room_first_crowd_pre_state": caps, "room_first_crowd_launch_state": caps_launch}, open("crowd_minout.json", "w"), indent=1)
