"""S01: the V3 self-buying launcher family lc:0a493d1a|13ead562 (REPORT_C candidate 2): every launch of the last H hours (default 50).
Public RPC only, read-only, polite (rpc.py = W/rpc.py: one POST at a time, >= 0.5 s apart).
Factory PoolCreated -> the creating tx -> keep txs to the V3 NonfungiblePositionManager 0x73991a25 calling createAndInitializePoolIfNecessary
(13ead562, 132 B) directly (= lc:0a493d1a|13ead562; 0a493d1a is the NonfungiblePositionManager's code hash prefix, checked here) -> s01_launches.json"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpc
from eth_utils import keccak
OUT = os.path.dirname(os.path.abspath(__file__))
H = float(sys.argv[1]) if len(sys.argv) > 1 else 50.0
FACT = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"; NPM = "0x73991a25c818bf1f1128deaab1492d45638de0d3"; WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
T_PC = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex()
head = int(rpc.call("eth_blockNumber", []), 16)
t_head = int(rpc.call("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
code = rpc.call("eth_getCode", [NPM, "latest"]); ch = keccak(bytes.fromhex(code[2:])).hex()
print(f"head {head} {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t_head))} UTC; NPM code hash {ch[:8]}")
# the start block: the first block with timestamp >= t_head - H h (binary search on the public node)
lo, hi = head - int(H * 3600 * 12), head
while lo < hi:
    m = (lo + hi) // 2
    if int(rpc.call("eth_getBlockByNumber", [hex(m), False])["timestamp"], 16) < t_head - H * 3600: lo = m + 1
    else: hi = m
start = lo
print(f"start {start} (= head - {head - start} blocks, {H} h, {(head - start) / (H * 3600):.3f} blocks/s)")
pc = []
for a in range(start, head + 1, 50000):
    pc += rpc.logs({"address": FACT, "topics": [T_PC]}, a, min(a + 49999, head))
print(f"PoolCreated {len(pc)}")
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in pc])
fam = []; shapes = {}
for l, t in zip(pc, txs):
    if not t: continue
    k = ((t.get("to") or "").lower()[:10], t["input"][:10], (len(t["input"]) - 2) // 2)
    shapes[str(k)] = shapes.get(str(k), 0) + 1
    if (t.get("to") or "").lower() != NPM or t["input"][2:10] != "13ead562": continue
    t0 = "0x" + l["topics"][1][-40:]; t1 = "0x" + l["topics"][2][-40:]
    fam.append({"pool": "0x" + l["data"][-40:], "token0": t0, "token1": t1, "fee": int(l["topics"][3], 16), "ts_": int(l["data"][2:66], 16),
                "lb": int(l["blockNumber"], 16), "ti": int(l["transactionIndex"], 16), "launch_tx": t["hash"], "launch_from": t["from"].lower(),
                "launch_len": (len(t["input"]) - 2) // 2, "launch_value": int(t["value"], 16), "launch_nonce": int(t["nonce"], 16),
                "qs": 0 if t0 == WETH else 1 if t1 == WETH else None, "sqrtp_init": int(t["input"][2 + 8 + 64 * 3: 2 + 8 + 64 * 4], 16)})
bl = rpc.batch("eth_getBlockByNumber", [[hex(x["lb"]), False] for x in fam])
for x, b in zip(fam, bl): x["ts"] = int(b["timestamp"], 16)
json.dump({"head": head, "t_head": t_head, "start": start, "H": H, "npm_code_hash": ch, "n_poolcreated": len(pc), "shapes": shapes, "launches": fam},
          open(os.path.join(OUT, "s01_launches.json"), "w"), indent=0)
print(f"13ead562 launches {len(fam)}; WETH-side {sum(1 for x in fam if x['qs'] is not None)}; fee {sorted(set(x['fee'] for x in fam))}; wallets {len(set(x['launch_from'] for x in fam))}")
print("rpc", rpc.STATS)
