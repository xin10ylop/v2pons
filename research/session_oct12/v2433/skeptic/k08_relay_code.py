"""Our relay's v4 swaps near/after the stop; bot router code now vs before; 2.433 pool for the last launch."""
import kc, json, hashlib
from eth_utils import keccak
rows = [json.loads(l) for l in open(kc.p("k01_launches_cache.jsonl"))]
head = max(r["block"] for r in rows)
pid2 = {r["id"]: r for r in rows}
lg = kc.cached_logs("k08_relay_swaps_cache.jsonl", {"address": kc.PM, "topics": [kc.T_SWAP, None, "0x" + "0" * 24 + kc.RELAY[2:]]}, 86250000, head, step=50000)
print("relay swaps since block 86250000:", len(lg))
bt = kc.block_ts_map("k08_bt_cache.jsonl", [int(l["blockNumber"], 16) for l in lg])
for l in lg[-8:]:
    b = int(l["blockNumber"], 16); r = pid2.get(l["topics"][1]); d = l["data"]
    a0, a1 = kc.sgn(kc.W(d, 0), 256), kc.sgn(kc.W(d, 1), 256)
    print("  ", b, kc.ts(bt[b]), "launch+%s" % ((b - r["block"]) if r else "?"), "fam=%s" % ((r["value"] or 0) / 1e18 if r else "?"), "amount0(ETH) %.6f" % (a0 / 1e18), l["transactionHash"][:14])
for blk in ("latest", hex(86300000)):
    try:
        c = kc.R.call("eth_getCode", [kc.BOT, blk]); print("BOT code at", blk, (len(c) - 2) // 2, "bytes keccak", keccak(hexstr=c).hex()[:16])
    except Exception as e: print("BOT code at", blk, "error", str(e)[:120])
