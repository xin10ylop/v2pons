import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); P = load_pools()
KEYS = json.load(open("keys.json"))
E = load_events(set(F[KEYS[1]]["pids"][:3]) | set(F[KEYS[3]]["pids"][:3])); T = load_txs()
for k in (KEYS[1], KEYS[3]):
    for pid in F[k]["pids"][1:3]:
        e = E[pid]; s = [x for x in e["swaps"] if x["a0"] < 0][0]
        t = T[s["tx"]]
        print(pid[:10], P[pid]["token"], "a0", s["a0"], "a1", s["a1"], "tx", t["hash"], t["to"], t["from"], t["calldata_len"])
        inp = t.get("input") or t["input512"]
        print("sel", inp[:10])
        for i in range((len(inp) - 10) // 64):
            print(f"  w{i:02d} {inp[10+64*i:10+64*(i+1)]}")
