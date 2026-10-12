"""Skeptic 1, step 7: (a) launches of the line after the frozen head (is the line still launching?); (b) the ETH price from the deepest
USDG/WETH V3 pool (0x52e65b17..., fee 100) read myself: token0(), token1(), decimals(), slot0()."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpc
from eth_utils import keccak
HERE = os.path.dirname(os.path.abspath(__file__))
FACT = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"; NPM = "0x73991a25c818bf1f1128deaab1492d45638de0d3"; WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
T_PC = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex()
D = json.load(open(os.path.join(HERE, "k01_launches.json")))
head = int(rpc.call("eth_blockNumber", []), 16); th = int(rpc.call("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
pc = rpc.logs({"address": FACT, "topics": [T_PC]}, D["head"] + 1, head)
cand = [l for l in pc if int(l["topics"][3], 16) == 100 and WETH[2:] in (l["topics"][1][-40:], l["topics"][2][-40:])]
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in cand]) if cand else []
new = [t for t in txs if (t.get("to") or "").lower() == NPM and t["input"][:10] == "0xac9650d8" and (len(t["input"]) - 2) // 2 == 836 and int(t["value"], 16) == 0]
last = max(x["ts"] for x in D["line"])
print(f"head now {head} {time.strftime('%m-%d %H:%M:%S', time.gmtime(th))} UTC; PoolCreated since the frozen head {len(pc)}, fee-100 WETH {len(cand)}, line-shaped {len(new)}")
print(f"last line launch {time.strftime('%m-%d %H:%M:%S', time.gmtime(last))} UTC: {(th - last) / 3600:.2f} h without a launch" if not new else f"new launches: {[t['blockNumber'] for t in new]}")
POOL = "0x52e65b17fb6e5ba00ed806f37afcd2daa50271ca"
t0 = "0x" + rpc.call("eth_call", [{"to": POOL, "data": "0x0dfe1681"}, "latest"])[-40:]; t1 = "0x" + rpc.call("eth_call", [{"to": POOL, "data": "0xd21220a7"}, "latest"])[-40:]
fee = int(rpc.call("eth_call", [{"to": POOL, "data": "0xddca3f43"}, "latest"]), 16)
other = t1 if t0 == WETH else t0
dec = int(rpc.call("eth_call", [{"to": other, "data": "0x313ce567"}, "latest"]), 16)
sym = bytes.fromhex(rpc.call("eth_call", [{"to": other, "data": "0x95d89b41"}, "latest"])[2:])[64:].rstrip(b"\0").decode(errors="replace")
sp = int(rpc.call("eth_call", [{"to": POOL, "data": "0x3850c7bd"}, "latest"])[2:66], 16)
wbal = int(rpc.call("eth_call", [{"to": WETH, "data": "0x70a08231" + POOL[2:].zfill(64)}, "latest"]), 16)
p = (sp / 2 ** 96) ** 2                                   # token1 per token0 in raw units
usd = p * 10 ** 18 / 10 ** dec if t0 == WETH else 10 ** 18 / (p * 10 ** dec)    # USDG per WETH in whole units
print(f"pool {POOL} fee {fee}: token0 {t0} token1 {t1}; {sym} decimals {dec}; WETH in pool {wbal / 1e18:,.1f}; ETH = ${usd:,.2f}")
for Q in (0.0012, 0.0058): print(f"  stake {Q} ETH = ${Q * usd:.2f}")
for d in (5, 15): print(f"  ${d} = {d / usd:.4f} ETH")
print(rpc.STATS)
