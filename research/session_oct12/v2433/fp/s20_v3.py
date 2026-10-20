"""Off-v4 check: every Uniswap V3 PoolCreated (factory 0x1f7d7550, the engine's V3_FACTORY) in the window, with its transaction (sender, to,
value, calldata length): did a 2.4333-like launcher move to V3? Cached in s20_v3_cache.jsonl."""
import json, collections, time, bisect
from common import R, keccak, p, load_jsonl, append_jsonl, V2433
F = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"
T_PC = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex()
meta = json.load(open(p("s01_meta.json")))
if not load_jsonl("s20_v3_cache.jsonl"):
    ls = []
    for a in range(meta["start"], meta["head"] + 1, 50000):
        ls += R.logs({"address": F, "topics": [T_PC]}, a, min(a + 49999, meta["head"]))
    txs = R.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in ls])
    append_jsonl("s20_v3_cache.jsonl", [{"b": int(l["blockNumber"], 16), "h": l["transactionHash"], "t0": "0x" + l["topics"][1][-40:], "t1": "0x" + l["topics"][2][-40:], "fee": int(l["topics"][3], 16),
                                         "from": t["from"].lower(), "to": (t.get("to") or "").lower(), "value": str(int(t["value"], 16)), "clen": (len(t["input"]) - 2) // 2, "sel": t["input"][:10]} for l, t in zip(ls, txs)])
v = load_jsonl("s20_v3_cache.jsonl")
bl = sorted((x["b"], x["t"]) for x in load_jsonl("s01_blocks_cache.jsonl")); bb = [b for b, _ in bl]
def t_of(b):
    i = bisect.bisect_left(bb, b); i = min(max(i, 1), len(bb) - 1); (b0, t0), (b1, t1) = bl[i - 1], bl[i]; return t0 + (t1 - t0) * (b - b0) / (b1 - b0)
print("V3 PoolCreated in the window:", len(v), "| value == 2.4333285:", sum(int(x["value"]) == V2433 for x in v), "| value within 10%:", sum(abs(int(x["value"]) / V2433 - 1) <= .1 for x in v))
g = collections.defaultdict(list)
for x in v: g[(x["to"][:10], x["sel"], x["clen"], x["fee"])].append(x)
hours = list(range(int(bl[0][1] // 3600), int(bl[-1][1] // 3600) + 1))
print("%-48s %4s %5s %-23s | %s" % ("(to, selector, calldata B, fee)", "n", "sndr", "first..last", " ".join(time.strftime("%H", time.gmtime(h * 3600)).rjust(3) for h in hours)))
for k, xs in sorted(g.items(), key=lambda kv: -len(kv[1]))[:15]:
    c = collections.Counter(int(t_of(x["b"]) // 3600) for x in xs); vals = collections.Counter(round(int(x["value"]) / 1e18, 4) for x in xs).most_common(2)
    print("%-48s %4d %5d %s..%s | %s  values %s" % (str(k)[:48], len(xs), len({x["from"] for x in xs}), time.strftime("%d %H:%M", time.gmtime(t_of(xs[0]["b"]))), time.strftime("%d %H:%M", time.gmtime(t_of(xs[-1]["b"]))),
                                                   " ".join(str(c[h]).rjust(3) for h in hours), vals))
