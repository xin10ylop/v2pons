"""Gas and price inputs, from the chain: (1) baseFeePerGas over the window (40 block headers, evenly spaced); (2) receipts of 12 crowd buys
(gasUsed, gasUsedForL1, effectiveGasPrice) to see what a 0.01% V3 swap transaction costs here; (3) the ETH price in USD from the busiest
WETH/stablecoin V3 pool of the factory (PoolCreated over the factory's life, the counterpart's symbol()/decimals(), then slot0()).
Writes r05_gas_price.json."""
from common import *
import rpc, collections
M = json.load(open(J("r01_meta.json"))); head = int(rpc.call("eth_blockNumber", []), 16)
bl = [M["start"] + (head - M["start"]) * i // 39 for i in range(40)]
hdr = rpc.batch("eth_getBlockByNumber", [[hex(b), False] for b in bl])
bf = [(b, int(h["timestamp"], 16), int(h["baseFeePerGas"], 16)) for b, h in zip(bl, hdr)]
print("base fee (gwei) over the window:", [round(x[2] / 1e9, 4) for x in bf])
TX = jl(J("r03_txs_cache.jsonl")); crowd = [t for t in TX if (t["sel"], t["n"]) in CROWD_SHAPES and t["value"] == 0][-12:]
rcs = rpc.batch("eth_getTransactionReceipt", [[t["hash"]] for t in crowd], n=12)
rr = [{"hash": t["hash"], "gasUsed": int(r["gasUsed"], 16), "l1": int(r.get("gasUsedForL1", "0x0"), 16), "egp": int(r["effectiveGasPrice"], 16), "status": r["status"]} for t, r in zip(crowd, rcs)]
for r in rr: print("crowd buy receipt", r)
# ETH/USD
pc = []
for a in range(0, head + 1, 4000000):
    pc += rpc.logs({"address": FACT, "topics": [T_PC]}, a, min(a + 3999999, head))
other = collections.Counter()
pools = collections.defaultdict(list)
for l in pc:
    t0, t1 = "0x" + l["topics"][1][-40:], "0x" + l["topics"][2][-40:]; fee = int(l["topics"][3], 16)
    if WETH in (t0, t1):
        o = t1 if t0 == WETH else t0; other[o] += 1; pools[o].append((fee, "0x" + l["data"][-40:], t0 == WETH))
print(f"factory PoolCreated (life): {len(pc)}; counterparts of WETH in >= 2 pools: {sum(1 for o, n in other.items() if n >= 2)}")
def sym(a):
    try:
        r = rpc.call("eth_call", [{"to": a, "data": "0x95d89b41"}, "latest"]); b = bytes.fromhex(r[2:])
        if len(b) >= 96: n = int.from_bytes(b[32:64], "big"); return b[64:64 + n].decode(errors="replace")
        return b.rstrip(b"\0").decode(errors="replace")
    except Exception as e: return "?"
cands = []
for o, n in other.most_common(40):
    if n < 2 and len(cands) > 5: break
    s = sym(o)
    if any(k in s.upper() for k in ("USD", "DAI")):
        dec = int(rpc.call("eth_call", [{"to": o, "data": "0x313ce567"}, "latest"]), 16)
        for fee, pool, weth0 in pools[o]:
            s0 = rpc.call("eth_call", [{"to": pool, "data": "0x3850c7bd"}, "latest"]); sp = int(s0[2:66], 16)
            liq = int(rpc.call("eth_call", [{"to": pool, "data": "0x1a686502"}, "latest"]), 16)
            bal = int(rpc.call("eth_call", [{"to": WETH, "data": "0x70a08231" + pool[2:].zfill(64)}, "latest"]), 16)
            p = (sp / 2 ** 96) ** 2                       # token1 per token0 (raw)
            usd = p * 10 ** (18 - dec) if weth0 else (1 / p) * 10 ** (18 - dec) if p else 0
            cands.append({"token": o, "sym": s, "dec": dec, "fee": fee, "pool": pool, "eth_usd": usd, "liq": liq, "weth_in_pool": bal / 1e18})
            print("  ", s, o, "fee", fee, "pool", pool, f"ETH = ${usd:,.2f}", "WETH in pool", round(bal / 1e18, 3))
json.dump({"base_fee": bf, "receipts": rr, "eth_usd_pools": cands}, open(J("r05_gas_price.json"), "w"))
print("rpc", rpc.STATS)
