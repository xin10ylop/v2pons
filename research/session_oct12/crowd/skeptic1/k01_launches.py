"""Skeptic 1, step 1: every v3crowd-shaped launch from Oct 10 12:00 UTC (block 84,980,908, the replay's start) to a frozen head.
V3 factory PoolCreated (fee 100, WETH on one side) -> the creating tx -> keep to == NPM, multicall ac9650d8, 836 B, value 0.
Block timestamps of every launch block (for the windows). Read-only, public RPC, paced (rpc.py from ../../c1)."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpc
from eth_utils import keccak
FACT = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"; NPM = "0x73991a25c818bf1f1128deaab1492d45638de0d3"; WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
T_PC = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex()
START = 84980908
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "k01_launches.json")
head = int(rpc.call("eth_blockNumber", []), 16)
hb = rpc.call("eth_getBlockByNumber", [hex(head), False]); t_head = int(hb["timestamp"], 16)
print(f"head {head} {time.strftime('%m-%d %H:%M:%S', time.gmtime(t_head))} UTC")
pc = []
for a in range(START, head + 1, 50000):
    pc += rpc.logs({"address": FACT, "topics": [T_PC]}, a, min(a + 49999, head))
cand = [l for l in pc if int(l["topics"][3], 16) == 100 and WETH[2:] in (l["topics"][1][-40:], l["topics"][2][-40:])]
print(f"PoolCreated {len(pc)}; fee 100 with WETH {len(cand)}")
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in cand])
line, other = [], {}
for l, t in zip(cand, txs):
    shape = ((t.get("to") or "").lower(), t["input"][:10], (len(t["input"]) - 2) // 2, int(t["value"], 16))
    if shape == (NPM, "0xac9650d8", 836, 0):
        line.append({"pool": "0x" + l["data"][-40:], "token0": "0x" + l["topics"][1][-40:], "token1": "0x" + l["topics"][2][-40:], "lb": int(l["blockNumber"], 16),
                     "hash": t["hash"], "from": t["from"].lower(), "input": t["input"], "ti": int(t["transactionIndex"], 16)})
    else:
        k = f"{shape[0][:10]}:{shape[1]}:{shape[2]}:{'v' if shape[3] else '0'}"; other[k] = other.get(k, 0) + 1
print(f"line launches {len(line)}; other fee-100 WETH launch shapes {other}")
blks = sorted({x["lb"] for x in line})
hdr = rpc.batch("eth_getBlockByNumber", [[hex(b), False] for b in blks])
ts = {b: (int(h["timestamp"], 16), int(h.get("baseFeePerGas", "0x0"), 16)) for b, h in zip(blks, hdr)}
for x in line:
    x["ts"], x["basefee"] = ts[x["lb"]]
json.dump({"head": head, "t_head": t_head, "start": START, "line": line, "other_shapes": other}, open(OUT, "w"))
print("saved", len(line), rpc.STATS)
