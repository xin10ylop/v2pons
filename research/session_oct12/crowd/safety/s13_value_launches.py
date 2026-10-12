"""the 836-byte PositionManager multicalls that created a fee-100 WETH pool WITH a value (s01's 'other shapes': not the engine's v3crowd family,
whose value_wei is 0): their value, sender, decode, the token's template. Writes s13_value_launches.out (stdout)."""
from common import *
import rpc
from v3dec import decode_launch_v3
m = json.load(open(J("s01_launches.json"))); head = m["head"]; start = m["start"]
pc = []
for a in range(start, head + 1, 200000): pc += rpc.logs({"address": FACT, "topics": [T_PC]}, a, min(a + 199999, head))
cand = [l for l in pc if int(l["topics"][3], 16) == 100 and WETH[2:] in (l["topics"][1][-40:], l["topics"][2][-40:])]
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in cand])
for l, t in zip(cand, txs):
    n = (len(t["input"]) - 2) // 2; v = int(t["value"], 16)
    if (t["to"] or "").lower() == NPM and t["input"][:10] == "0xac9650d8" and n == 836 and v > 0:
        d = decode_launch_v3(bytes.fromhex(t["input"][2:])); tok = "0x" + d["token"] if d else None
        c = rpc.call("eth_getCode", [tok, "latest"]) if tok else "0x"
        print(f"block {int(l['blockNumber'], 16)} from {t['from']} value {v / 1e18:.6f} ETH qs {d['qs'] if d else None} hi {d['hi'] if d else None} token {tok} code {len(c) // 2 - 1} B {('0x' + keccak(bytes.fromhex(c[2:])).hex())[:14]}")
print(rpc.STATS)
