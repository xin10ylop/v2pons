"""Probe: the head, the ETH price (the deepest V3 WETH/USDG pool), and whether the public node answers eth_getCode / eth_call / eth_getStorageAt
at old blocks (an archive node lets a sell be simulated at the block it would have gone in)."""
from common import *
import rpc
head = int(rpc.call("eth_blockNumber", []), 16); hb = rpc.call("eth_getBlockByNumber", [hex(head), False])
print(f"head {head} {utc(int(hb['timestamp'], 16))} base fee {int(hb['baseFeePerGas'], 16) / 1e9:.4f} gwei")
t0, t1 = sorted([WETH, USDG])
best = None
for fee in (100, 500, 3000):
    r = rpc.call("eth_call", [{"to": FACT, "data": "0x1698ee82" + t0[2:].zfill(64) + t1[2:].zfill(64) + "%064x" % fee}, "latest"])
    pool = "0x" + r[-40:]
    if int(pool, 16) == 0: continue
    sp = int(rpc.call("eth_call", [{"to": pool, "data": "0x3850c7bd"}, "latest"])[2:66], 16); liq = int(rpc.call("eth_call", [{"to": pool, "data": "0x1a686502"}, "latest"]), 16)
    p = (sp / 2 ** 96) ** 2; usd = p * 1e18 / 1e6 if t0 == WETH else 1 / p * 1e18 / 1e6
    print(f"WETH/USDG fee {fee}: {pool} L {liq:.3e} ETH = ${usd:,.2f}")
    if best is None or liq > best[0]: best = (liq, usd)
print(f"ETH price used: ${best[1]:,.2f}")
tok = "0x4d3f136f4e5351abdc6892b0678cd278c3d77f24"   # the first launch of Oct 10 12:00 (replay r01): its token
for back in (1000, 100000, 900000, 1700000):
    b = head - back
    try:
        c = rpc.call("eth_getCode", [tok, hex(b)]); r = rpc.call("eth_call", [{"to": tok, "data": "0x18160ddd"}, hex(b)])
        print(f"  {back:>8} blocks back ({back / 9.7 / 3600:.1f} h): code {len(c) // 2 - 1} bytes, totalSupply call -> {r[:20]}...")
    except Exception as e:
        print(f"  {back:>8} blocks back: {str(e)[:160]}")
json.dump({"head": head, "eth_usd": best[1], "base_fee_wei": int(hb["baseFeePerGas"], 16)}, open(J("s00_probe.json"), "w"))
print(rpc.STATS)
