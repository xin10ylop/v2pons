"""The fee-100 WETH pools created since the last 836-byte launch (13:44 UTC Oct 12) that the watch saw as not the v3crowd shape: who sends them,
the call (to, selector, bytes, value), the inner calls of a PositionManager multicall, the minted range, the token's code (template?) and the
launch wallet's nonce: has the line changed its launch call (as p356's calldata grew on Oct 11)? Writes s16_new_shapes.out (stdout)."""
from common import *
import rpc, collections
from eth_abi import decode
m = json.load(open(J("s01_launches.json"))); h0 = m["head"]
T2 = {r["codehash"]: r["size"] for r in json.load(open(J("s02_codes.json")))}
head = int(rpc.call("eth_blockNumber", []), 16)
pc = rpc.logs({"address": FACT, "topics": [T_PC]}, h0 - 20000, head)
cand = [l for l in pc if int(l["topics"][3], 16) == 100 and WETH[2:] in (l["topics"][1][-40:] + l["topics"][2][-40:])]
print(f"fee-100 WETH pools in blocks {h0 - 20000}..{head}: {len(cand)}")
for l in cand:
    t = rpc.call("eth_getTransactionByHash", [l["transactionHash"]]); r = rpc.call("eth_getTransactionReceipt", [l["transactionHash"]])
    inp = bytes.fromhex(t["input"][2:]); n = len(inp); bn = int(l["blockNumber"], 16)
    t0, t1 = "0x" + l["topics"][1][-40:], "0x" + l["topics"][2][-40:]; tok = t1 if t0 == WETH else t0
    code = rpc.call("eth_getCode", [tok, "latest"]); ch = "0x" + keccak(bytes.fromhex(code[2:])).hex()
    inner = []
    if inp[:4].hex() == "ac9650d8":
        try:
            for c in decode(["bytes[]"], inp[4:])[0]: inner.append(f"{c[:4].hex()}/{len(c)}")
        except Exception: inner = ["?"]
    mints = [(sgn(int(x["topics"][2], 16)), sgn(int(x["topics"][3], 16))) for x in r["logs"] if x["topics"][0] == T_MI]
    print(f"block {bn} {utc(int(rpc.call('eth_getBlockByNumber', [hex(bn), False])['timestamp'], 16))} from {t['from'][:12]} nonce {int(t['nonce'], 16)} to {t['to'][:12]} "
          f"{inp[:4].hex()}/{n} B value {int(t['value'], 16) / 1e18:g}; inner {inner}; WETH {'token0' if t0 == WETH else 'token1'}; mint ranges {mints}; "
          f"token code {len(code) // 2 - 1} B {ch[:14]} ({'known template ' + str(T2[ch]) if ch in T2 else 'not one of the line templates'})")
print(rpc.STATS)
