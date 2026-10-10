import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); k = "0x34c0d66f3a57a4cad3c5f792f5028d9c1da83d12|f03e0011|292|0|200|false"
E = load_events(set(F[k]["pids"])); T = load_txs()
for pid in F[k]["pids"]:
    for s in E[pid]["swaps"]:
        t = T.get(s["tx"])
        print(pid[:10], s["bn"] - E[pid]["launch_block"], "a0", s["a0"], "a1", s["a1"], "tx", s["tx"], "value", t and t["value_wei"], "to", t and t["to"][:10], "sel", t and t["selector"], "ratio", t and t["value_wei"] and (-s["a0"]) / t["value_wei"])
