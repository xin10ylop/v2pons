import json, collections, os
HERE = os.path.dirname(os.path.abspath(__file__))
L = [json.loads(l) for l in open(os.path.join(HERE, "out/probe.jsonl"))]
lag = [x["lag"] for x in L if x["m"] == "lag" and "lag" in x and x["feed_seq_at_send"] > 0]
print("lag samples", len(lag), sorted(collections.Counter(lag).items()))
print("lag errors", sum(1 for x in L if x["m"] == "lag" and "err" in x), [x["err"][:80] for x in L if x["m"] == "lag" and "err" in x][:5])
for x in L:
    if x["m"] != "lag":
        print(x)
for l in open(os.path.join(HERE, "out/engine.jsonl")):
    e = json.loads(l)
    if e["ev"] in ("launch", "armed", "launch_no_receipt", "launch_no_pool", "would_fire", "skip", "would_sell", "alarm", "feed_error", "feed_stall"):
        print({k: e[k] for k in e if k in ("ev", "seq", "to", "arm_ms", "eligible", "launcher_code", "why", "offset", "what", "err", "fee", "liq")})
