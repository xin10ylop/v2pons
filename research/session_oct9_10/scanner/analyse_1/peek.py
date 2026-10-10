import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); F = load_families()
key = sys.argv[1]; nshow = int(sys.argv[2]) if len(sys.argv) > 2 else 3
pids = F[key]["pids"]
E = load_events(set(pids)); T = load_txs()
for pid in pids[:nshow]:
    p = P[pid]; e = E[pid]
    print("=== pid", pid, "launch", p["launch_block"], "from", p["launch_from"], "nonce", p["launch_nonce"], "token", p["token"], "sqrt", p["sqrt_p0"], "tick", p["tick0"], "liq", p["liq_launch"], "hooks", p["hooks"])
    lt = T[p["launch_tx"]]; print("  launch input512", lt["input512"][:300])
    print("  adds", [(a["bn"]-p["launch_block"], a["lo"], a["hi"], a["dl"], a["sender"][:10]) for a in e["adds"]][:5])
    print("  pulls", [(a["bn"]-p["launch_block"], a["lo"], a["hi"], a["dl"], a["sender"][:10], a["tx"][:10]) for a in e["pulls"]][:5])
    for s in e["swaps"][:14]:
        t = T.get(s["tx"])
        print("  swap +%d ti%d a0=%.6g a1=%d fee=%d sender=%s to=%s from=%s sel=%s len=%s" % (s["bn"]-p["launch_block"], s["ti"], s["a0"]/1e18, s["a1"], s["fee"], s["sender"][:10], t and (t["to"] or "")[:10], t and t["from"][:10], t and t["selector"], t and t["calldata_len"]))
    print("  nswaps", len(e["swaps"]), "zero_mods", len(e["zero_mods"]))
