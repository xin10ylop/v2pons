import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
KEY = "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|true"
F = load_families(); pids = F[KEY]["pids"]
P = load_pools(); E = load_events(set(pids[:1])); T = load_txs()
e = E[pids[0]]
for s in e["swaps"][:8]:
    t = T[s["tx"]]
    print(s["bn"]-e["adds"][0]["bn"], s["a0"]/1e18, t["from"], t["to"], t["nonce"], t["selector"], t["calldata_len"], t["value_eth"], t["gas_price"], t.get("max_prio"))
    inp = t.get("input") or t["input512"]
    if t["selector"] == "7169b574":
        w = [inp[10+64*i:10+64*(i+1)] for i in range((len(inp)-10)//64)]
        for i, x in enumerate(w): print("   ", i, x)
t = T[P[pids[0]]["launch_tx"]]; print("launch", {k: v for k, v in t.items() if k not in ("input512",)})
