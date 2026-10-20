"""the migration pools' hook 0xe5e70264 (flags beforeInitialize|afterSwap|afterSwapReturnDelta): its code size, views, and the fee it takes,
from receipts of direct Universal-Router swaps in migration pools (the Swap event's amounts vs the hook's own logs and the user's transfers)."""
import json, collections
from krpc import *
HOOK = "0xe5e702641ea86f4ae6cc3cdaed2b886f976be044"
code = rpc("eth_getCode", [HOOK, "latest"]); print("hook code bytes", (len(code) - 2) // 2, "flags", bin(int(HOOK[-4:], 16) & 0x3fff))
E = json.load(open(os.path.join(DATA, "mig_pool_events.json")))
pick = []
for pid, ev in list(E.items())[:40]:
    sw = [e for e in ev if e[0] == "s"]
    for e in sw[5:7]: pick.append((pid, e))
pick = pick[:30]
R = batch([("eth_getTransactionReceipt", [e[12]]) for _, e in pick])
T = batch([("eth_getTransactionByHash", [e[12]]) for _, e in pick])
res = []
for (pid, e), r, t in zip(pick, R, T):
    if not r: continue
    hl = [l for l in r["logs"] if l["address"].lower() == HOOK]
    a0, a1 = e[6], e[7]
    print(pid[:10], "router", e[5][:10], "a0(ETH)", a0, "a1(tok)", a1, "tx.value", int(t["value"], 16), "to", t["to"][:10])
    for l in hl: print("     hook log", l["topics"][0][:10], [A(x)[:10] for x in l["topics"][1:]], [W(l["data"], i) for i in range((len(l["data"]) - 2) // 64)])
    tl = [l for l in r["logs"] if l["topics"][0][:10] == "0xddf252ad"]
    for l in tl: print("     transfer", l["address"][:10], A(l["topics"][1])[:10], "->", A(l["topics"][2])[:10], int(l["data"], 16))
    res.append({"pool": pid, "swap": e, "hook_logs": hl, "receipt_logs": r["logs"], "value": int(t["value"], 16)})
json.dump(res, open(os.path.join(DATA, "k25_hook_receipts.json"), "w"))
