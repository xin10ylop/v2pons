"""Classify the cached Initialize rows of one chain against the 2.433 / 3.0 / 5.0 tells."""
import sys, json, collections
ch = sys.argv[1]; f = sys.argv[2] if len(sys.argv) > 2 else f"c11_{ch}_inits_cache.jsonl"
R = [json.loads(l) for l in open(f)]
S = {"2433": 1604517591721945638372359205383840, "3.0": 679394651928963067279918579724198, "5.0": 526364174002223567019744861584709}
z = "0x" + "0" * 40
print(ch, "Initialize rows", len(R), "blocks", min(r["b"] for r in R) if R else None, "..", max(r["b"] for r in R) if R else None)
for k, s in S.items():
    m = [r for r in R if r["sqrtP"] == s]
    near = [r for r in R if abs(r["sqrtP"] - s) / s < 0.03]
    print(f"  sqrtP {k}: exact {len(m)}, within 3% {len(near)}", [(r["b"], r["c0"][:8], r["c1"], r["fee"], r["ts_"], r["hooks"][:8]) for r in (m or near)[:6]])
nat = [r for r in R if r["c0"] == z and r["hooks"] == z]
print("  native-ETH no-hook launches:", len(nat))
print("  fee/ts 5000/100 native no-hook:", len([r for r in nat if (r["fee"], r["ts_"]) == (5000, 100)]), " 10000/200:", len([r for r in nat if (r["fee"], r["ts_"]) == (10000, 200)]), " 2500/50:", len([r for r in nat if (r["fee"], r["ts_"]) == (2500, 50)]))
e777 = [r for r in R if r["c1"].endswith("777") or r["c0"].endswith("777")]
print("  any currency ending 777:", len(e777), collections.Counter((r["fee"], r["ts_"], r["hooks"] == z, r["c0"] == z) for r in e777).most_common(6))
n777 = [r for r in nat if r["c1"].endswith("777")]
print("  native no-hook with token ending 777:", len(n777), [(r["b"], r["c1"], r["fee"], r["ts_"], r["sqrtP"]) for r in n777[:10]])
print("  top native no-hook fee/ts:", collections.Counter((r["fee"], r["ts_"]) for r in nat).most_common(8))
