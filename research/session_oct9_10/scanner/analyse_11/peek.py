import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); P = load_pools(); T = load_txs()
keys = json.load(open("keys.json"))
pids = set(p for k in keys for p in F[k]["pids"])
E = load_events(pids)
for k in keys:
    f = F[k]
    print("=" * 100); print(k)
    print({kk: f[kk] for kk in f if kk not in ("pids",)})
    for pid in f["pids"]:
        p = P[pid]; e = E.get(pid)
        print("--", pid[:12], "b0", p["launch_block"], p["launch_ts"], "from", p["launch_from"][:10], "nonce", p["launch_nonce"], "val", p["launch_value_eth"], "hooks", p["hooks"][:10], "token", p["token"][:10], "tick0", p["tick0"], "liq", p["liq_launch"])
        if not e: print("   no events"); continue
        b0 = p["launch_block"]
        for a in e["adds"][:3]: print("   add", a["bn"]-b0, a["lo"], a["hi"], a["dl"], a["tx"][:10], a["sender"][:10])
        for s in e["swaps"][:14]:
            t = T.get(s["tx"])
            print("   swap", s["bn"]-b0, s["ti"], "buy" if s["a0"] < 0 else "sell", abs(s["a0"])/1e18, "fee", s["fee"], "to", t["to"][:10] if t and t["to"] else None, "from", t["from"][:10] if t else None, "sel", t["selector"] if t else None, "clen", t["calldata_len"] if t else None, "nonce", t["nonce"] if t else None)
        print("   nswaps", len(e["swaps"]))
        for pl in e["pulls"][:2]:
            t = T.get(pl["tx"])
            print("   pull", pl["bn"]-b0, pl["dl"], "to", t["to"][:10] if t else None, "from", t["from"][:10] if t else None, "sel", t["selector"] if t else None)
