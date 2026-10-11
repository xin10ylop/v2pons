"""Can we buy and sell a live C-1 pool? eth_call only (no key, nothing sent):
1. find the live C-1 pools (post-census Initialize logs, launch tx shape, no negative ModifyLiquidity yet);
2. read the pool's current state from the PoolManager (extsload of slot0 and liquidity);
3. check the deployed relay 0x2abb5653 is FlipRelay with pm = PoolManager and owner = our wallet 0xab5a34c3 (eth_getCode, owner(), pm());
4. state override: the harness (harness.py, raw EVM) as code at our wallet's address, so it is the relay's owner; the relay's balance set
   to 0.05 ETH; a second FlipRelay instance (owner = our wallet) at 0xc2c2.. with 1 ETH stands in for the bot;
5. the engine's own calldata (flip_engine.tx_buy / tx_sell) for 0.0058 ETH: (A) buy then sell at once, (B) buy, the stand-in buys the
   bot's median 0.14 ETH, sell, (C) buy with minOut = the v4math prediction + 1 (must revert TooLittleOut if the prediction is exact).
Predictions from src/v4math with the state read in step 2."""
import os, sys
os.environ.setdefault("LOG_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine_import.jsonl"))
import rpc
from sim import *
import flip_engine as fe, harness
from eth_utils import keccak
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16); sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
WALLET = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"; RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"; STANDIN = "0x" + "c2" * 20
head = int(rpc.call("eth_blockNumber", []), 16)
# 1. live pools
F = json.load(open(os.path.join(V, "fresh.json"))); cands = {x["pid"]: x for x in F["c1"]}
ls = rpc.call("eth_getLogs", [{"fromBlock": hex(F["head"] + 1), "toBlock": hex(head), "address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}])
for l in ls:
    d = l["data"]
    if W(d, 0) == 100 and sgn(W(d, 1)) == 1 and int(d[130:194], 16) == 0:
        t = rpc.call("eth_getTransactionByHash", [l["transactionHash"]])
        if t["to"].lower() == POSM and t["input"][2:10] == "ac9650d8" and (len(t["input"]) - 2) // 2 == 2276 and int(t["value"], 16) == 0:
            cands[l["topics"][1]] = {"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "bn": int(l["blockNumber"], 16), "sqrt": W(d, 3), "tick": sgn(W(d, 4))}
live = []
for pid, x in cands.items():
    lg = rpc.call("eth_getLogs", [{"fromBlock": hex(x["bn"]), "toBlock": hex(head), "address": PM, "topics": [[T_ML, T_SWAP], pid]}])
    pulled = any(l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0 for l in lg)
    last_swap = max((int(l["blockNumber"], 16) for l in lg if l["topics"][0] == T_SWAP), default=None)
    nsw = sum(1 for l in lg if l["topics"][0] == T_SWAP)
    if not pulled: live.append((last_swap or 0, pid, x, nsw))
live.sort(reverse=True)
print(f"head {head}: C-1 pools since the census {len(cands)}, still unpulled {len(live)}: " + ", ".join(f"{p[:10]} (launch {x['bn']}, {n} swaps, last swap {ls_})" for ls_, p, x, n in live))
# 2. state
def extsload(slot): return int(rpc.call("eth_call", [{"to": PM, "data": "0x" + keccak(text="extsload(bytes32)").hex()[:8] + "%064x" % slot}, "latest"]), 16)
# 3. relay check
art = json.load(open(os.path.join(REPO, "contracts", "FlipRelay.json")))
def runtime(owner):
    code = bytearray.fromhex(art["deployedBytecode"][2:])
    for ast_id, val in zip(sorted(art["immutableReferences"], key=int), (PM, owner)):
        for r in art["immutableReferences"][ast_id]: code[r["start"]:r["start"] + r["length"]] = bytes(12) + bytes.fromhex(val[2:])
    return "0x" + code.hex()
dep = rpc.call("eth_getCode", [RELAY, "latest"])
own = rpc.call("eth_call", [{"to": RELAY, "data": "0x8da5cb5b"}, "latest"]); pmr = rpc.call("eth_call", [{"to": RELAY, "data": "0x8970cdff"}, "latest"])
print(f"deployed relay: code {len(dep)//2 - 1} bytes, equals FlipRelay.json runtime with (pm, owner = our wallet): {dep.lower() == runtime(WALLET).lower()}; owner() 0x{own[-40:]}; pm() 0x{pmr[-40:]}")
HC = harness.assemble()
Q = int(0.0058e18); BOTQ = int(0.14e18)
results = []
for _, pid, x, nsw in live[:2]:
    ss = int(keccak(bytes.fromhex(pid[2:]) + (6).to_bytes(32, "big")).hex(), 16)
    s0 = extsload(ss); sqrt = s0 & ((1 << 160) - 1); tick = sgn((s0 >> 160) & ((1 << 24) - 1)) if ((s0 >> 160) & ((1 << 24) - 1)) < (1 << 23) else ((s0 >> 160) & ((1 << 24) - 1)) - (1 << 24)
    L = extsload(ss + 3)
    pf = (s0 >> 184) & ((1 << 24) - 1); lpf = (s0 >> 208) & ((1 << 24) - 1); pf01, pf10 = pf & 0xfff, pf >> 12
    fee_buy = pf01 + lpf - pf01 * lpf // 1_000_000; fee_sell = pf10 + lpf - pf10 * lpf // 1_000_000
    print(f"  slot0 protocolFee zeroForOne {pf01} / oneForZero {pf10} ppm, lpFee {lpf} ppm -> swap fee buy {fee_buy} / sell {fee_sell} ppm")
    Lp = L if L else 100000088127620690885293   # price at the range's upper tick: the buy crosses into the launch position at once
    p = {"c0": "0" * 40, "token": x["token"][2:], "fee": 100, "tick_spacing": 1, "hooks": "0" * 40}
    pred = v4math.buy_out_int(sqrt, Lp, Q, fee_buy)
    s1 = sqrt_buy(sqrt, Lp, Q, fee_buy); pred_back_A = v4math.sell_out_int(s1, Lp, pred, fee_sell)
    s2 = sqrt_buy(s1, Lp, BOTQ, fee_buy); pred_back_B = v4math.sell_out_int(s2, Lp, pred, fee_sell)
    buy = fe.tx_buy(p, 0, int(pred * 0.97), 0, stake=Q)["data"]; sell = fe.tx_sell(p, 0)["data"]
    bal = "0x70a08231" + "%064x" % int(RELAY, 16)
    sb = fe.tx_buy(p, 0, 0, 0, stake=BOTQ)["data"]
    ov = {WALLET: {"code": HC}, RELAY: {"balance": hex(int(0.05e18))}, STANDIN: {"code": runtime(WALLET), "balance": hex(10**18)}}
    print(f"\npool {pid} token {x['token']} ({nsw} swaps so far): slot0 sqrtP {sqrt} tick {tick}, liquidity {L}; price move of our buy {((sqrt / s1) ** 2 - 1):+.4%}")
    print(f"  pool depth: virtual ETH in range L/sqrtP = {Lp * (1 << 96) / sqrt / 1e18:.3f} ETH")
    for name, calls in (("A buy+sell", [(RELAY, buy), (x["token"], bal), (RELAY, sell), (x["token"], bal)]),
                        ("B buy, stand-in 0.14 ETH, sell", [(RELAY, buy), (x["token"], bal), (STANDIN, sb), (RELAY, sell), (x["token"], bal)]),
                        ("C buy minOut=pred+1", [(RELAY, fe.tx_buy(p, 0, pred + 1, 0, stake=Q)["data"])])):
        try:
            r = rpc.call("eth_call", [{"from": "0x" + "c0" * 20, "to": WALLET, "data": harness.encode(calls), "gas": hex(8_000_000)}, "latest", ov])
            ws = [int(r[2 + 64*i: 2 + 64*(i+1)], 16) for i in range((len(r) - 2) // 64)]
            print(f"  {name}: returned words {ws}")
            if name.startswith("A"):
                print(f"    buy got {ws[0]} tokens (v4math {pred}: {'exact' if ws[0] == pred else f'off {ws[0]/pred-1:+.2e}'}); relay holds {ws[1]}; sell returned {ws[2]} wei = {ws[2]/1e18:.8f} ETH (v4math {pred_back_A}: {'exact' if ws[2] == pred_back_A else f'off {ws[2]/pred_back_A-1:+.2e}'}); round trip {ws[2]/Q-1:+.4%}; tokens left {ws[3]}")
            if name.startswith("B"):
                print(f"    after the stand-in's 0.14 ETH buy, our sell returned {ws[3]/1e18:.8f} ETH (v4math {pred_back_B/1e18:.8f}): {ws[3]/Q-1:+.3%} before gas; tokens left {ws[4]}")
            results.append({"pool": pid, "case": name, "words": ws})
        except RuntimeError as e:
            msg = str(e); print(f"  {name}: reverted: {msg[:300]}")
            results.append({"pool": pid, "case": name, "revert": msg[:600]})
json.dump({"head": head, "results": results}, open(os.path.join(V, "v22_sim.json"), "w"), indent=1)
print(rpc.STATS)
