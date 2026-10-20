import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
D = json.load(open("react_data.json"))
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
pids = sorted(D["pools"], key=lambda p: D["pools"][p]["meta"]["block"])
want = {"0x8700722d", "0x295877ce", "0xdc2e8661", "0x75442507", "0x2b7be2fa", "0xe71a69f4", "0x0b410a5f", "0x94e12c34", "0x6e0fb625", "0x6c76d077"}
seen = collections.Counter(); hs = []
for n in (91, 94, 96, 97, 100, 33, 34, 41, 45, 0):
    P = D["pools"][pids[n]]
    for e in P["ev"]:
        t = P["txs"].get(e["tx"])
        if t and e["t0"] == T_SWAP and s128(W(e["data"], 0)) < 0 and t["from"][:10] in want and seen[t["from"]] < 2:
            seen[t["from"]] += 1; hs.append((n, t["from"], e["tx"]))
txs = batch([("eth_getTransactionByHash", [h]) for _, _, h in hs])
for (n, w, h), t in zip(hs, txs):
    inp = t["input"]; d = bytes.fromhex(inp[2:])
    print(n, w[:10], "type", t["type"], "gas", int(t["gas"], 16), "gasPrice", int(t.get("gasPrice", "0x0"), 16), "maxPrio", int(t.get("maxPriorityFeePerGas", "0x0"), 16), "len", len(d), "sel", inp[:10])
    print("    ", inp[10:10+64*4], "...", inp[-200:])
