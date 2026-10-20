import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); P = load_pools()
KEYS = json.load(open("keys.json"))
allp = set()
for k in KEYS: allp |= set(F[k]["pids"])
E = load_events(allp); T = load_txs()
for k in KEYS:
    print("=====", k)
    for pid in F[k]["pids"]:
        p = P[pid]; e = E.get(pid)
        b0 = p["launch_block"]
        print(f"{pid[:10]} b{b0} ts{p['launch_ts']} from {p['launch_from'][:10]} n{p['launch_nonce']} v{p['launch_value_eth']} sw{p['n_swaps']} b{p['n_buys']} s{p['n_sells']} pl{p['n_pulls']} ad{p['n_adds']} fb{p['first_buy_rel']} {p['first_buy_eth']} fp{p['first_pull_rel']} liq{p['liq_launch']} bilt{p['buy_in_launch_tx']} tick0 {p['tick0']} token {p['token'][:10]}")
        if e:
            for a in e["adds"][:3]: print("   add", a["bn"]-b0, a["lo"], a["hi"], a["dl"], a["tx"][:10], a["sender"][:10])
            for s in e["swaps"][:6]:
                t = T.get(s["tx"])
                print("   sw", s["bn"]-b0, s["ti"], s["a0"]/1e18, s["fee"], s["sender"][:10], (t["to"] or "")[:10] if t else None, t["from"][:10] if t else None, t["selector"] if t else None, t["calldata_len"] if t else None)
            for s in e["pulls"][:2]: print("   pull", s["bn"]-b0, s["dl"], s["sender"][:10])
