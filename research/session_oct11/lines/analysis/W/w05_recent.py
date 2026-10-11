"""Forward-test data: the V3 crowd line's launches of the last N hours from the chain (public RPC, read-only, polite).
factory PoolCreated (fee 100, WETH side) -> launch txs (to the V3 PositionManager, multicall, 836 bytes, value 0) -> their receipts ->
every Swap/Mint/Burn of those pools to the head -> the txs of the first real buys (>= 0.005 ETH) of each pool -> w05_recent.json"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpc
from eth_utils import keccak
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
FACT = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"; NPM = "0x73991a25c818bf1f1128deaab1492d45638de0d3"; WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
tp = lambda s: "0x" + keccak(text=s).hex()
T_PC = tp("PoolCreated(address,address,uint24,int24,address)"); T_SW = tp("Swap(address,address,int256,int256,uint160,uint128,int24)")
T_MI = tp("Mint(address,address,int24,int24,uint128,uint256,uint256)"); T_BU = tp("Burn(address,int24,int24,uint128,uint256,uint256)")
T_IN = tp("Initialize(uint160,int24)")
head = int(rpc.call("eth_blockNumber", []), 16)
bh = rpc.call("eth_getBlockByNumber", [hex(head), False]); t_head = int(bh["timestamp"], 16)
b0 = rpc.call("eth_getBlockByNumber", [hex(head - 20000), False]); bps = 20000 / max(1, t_head - int(b0["timestamp"], 16))
start = head - int(hours * 3600 * bps)
print(f"head {head} {time.strftime('%H:%M:%S', time.gmtime(t_head))} UTC, {bps:.2f} blocks/s, from {start} ({hours} h)")
pc = []
for a in range(start, head + 1, 50000):
    pc += rpc.logs({"address": FACT, "topics": [T_PC]}, a, min(a + 49999, head))
cand = [l for l in pc if int(l["topics"][3], 16) == 100 and WETH[2:] in (l["topics"][1][-40:], l["topics"][2][-40:])]
print(f"PoolCreated {len(pc)}, fee 100 with WETH {len(cand)}")
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in cand])
line = []
for l, t in zip(cand, txs):
    if t and (t.get("to") or "").lower() == NPM and t["input"][:10] == "0xac9650d8" and (len(t["input"]) - 2) // 2 == 836 and int(t["value"], 16) == 0:
        line.append({"pool": "0x" + l["data"][-40:], "token0": "0x" + l["topics"][1][-40:], "token1": "0x" + l["topics"][2][-40:], "lb": int(l["blockNumber"], 16), "tx": t})
others = sorted({((t.get("to") or "")[:10], t["input"][:10], (len(t["input"]) - 2) // 2, int(t["value"], 16) > 0) for l, t in zip(cand, txs) if t} - {(NPM[:10], "0xac9650d8", 836, False)})
print(f"line launches {len(line)}; other fee-100 WETH launch shapes: {others[:10]}")
rcs = rpc.batch("eth_getTransactionReceipt", [[x["tx"]["hash"]] for x in line], n=10)
for x, r in zip(line, rcs): x["receipt"] = r
pools = [x["pool"] for x in line]; ev = []
if pools:
    a0 = min(x["lb"] for x in line)
    for i in range(0, len(pools), 25):
        for a in range(a0, head + 1, 20000):
            ev += rpc.logs({"address": pools[i:i + 25], "topics": [[T_SW, T_MI, T_BU]]}, a, min(a + 19999, head))
print(f"pool events {len(ev)}")
by = {}
for l in ev: by.setdefault(l["address"].lower(), []).append(l)
want = []
for x in line:
    ls = sorted(by.get(x["pool"], []), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    x["logs"] = ls
    qs = 0 if x["token0"] == WETH else 1; n = 0
    for l in ls:
        if l["topics"][0] != T_SW: continue
        d = l["data"]; a0_ = int(d[2:66], 16); a1_ = int(d[66:130], 16)
        a0_ = a0_ - (1 << 256) if a0_ >> 255 else a0_; a1_ = a1_ - (1 << 256) if a1_ >> 255 else a1_
        dq = a0_ if qs == 0 else a1_
        if dq >= 5 * 10 ** 15 and n < 8:
            want.append(l["transactionHash"]); n += 1
want = sorted(set(want))
stx = rpc.batch("eth_getTransactionByHash", [[h] for h in want]) if want else []
json.dump({"head": head, "t_head": t_head, "bps": bps, "start": start, "hours": hours, "line": line, "buy_txs": dict(zip(want, stx)), "other_shapes": others},
          open(f"w05_recent_{hours:g}h.json", "w"))
print("saved", rpc.STATS)
