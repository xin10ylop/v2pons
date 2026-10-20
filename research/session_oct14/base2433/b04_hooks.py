"""Base: the three fee-5000/ts-100 launches of Oct 14 (b03_24h.out): each launch's token, launcher contract (code, creator nonce), hook
address and its v4 permission bits (the address's low 14 bits), and who deployed what. Public endpoints (Tenderly's for old logs)."""
import sys, json
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/skeptic"); import xr
xr.EP["base_t"] = "https://base.gateway.tenderly.co"; xr.PACE["base_t"] = 0.3
from eth_utils import keccak
PM = "0x498581ff718922c3f8e6a244956af099b2652b2b"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
FLAGS = ["afterRemoveLiquidityReturnDelta", "afterAddLiquidityReturnDelta", "afterSwapReturnDelta", "beforeSwapReturnDelta", "afterDonate", "beforeDonate",
         "afterSwap", "beforeSwap", "afterRemoveLiquidity", "beforeRemoveLiquidity", "afterAddLiquidity", "beforeAddLiquidity", "afterInitialize", "beforeInitialize"]
for blk in (52590492, 52590807):
    pass
ls = []
head = int(xr.batch("base", "eth_blockNumber", [[]], n=1)[0], 16)
for s in range(head - 43200, head + 1, 500):
    ls += [l for l in (xr.batch("base_t", "eth_getLogs", [[{"address": PM, "topics": [T_INIT], "fromBlock": hex(s), "toBlock": hex(min(s + 499, head))}]], n=1)[0] or [])
           if int(l["data"][2:66], 16) == 5000 and int(l["data"][66:130], 16) == 100]
for l in ls:
    d = l["data"]; hook = "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3]; c0, c1 = "0x" + l["topics"][2][-40:], "0x" + l["topics"][3][-40:]
    tok = c1 if c0 == "0x" + "0" * 40 else c0
    t = xr.batch("base_t", "eth_getTransactionByHash", [[l["transactionHash"]]], n=1)[0]
    bits = int(hook, 16) & 0x3FFF
    on = [f for i, f in enumerate(reversed(FLAGS)) if bits >> i & 1]
    codes = {k: xr.batch("base", "eth_getCode", [[a, "latest"]], n=1)[0] for k, a in (("token", tok), ("hook", hook), ("launcher", t["to"]))}
    nonce = int(xr.batch("base", "eth_getTransactionCount", [[t["from"], "latest"]], n=1)[0], 16)
    print(f"block {int(l['blockNumber'],16)} tx {t['hash'][:14]} from {t['from']} (nonce now {nonce}) to {t['to']}")
    print(f"  token {tok}  code {(len(codes['token'])-2)//2} B {keccak(bytes.fromhex(codes['token'][2:])).hex()[:12] if len(codes['token'])>2 else '-'}")
    print(f"  hook {hook}  code {(len(codes['hook'])-2)//2} B {keccak(bytes.fromhex(codes['hook'][2:])).hex()[:12] if len(codes['hook'])>2 else '-'}  permissions {on}")
    print(f"  launcher code {(len(codes['launcher'])-2)//2} B {keccak(bytes.fromhex(codes['launcher'][2:])).hex()[:12] if len(codes['launcher'])>2 else '-'}  calldata {t['input'][:10]} {(len(t['input'])-2)//2} B")
    print("  calldata words:", [t["input"][10 + 64 * i: 74 + 64 * i].lstrip("0")[:40] or "0" for i in range(8)])
