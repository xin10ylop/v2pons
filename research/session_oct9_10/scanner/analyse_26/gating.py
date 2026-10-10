import sys, os, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
C = json.load(open("cache/fetch2.json")); P = load_pools()
PMA = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
F4 = [p["pid"] for p in P.values() if p["launch_to"] == PMA and p["selector"] == "6276cbbe" and p["calldata_len"] == 196]
F4a = [x for x in F4 if P[x]["fee"] == 500 and P[x]["tick_spacing"] == 1 and P[x]["hooks_zero"]]
F4b = [x for x in F4 if P[x]["fee"] == 500 and P[x]["tick_spacing"] == 1 and not P[x]["hooks_zero"]]
E = load_events(set(F4b[:3] + F4a[:1]))
for pid in F4b[:3] + F4a[:1]:
    lb = E[pid]["adds"][0]["bn"]; tok = P[pid]["token"][2:]
    print("==", pid[:12], "hooked" if pid in F4b else "F4a", "live", lb, "first swap", E[pid]["swaps"][0]["bn"] - lb if E[pid]["swaps"] else None)
    for b in range(lb, lb + 77):
        for t in C["blocks"].get(str(b), []):
            if tok in t["input"].lower() or pid[2:] in t["input"].lower():
                r = C["rcpt"].get(t["hash"], {})
                print("   +%d ti %d from %s to %s sel %s len %d value %.6f status %s gas %s logs %s" % (b - lb, t["ti"], t["from"][:10], t["to"][:10], t["input"][2:10], (len(t["input"]) - 2) // 2, t["value"] / 1e18, r.get("status"), r.get("gasUsed"), r.get("nlogs")))
