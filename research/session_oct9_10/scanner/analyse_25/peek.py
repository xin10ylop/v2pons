import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
K = json.load(open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_25/keys.json"))
P = load_pools(); F = load_families(); T = load_txs()
pids = set(x for k in K for x in F[k]["pids"])
E = load_events(pids)
for k in K:
    print("=" * 100); print(k); fr = F[k]; print({a: b for a, b in fr.items() if a != "pids"})
    for pid in fr["pids"]:
        p = P[pid]; e = E.get(pid) or {}
        print(" pid", pid[:12], "bn", p["launch_block"], "ts", p["launch_ts"], "from", p["launch_from"][:10], "nonce", p["launch_nonce"], "val", p["launch_value_eth"], "tok", p["token"][:10],
              "tick0", p["tick0"], "liq", p["liq_launch"], "buyInLaunch", p["buy_in_launch_tx"], "nsw", p["n_swaps"], "nb", p["n_buys"], "np", p["n_pulls"], "na", p["n_adds"], "fb", p["first_buy_rel"], p["first_buy_eth"], "fp", p["first_pull_rel"])
        for a in e.get("adds", [])[:3]: print("    add", a["bn"] - p["launch_block"], a["lo"], a["hi"], a["dl"], a["tx"][:10], a["sender"][:10])
        for s in e.get("swaps", [])[:10]:
            t = T.get(s["tx"]) or {}
            print("    sw", s["bn"] - p["launch_block"], s["ti"], "a0", s["a0"] / 1e18, "a1", s["a1"], "fee", s["fee"], "to", (t.get("to") or "?")[:10], t.get("selector"), t.get("calldata_len"), "from", (t.get("from") or "?")[:10], "nonce", t.get("nonce"))
        for s in e.get("pulls", [])[:3]: print("    pull", s["bn"] - p["launch_block"], s["dl"], s["tx"][:10], s["sender"][:10])
