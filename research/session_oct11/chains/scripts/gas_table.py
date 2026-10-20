"""Gas per typical swap (assumed 150k gas; L2 L1-data fee excluded since receipts were not fetched):
sampled median effective gasPrice where available, else head-block baseFee from probe.json. USD only for ETH/BNB gas (on-chain prices)."""
import json, os
OUT = os.path.join(os.path.dirname(__file__), "..", "out")
probe = json.load(open(os.path.join(OUT, "probe.json")))
prices = json.load(open(os.path.join(OUT, "prices.json")))
summ = json.load(open(os.path.join(OUT, "summary.json")))
NATIVE = {"bnb": "BNB", "polygon": "POL", "avalanche": "AVAX", "sonic": "S", "berachain": "BERA", "monad": "MON",
          "hyperevm": "HYPE", "apechain": "APE", "xai": "XAI", "reya": "?"}
sampled = {}
for r in summ:
    if r["gas_gwei_median"] is not None:
        sampled.setdefault(r["chain"], []).append(r["gas_gwei_median"])
rows = {}
for ch, lst in probe.items():
    ok = [x for x in lst if "block_time_s" in x]
    if not ok: rows[ch] = {"status": "unreachable: " + lst[0].get("error", "")[:60]}; continue
    p = ok[0]
    nat = NATIVE.get(ch, "ETH")
    g = sorted(sampled[ch])[len(sampled[ch]) // 2] if ch in sampled else p["baseFeeGwei"]
    cost = g * 1e-9 * 150_000
    px = prices.get(f"{nat}_USD")
    rows[ch] = {"block_time_s": p["block_time_s"], "gas_gwei": g, "gas_src": "sampled swap txs" if ch in sampled else "head baseFee",
                "native_per_swap": cost, "native": nat, "usd_per_swap": round(cost * px, 5) if px else None}
json.dump(rows, open(os.path.join(OUT, "gas_blocktime.json"), "w"), indent=1)
for k, v in rows.items(): print(k, v)
