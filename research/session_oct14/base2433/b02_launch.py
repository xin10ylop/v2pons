"""Base: what the 2.433 buyer wallets traded at 09:42-09:43 UTC Oct 14 (b01_2000.out): the token 0x3a73002f...a777, the contract
0x987d5db8 they bought through (27f7e6ee, 356 B), the two addresses 0x505b452d / 0x72d0cac5 they each paid at 09:36 / 09:39, and the
pool's launch (Uniswap v4 PoolManager Initialize on Base). Code hashes are compared with the Robinhood line's (router bd31d4da, token
63ad5291cdef). Public endpoint, read-only."""
import sys, json, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/skeptic"); import xr
from eth_utils import keccak
PM = "0x498581ff718922c3f8e6a244956af099b2652b2b"                     # Uniswap v4 PoolManager on Base
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
TOKEN = "0x3a73002fcad288a2ce1aff82fad49229b060a777"
ADDRS = {"router? 0x987d5db8": "0x987d5db84d105c1f49391af409cc34c6050fb1d0", "paid1 0x505b452d": "0x505b452dc968ff72aade79fcd87fd31552d212e3",
         "paid2 0x72d0cac5": "0x72d0cac5017dd7e2bcf3cfbde9079eae796c163c", "token a777": TOKEN, "0x8f79d153": "0x8f79d153630b327cc84487804f152972cce93cb4"}
for k, a in ADDRS.items():
    code, n, b = xr.batch("base", "eth_getCode", [[a, "latest"]], n=1)[0], int(xr.batch("base", "eth_getTransactionCount", [[a, "latest"]], n=1)[0], 16), int(xr.batch("base", "eth_getBalance", [[a, "latest"]], n=1)[0], 16) / 1e18
    print(f"{k} {a}: code {(len(code) - 2) // 2} B hash {keccak(bytes.fromhex(code[2:])).hex()[:12] if len(code) > 2 else '-'}  nonce {n}  {b:.4f} ETH")
head = int(xr.batch("base", "eth_blockNumber", [[]], n=1)[0], 16)
a, b = 52590500, 52590830
ini = []
for s in range(a, b + 1, 500):
    ini += xr.batch("base", "eth_getLogs", [[{"address": PM, "topics": [T_INIT], "fromBlock": hex(s), "toBlock": hex(min(s + 499, b))}]], n=1)[0] or []
mine = [l for l in ini if TOKEN[2:] in (l["topics"][2][-40:] + l["topics"][3][-40:])]
print(f"v4 Initialize logs on Base in {a}..{b}: {len(ini)}; with the token: {len(mine)}")
for l in mine:
    d = l["data"]; W = lambda i: int(d[2 + 64 * i: 66 + 64 * i], 16)
    pid = l["topics"][1]; tx = xr.batch("base", "eth_getTransactionByHash", [[l["transactionHash"]]], n=1)[0]
    blk = int(l["blockNumber"], 16)
    print(f"  launch block {blk} pool {pid[:18]} c0 {l['topics'][2][-40:][:10]} c1 {l['topics'][3][-40:][:10]} fee {W(0)} ts {W(1)} hook 0x{d[2+64*2+24:2+64*3][:8]} sqrtP {W(3)}")
    print(f"  launch tx {tx['hash']} from {tx['from']} to {tx['to']} sel {tx['input'][:10]} {(len(tx['input'])-2)//2} B value {int(tx['value'],16)/1e18:.7f}")
    sw = []
    for s in range(blk, min(blk + 400, head) + 1, 500):
        sw += xr.batch("base", "eth_getLogs", [[{"address": PM, "topics": [T_SWAP, pid], "fromBlock": hex(s), "toBlock": hex(min(s + 499, blk + 400, head))}]], n=1)[0] or []
    txs = xr.batch("base", "eth_getTransactionByHash", [[x["transactionHash"]] for x in sw], n=20) if sw else []
    from_sgn = lambda x: x - (1 << 128) if x >= (1 << 127) else x
    print(f"  swaps to +400: {len(sw)}")
    for x, t in zip(sw, txs):
        d = x["data"]; a0 = from_sgn(int(d[2:66], 16) & ((1 << 128) - 1)) if False else int(d[2:66], 16)
        a0 = a0 - (1 << 256) if a0 >= (1 << 255) else a0
        print(f"    +{int(x['blockNumber'],16)-blk} from {t['from'][:10]} to {(t.get('to') or '')[:10]} sel {t['input'][:10]} {(len(t['input'])-2)//2} B value {int(t['value'],16)/1e18:.4f}  ETH delta(amount0) {a0/1e18:+.4f}")
