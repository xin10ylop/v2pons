import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
K = json.load(open(os.path.join(HERE, "keys.json")))
P = load_pools(); F = load_families(); T = load_txs()
pids = [x for k in K for x in F[k]["pids"]]
E = load_events(set(pids))
for k in K:
    f = F[k]
    print("=" * 100); print(k)
    print({kk: f[kk] for kk in f if kk not in ("pids",)})
    for pid in f["pids"]:
        p = P[pid]; e = E.get(pid)
        print("--", pid, "bn", p["launch_block"], "ts", p["launch_ts"], "from", p["launch_from"], "nonce", p["launch_nonce"], "val", p["launch_value_eth"], "tick0", p["tick0"], "liq", p["liq_launch"], "token", p["token"])
        print("   created", p["created_contract"], "to_code", p["to_code_size"], "known", p["known"], "nsw", p["n_swaps"], "nb", p["n_buys"], "ns", p["n_sells"], "np", p["n_pulls"], "na", p["n_adds"])
        if not e: continue
        for a in e["adds"]: print("   add", a["bn"] - p["launch_block"], a["lo"], a["hi"], a["dl"], a["sender"][:10], a["tx"][:10])
        for s in e["swaps"][:15]:
            t = T.get(s["tx"])
            print("   sw", s["bn"] - p["launch_block"], s["ti"], "buy" if s["a0"] < 0 else "sell", abs(s["a0"]) / 1e18, s["fee"], s["sender"][:10], (t["from"], t["to"], t["selector"], t["calldata_len"], t["nonce"]) if t else None)
        for s in e["pulls"][:3]: print("   pull", s["bn"] - p["launch_block"], s["dl"], s["sender"][:10])
