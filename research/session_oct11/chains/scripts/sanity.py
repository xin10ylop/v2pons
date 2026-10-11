"""Sanity check that eth_getLogs returns data: count ERC20 Transfer logs (no address) and DEX Swap logs over the last N blocks."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import rpc
TR = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
SW = ["0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f", "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67",
      "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"]
out = {}
for name, url, n in [(a.split("=")[0], a.split("=")[1], int(a.split("=")[2])) for a in sys.argv[1:]]:
    try:
        h = rpc.block_number(url) - 3
        tr, _ = rpc.get_logs_range(url, None, [TR], h - n, h, chunk=n, max_chunk=n)
        sw, _ = rpc.get_logs_range(url, None, [SW], h - n, h, chunk=n, max_chunk=n)
        import collections
        out[name] = {"blocks": n, "transfers": len(tr), "swaps": len(sw), "swap_emitters_top": collections.Counter(l["address"] for l in sw).most_common(3)}
    except Exception as e:
        out[name] = {"error": str(e)[:200]}
    print(name, json.dumps(out[name]), flush=True)
json.dump(out, open(os.path.join(os.path.dirname(__file__), "..", "out", "sanity_logs.json"), "w"), indent=1)
