"""Copy of session_oct11/lines/analysis/H/h03_sim.py (outputs redirected here). The hooked pump line (tok a98b3b9e, fee 3000 / ts 60, a hook per pool): can our relay buy and sell? eth_call only, nothing sent.
Adapted from V/v22_sim.py: the harness as code at our wallet (the relay's owner), the relay's balance overridden to 0.05 ETH."""
import os, sys, json
H = os.path.dirname(os.path.abspath(__file__)); V = "/home/user/v2pons/research/session_oct11/lines/analysis/V"; sys.path.insert(0, V)
os.environ.setdefault("LOG_PATH", os.path.join(H, "engine_import.jsonl"))
import rpc
from sim import *
import flip_engine as fe, harness
from eth_utils import keccak
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16); sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
WALLET = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"; RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"; STANDIN = "0x" + "c2" * 20
head = int(rpc.call("eth_blockNumber", []), 16)
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 8
start = head - int(hours * 3600 * 9.8); ls = []
for a in range(start, head + 1, 4000):
    ls += rpc.call("eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(min(a + 3999, head)), "address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}])
cand = [l for l in ls if W(l["data"], 0) == 3000 and sgn(W(l["data"], 1)) == 60 and int(l["data"][130:194], 16) != 0]
pools = []
for l in cand:
    t = rpc.call("eth_getTransactionByHash", [l["transactionHash"]])
    if t and (t.get("to") or "").lower() == POSM and t["input"][2:10] == "ac9650d8" and (len(t["input"]) - 2) // 2 == 2020 and int(t["value"], 16) == 0:
        pools.append({"pool": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "hooks": "0x" + l["data"][154:194], "fee": "3000", "tick_spacing": "60", "launch_block": str(int(l["blockNumber"], 16)), "launch_utc": "chain"})
print(f"head {head}: {len(cand)} hooked fee-3000/ts-60 ETH pools initialised in the last {hours:g} h, {len(pools)} with the line's launch shape")
pools.sort(key=lambda x: int(x["launch_block"]), reverse=True)
def extsload(slot): return int(rpc.call("eth_call", [{"to": PM, "data": "0x" + keccak(text="extsload(bytes32)").hex()[:8] + "%064x" % slot}, "latest"]), 16)
art = json.load(open(os.path.join(REPO, "contracts", "FlipRelay.json")))
def runtime(owner):
    code = bytearray.fromhex(art["deployedBytecode"][2:])
    for ast_id, val in zip(sorted(art["immutableReferences"], key=int), (PM, owner)):
        for r in art["immutableReferences"][ast_id]: code[r["start"]:r["start"] + r["length"]] = bytes(12) + bytes.fromhex(val[2:])
    return "0x" + code.hex()
HC = harness.assemble(); Q = int(0.002e18); results = []; done = 0
for x in pools[:12]:
    pid = x["pool"]; ss = int(keccak(bytes.fromhex(pid[2:]) + (6).to_bytes(32, "big")).hex(), 16)
    s0 = extsload(ss); sqrt = s0 & ((1 << 160) - 1); L = extsload(ss + 3)
    lg = rpc.call("eth_getLogs", [{"fromBlock": hex(int(x["launch_block"])), "toBlock": hex(head), "address": PM, "topics": [T_ML, pid]}])
    pulled = any(sgn(W(l["data"], 2)) < 0 for l in lg)
    print(f"pool {pid[:12]} launch {x['launch_block']} ({x['launch_utc']}) hook {x['hooks'][:12]}: liquidity {L}, sqrtP {sqrt}, pulled {pulled}")
    if pulled or L == 0 or sqrt == 0: continue
    pf = (s0 >> 184) & ((1 << 24) - 1); lpf = (s0 >> 208) & ((1 << 24) - 1); pf01, pf10 = pf & 0xfff, pf >> 12
    fee_buy = pf01 + lpf - pf01 * lpf // 1_000_000; fee_sell = pf10 + lpf - pf10 * lpf // 1_000_000
    p = {"c0": "0" * 40, "token": x["token"][2:], "fee": int(x["fee"]), "tick_spacing": int(x["tick_spacing"]), "hooks": x["hooks"][2:]}
    pred = v4math.buy_out_int(sqrt, L, Q, fee_buy); s1 = sqrt_buy(sqrt, L, Q, fee_buy); pred_back = v4math.sell_out_int(s1, L, pred, fee_sell)
    buy = fe.tx_buy(p, 0, 0, 0, stake=Q)["data"]; sell = fe.tx_sell(p, 0)["data"]; bal = "0x70a08231" + "%064x" % int(RELAY, 16)
    ov = {WALLET: {"code": HC}, RELAY: {"balance": hex(int(0.05e18))}}
    print(f"  fees buy {fee_buy} / sell {fee_sell} ppm; depth {L * (1 << 96) / sqrt / 1e18:.3f} ETH; v4math: buy {pred} tokens, sell back {pred_back / 1e18:.8f} ETH ({pred_back / Q - 1:+.3%})")
    for name, calls in (("buy only", [(RELAY, buy), (x["token"], bal)]), ("buy+sell", [(RELAY, buy), (x["token"], bal), (RELAY, sell), (x["token"], bal)])):
        try:
            r = rpc.call("eth_call", [{"from": "0x" + "c0" * 20, "to": WALLET, "data": harness.encode(calls), "gas": hex(8_000_000)}, "latest", ov])
            ws = [int(r[2 + 64*i: 2 + 64*(i+1)], 16) for i in range((len(r) - 2) // 64)]
            if name == "buy only":
                print(f"  {name}: tokens {ws[0]} (v4math {pred}: {'exact' if ws[0] == pred else f'off {ws[0] / pred - 1:+.2%}'}), relay holds {ws[1]}")
            else:
                print(f"  {name}: sell returned {ws[2] / 1e18:.8f} ETH (v4math {pred_back / 1e18:.8f}: {'exact' if ws[2] == pred_back else f'off {ws[2] / pred_back - 1:+.2%}'}), round trip {ws[2] / Q - 1:+.3%}, tokens left {ws[3]}")
            results.append({"pool": pid, "case": name, "words": ws, "pred": pred, "pred_back": pred_back})
        except RuntimeError as e:
            print(f"  {name}: REVERTED: {str(e)[:260]}"); results.append({"pool": pid, "case": name, "revert": str(e)[:600]})
    done += 1
    if done >= 3: break
json.dump({"head": head, "results": results}, open(os.path.join(H, "s14_hooksim.json"), "w"), indent=1)
print(rpc.STATS)
