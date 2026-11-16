#!/usr/bin/env python3
"""hooktrace.py HOOK TOKEN: run the 1,380 B keep-tier hook's afterSwap on its real storage (minievm, read-only calls forwarded to the chain)
as the PoolManager would call it, for a small buy, with different swap senders: our FlipRelay (any non-router contract), the Universal Router,
and the other routers seen buying. Prints pass/revert and the storage reads and calls on each path. Read-only."""
import sys, json
import hlib as H
from minievm import EVM
HOOK = sys.argv[1].lower(); TOKEN = sys.argv[2].lower()
PM = H.CH["rh"]["pm"]
w = lambda x: format(x % (1 << 256), "064x"); ad = lambda a: "0" * 24 + a[2:].lower()
SENDERS = {"our relay (any contract)": "0x" + "f1" * 20, "Universal Router": "0x8876789976decbfcbbbe364623c63652db8c0904",
           "decoy router 0x65050a9b": "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc", "0x92475293 (bought 4x)": None}
e = EVM("rh", HOOK)
head = int(H.rpc(H.CH["rh"]["rpc"], "eth_blockNumber", []), 16); ts = int(H.rpc(H.CH["rh"]["rpc"], "eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
amt = 10 ** 15; tok_out = 10 ** 20
delta = ((-amt) % (1 << 128)) << 128 | (tok_out % (1 << 128))               # BalanceDelta: amount0 (ETH, paid) high, amount1 (tokens, received) low
def calldata(sender, zero_for_one=True):
    key = ad("0x" + "0" * 40) + ad(TOKEN) + w(1) + w(1) + ad(HOOK)
    params = w(1 if zero_for_one else 0) + w(-amt if zero_for_one else -tok_out) + w(4295128740 if zero_for_one else 1461446703485210103287273052203988822378723970341)
    return "0xb47b2fb1" + ad(sender) + key + params + w(delta) + w(11 * 32) + w(0)
for name, s in SENDERS.items():
    if not s:
        continue
    for side, z in (("buy", True), ("sell", False)):
        r = e.run(calldata(s, z), sender=PM, timestamp=ts, number=head)
        res = "REVERT " + r["revert"].hex()[:72] if r["revert"] is not None else "ok " + (r["result"] or b"").hex()[:8]
        print(f"{name:28s} {side}: {res}")
        print(f"     sloads {[(x[1][:40], hex(x[2])[:20]) for x in r['sloads']][:8]}")
        if r["calls"]:
            print(f"     calls {[(c[1][:12], c[2], c[3], c[4][:24]) for c in r['calls']][:6]}")
