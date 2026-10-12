"""Every transaction that names the token, in blocks launch .. launch + 100 of the 10 latest WETH-token0 launches (full blocks from the RPC,
only the matching transactions kept), with its receipt: who calls what, did it revert, and the launch block itself (anything after the launch
transaction in its own block). Reverted swaps leave no logs, so this is the only way to see failed buys or sells, ours-to-be included.
Writes s09_block_scan.jsonl (the matches) and s09_block_scan.out."""
from common import *
import rpc, collections
L = [x for x in json.load(open(J("s01_launches.json")))["launches"] if x["qs"] == 0][-10:]
N = 100; out = []
for x in L:
    tok = x["token"][2:]; blocks = []
    for a in range(x["lb"], x["lb"] + N + 1, 20):
        blocks += rpc.batch("eth_getBlockByNumber", [[hex(b), True] for b in range(a, min(a + 20, x["lb"] + N + 1))], n=20)
    m = []
    for b in blocks:
        for t in b["transactions"]:
            if tok in t["input"].lower() and t["hash"] != x["tx"]:
                m.append({"pool": x["pool"], "off": int(b["number"], 16) - x["lb"], "ti": int(t["transactionIndex"], 16), "hash": t["hash"], "from": t["from"].lower(),
                          "to": (t["to"] or "").lower(), "sel": t["input"][2:10], "n": (len(t["input"]) - 2) // 2, "value": int(t["value"], 16),
                          "buy_path": (WETH[2:] + "000064" + tok) in t["input"].lower(), "sell_path": (tok + "000064" + WETH[2:]) in t["input"].lower()})
    rec = rpc.batch("eth_getTransactionReceipt", [[t["hash"]] for t in m]) if m else []
    for t, r in zip(m, rec):
        t["status"] = int(r["status"], 16); t["gas_used"] = int(r["gasUsed"], 16); t["swap_logs"] = sum(1 for l in r["logs"] if l["topics"] and l["topics"][0] == T_SW)
    out += m
    same = [t for t in m if t["off"] == 0]
    print(f"{x['pool']} launch {utc(x['ts'])} (tx index {x['ti']}): {len(m)} txs name the token in + 0..+ {N}; reverted {sum(t['status'] == 0 for t in m)}; "
          f"in the launch block after it {len(same)} {[(t['to'][:10], t['sel'], t['status']) for t in same]}", flush=True)
with open(J("s09_block_scan.jsonl"), "w") as f:
    for t in out: f.write(json.dumps(t) + "\n")
rv = [t for t in out if t["status"] == 0]
print(f"\nall: {len(out)} txs; reverted {len(rv)}; by (to, selector, bytes, status): {collections.Counter((t['to'][:10], t['sel'], t['n'], t['status']) for t in out).most_common(12)}")
print(f"reverted: {[(t['pool'][:10], t['off'], t['to'][:10], t['sel'], t['n'], 'buy' if t['buy_path'] else 'sell' if t['sell_path'] else '?', t['gas_used']) for t in rv][:20]}")
print(f"sells (the token -> WETH path) {sum(t['sell_path'] for t in out)}, reverted {sum(t['sell_path'] and t['status'] == 0 for t in out)}; "
      f"first offsets of any tx naming the token: {sorted(collections.Counter(t['off'] for t in out if t['off'] <= 5).items())}")
print(rpc.STATS)
