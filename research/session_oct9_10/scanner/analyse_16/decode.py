import sys, json, re
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
K = json.load(open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_16/keys.json"))
F = load_families(); P = load_pools(); T = load_txs()
for k in K:
    print("=" * 80); print(k)
    for pid in F[k]["pids"][:7]:
        p = P[pid]; t = T[p["launch_tx"]]
        inp = t.get("input") or t["input512"]
        b = bytes.fromhex(inp[10:])
        strs = re.findall(rb"[\x20-\x7e]{4,}", b)
        words = [inp[10 + 64 * i: 10 + 64 * (i + 1)] for i in range(min(12, (len(inp) - 10) // 64))]
        print(pid[:12], "from", t["from"][:10], "val", t["value_eth"], "gas", t["gas"], "prio", t.get("max_prio"), "type", t["type"], [s.decode() for s in strs][:8])
        print("   ", [w.lstrip("0")[:20] or "0" for w in words])
