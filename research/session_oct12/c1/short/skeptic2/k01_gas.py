"""What a C-1 round trip really cost us: receipts of our 5 filled buys and their sells, and of the 3 reverted buys and their sells
(gasUsed x effectiveGasPrice, Arbitrum-style: gasUsed already carries the L1 part). Writes k01_gas.json."""
from sk import *
D = json.load(open(SH("s02_pools.json")))
txs = []
for p in D["pools"]:
    for s in p["sw"]:
        if s["cls"] == "ours": txs.append((p["pid"][:10], "buy" if s["buy"] else "sell", s["tx"]))
ours = json.load(open(J("c04_ours.json")))
for t in ours:
    if t.get("c1"): txs.append((t["c1"][:10], "revert " + ("buy" if t["input"].startswith("0x5ed06f60") else "sell"), t["hash"]))
CACHE = K("k01_receipts.json")
if os.path.exists(CACHE): rec = json.load(open(CACHE))
else: rec = rpc.batch("eth_getTransactionReceipt", [[h] for _, _, h in txs]); json.dump(rec, open(CACHE, "w"))
out = []
for (pid, kind, h), r in zip(txs, rec):
    g = int(r["gasUsed"], 16); gp = int(r["effectiveGasPrice"], 16); l1 = int(r.get("gasUsedForL1", "0x0"), 16)
    out.append({"pid": pid, "kind": kind, "tx": h, "gasUsed": g, "gasUsedForL1": l1, "effGasPrice": gp, "cost_wei": g * gp, "status": r["status"], "block": int(r["blockNumber"], 16)})
    print(f"{pid} {kind:12s} gas {g:7d} (L1 {l1:6d}) price {gp / 1e9:.4f} gwei cost {g * gp / 1e18:.3e} ETH = ${g * gp / 1e18 * 2500:.4f} at $2500 status {r['status']}")
fill = [o for o in out if o["kind"] in ("buy", "sell")]
rt = sum(o["cost_wei"] for o in fill if o["pid"] != "0xb47b706f") / 4                     # the 4 complete round trips
pulled_sell = next(o["cost_wei"] for o in out if o["pid"] == "0xb47b706f" and o["kind"] == "revert sell")
pulled = next(o["cost_wei"] for o in out if o["pid"] == "0xb47b706f" and o["kind"] == "buy") + pulled_sell
rv = sum(o["cost_wei"] for o in out if o["kind"].startswith("revert") and o["pid"] != "0xb47b706f") / 3
print(f"per filled round trip: {rt / 1e18:.3e} ETH = ${rt / 1e18 * 2500:.4f}; a fill whose sell met the pull (335k gas): {pulled / 1e18:.3e} ETH = ${pulled / 1e18 * 2500:.4f}; per reverted attempt (buy + its sell): {rv / 1e18:.3e} ETH = ${rv / 1e18 * 2500:.4f}")
json.dump({"tx": out, "per_fill_wei": rt, "per_pulled_wei": pulled, "per_revert_wei": rv}, open(K("k01_gas.json"), "w"), indent=1)
print("rpc", rpc.STATS)
