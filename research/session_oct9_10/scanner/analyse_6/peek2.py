import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); P = load_pools(); T = load_txs()
KEYS = ["0x404700be6b535e6aa7fd744f242d8cf78135817c|7fde822e|804|10000|200|true",
"0xe696daf67fe25c5936187fc1edf38404353d5f72|7fde822e|804|10000|200|true",
"0xb40382548413c559ad7f0bb6e24410401238eded|7fde822e|804|10000|200|true",
"0x0000ffffbe8efe702c8703ae3477ff5de3d319c0|ac9650d8|1316|2500|25|true"]
pids = set(); [pids.update(F[k]["pids"]) for k in KEYS]
E = load_events(pids)
for k in KEYS:
    print("=====", k)
    c = collections.Counter()
    for pid in F[k]["pids"]:
        e = E[pid]
        for s in e["swaps"]:
            t = T.get(s["tx"])
            c[(t["from"] if t else None, t["to"] if t else None, t["selector"] if t else None, s["sender"])] += 1
            print(pid[:10], s["bn"] - e["launch_block"], s["ti"], s["a0"], s["a1"], s["sqrt_p"], s["liq"], s["fee"], t and t["from"], t and t["to"], t and t["selector"], t and t["calldata_len"])
        print("   adds", [(a["bn"] - e["launch_block"], a["lo"], a["hi"], a["dl"], a["sender"]) for a in e["adds"]], "zm", len(e["zero_mods"]))
    print(c)
# launch tx examples
for k in KEYS:
    pid = F[k]["pids"][0]; t = T[P[pid]["launch_tx"]]
    print(k, t["hash"], t["from"], t["to"], t["value_eth"], t["gas"], t["gas_price"], t["max_prio"], t["type"])
    inp = t["input"]; print(inp[:10]); 
    for i in range((len(inp) - 10) // 64): print("  ", i, inp[10 + 64 * i: 10 + 64 * (i + 1)])
