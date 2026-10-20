"""The fingerprint of every buy transaction (before the pull + 50 blocks) on the operator's launches: tx type, gas limit,
priority fee, calldata length, the Universal Router deadline word. Cache: react_fp.json {tx hash: [...]}"""
import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
D = json.load(open("react_data.json"))
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
hs = set()
for pid, P in D["pools"].items():
    for e in P["ev"]:
        if e["t0"] == T_SWAP and s128(W(e["data"], 0)) < 0 and e["tx"] in P["txs"]: hs.add(e["tx"])
hs = sorted(hs); print(len(hs), "buy txs", flush=True)
out = {}
for i in range(0, len(hs), 500):
    ch = hs[i:i+500]
    for h, t in zip(ch, batch([("eth_getTransactionByHash", [h]) for h in ch])):
        inp = t["input"]
        dl = inp[10+128:10+192] if inp[:10] == "0x3593564c" and len(inp) >= 10 + 192 else None
        out[h] = {"type": int(t["type"], 16), "gas": int(t["gas"], 16), "prio": int(t.get("maxPriorityFeePerGas", "0x0"), 16), "gp": int(t.get("gasPrice", "0x0"), 16),
                  "len": (len(inp) - 2) // 2, "dl_max": dl == "f" * 64 if dl else None, "dl": int(dl, 16) if dl and dl != "f" * 64 else None}
    print(i + len(ch), flush=True)
json.dump(out, open("react_fp.json", "w"))
