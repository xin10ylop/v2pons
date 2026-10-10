import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_27")
from load import *
from rpcc import call, call_many
P = load_pools(); T = load_txs()
g3 = [p for p in P.values() if (p["to_code_hash"] or "").replace("0x","").startswith("f07d1c53")]
E = load_events(set(p["pid"] for p in g3))
p = g3[5]; e = E[p["pid"]]; b0 = p["launch_block"]
print(p["pid"], b0, p["hooks"], p["launch_to"], p["launch_from"])
codes = call_many([("eth_getCode", [p["hooks"], "latest"]), ("eth_getCode", [p["launch_to"], "latest"])])
for c in codes: print(len(c)//2 - 1, c[:120])
sw = e["swaps"][0]; pu = e["pulls"][0]
blocks = call_many([("eth_getBlockByNumber", [hex(b), True]) for b in range(b0, pu["bn"] + 3)])
watch = {"0x9fdd8ceab2de4fa2d9b0f1f37475a47baff8cd9a", p["launch_from"]}
hs = []
for b in blocks:
    for t in b["transactions"]:
        inp = t["input"]
        if t["from"] in watch or p["token"][2:] in inp or p["hooks"][2:] in inp or p["pid"][2:] in inp:
            hs.append(t["hash"]); print(int(b["number"],16)-b0, t["transactionIndex"], t["from"][:10], (t["to"] or "")[:10], inp[:10], len(inp)//2-1, int(t["value"],16)/1e18, "nonce", int(t["nonce"],16))
rc = call_many([("eth_getTransactionReceipt", [h]) for h in hs])
for h, r in zip(hs, rc): print(h[:12], r["status"], int(r["gasUsed"],16), len(r["logs"]), [l["address"][:10] + ":" + l["topics"][0][:10] for l in r["logs"]][:8])
