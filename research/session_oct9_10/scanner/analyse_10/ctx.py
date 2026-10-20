import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); F = load_families()
KEYS = json.load(open("keys.json"))
for k in KEYS:
    deps = set(P[p]["launch_from"] for p in F[k]["pids"])
    print("====", k[:60])
    for d in deps:
        rows = [p for p in P.values() if p["launch_from"] == d]
        c = collections.Counter((p["family"][:80]) for p in rows)
        print("  deployer", d, "pools", len(rows), "families", len(c), c.most_common(6))
        if len(rows) > 9:
            print("    n_swaps>0:", sum(1 for p in rows if p["n_swaps"]), "n_pulls>0:", sum(1 for p in rows if p["n_pulls"]), "real buys(eth_in>0.001):", sum(1 for p in rows if (p["eth_in_buys"] or 0) > 0.001),
                  "first_block", min(p["launch_block"] for p in rows), "last", max(p["launch_block"] for p in rows))
# the 7fde822e loose family
L = load_loose_families()
for kk, v in L.items():
    if kk.startswith("7fde822e"):
        print("loose", kk, {a: b for a, b in v.items() if a not in ("pids",)} if isinstance(v, dict) else v)
        break
rows = [p for p in P.values() if p["selector"] == "7fde822e"]
print("7fde822e pools", len(rows), "deployers", collections.Counter(p["launch_from"] for p in rows).most_common(),
      "contracts", len(set(p["launch_to"] for p in rows)), "with real buys", sum(1 for p in rows if (p["eth_in_buys"] or 0) > 0.0002), "pulled", sum(1 for p in rows if p["n_pulls"]))
c = collections.Counter((p["launch_from"], p["tick0"], p["liq_launch"]) for p in rows); print(c.most_common(8))
# graduation launches: pools whose launch tx touched the bonding factory? Use hooks e5e70264
rows = [p for p in P.values() if p["hooks"] == "0xe5e702641ea86f4ae6cc3cdaed2b886f976be044"]
print("hook e5e70264 pools", len(rows), collections.Counter((p["launch_to"], p["selector"], p["launch_from"]) for p in rows).most_common(12))
print("  pulled", sum(1 for p in rows if p["n_pulls"]), "median swaps", sorted(p["n_swaps"] for p in rows)[len(rows)//2])
