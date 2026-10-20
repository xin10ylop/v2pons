import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
K = json.load(open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_16/keys.json"))
F = load_families(); P = load_pools()
pids = set()
for k in K:
    f = F[k]; pids |= set(f["pids"])
E = load_events(pids); T = load_txs()
for k in K:
    f = F[k]
    print("=" * 100); print(k)
    print({x: f[x] for x in f if x not in ("pids",)})
    for pid in f["pids"]:
        p = P[pid]; e = E.get(pid)
        print("--", pid[:12], "lb", p["launch_block"], "ts", p["launch_ts"], "from", p["launch_from"][:10], "nonce", p["launch_nonce"], "val", p["launch_value_eth"], "tok", p["token"][:10], "sp0", p["sqrt_p0"], "tick0", p["tick0"], "liq", p["liq_launch"], "ti", p["tx_index"])
        if not e: print("   no events"); continue
        for s in e["swaps"][:12]:
            t = T.get(s["tx"])
            print("   swap +%d ti%d a0 %.6f a1 %d sender %s to %s from %s sel %s" % (s["bn"] - p["launch_block"], s["ti"], -s["a0"] / 1e18, s["a1"], s["sender"][:10], (t or {}).get("to", "?") and (t or {}).get("to", "?")[:10], (t or {}).get("from", "?")[:10], (t or {}).get("selector")))
        print("   nswaps", len(e["swaps"]))
        for a in e["adds"][:4]: print("   add +%d lo %d hi %d dl %d sender %s" % (a["bn"] - p["launch_block"], a["lo"], a["hi"], a["dl"], a["sender"][:10]))
        for a in e["pulls"][:4]: print("   pull +%d lo %d hi %d dl %d sender %s" % (a["bn"] - p["launch_block"], a["lo"], a["hi"], a["dl"], a["sender"][:10]))
        print("   pull_to", p["first_pull_to"], p["first_pull_selector"], p["first_pull_from"])
