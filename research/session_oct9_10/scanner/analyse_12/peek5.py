import sys, os, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
C = json.load(open("rpc_cache.json"))
F = load_families(); P = load_pools(); T = load_txs()
K3 = "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|3000|60|true"
K4 = "0xa0ce0291c181f800e7a5096b433685c37cfbf4df|617ac5de|676|8388608|200|false"
E = load_events(set(F[K3]["pids"] + F[K4]["pids"]))
TR = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f179063b0aef6f42d3b1c2bc"
def show(h, b0):
    r = C["rc:" + h]; t = C.get("tx:" + h)
    print("  tx", h[:10], "bn+", int(r["blockNumber"],16)-b0, "ti", int(r["transactionIndex"],16), "from", r["from"][:10], "to", r["to"][:10], "val", t and int(t["value"],16)/1e18, "status", r["status"], "gas", int(r["gasUsed"],16), "egp", int(r["effectiveGasPrice"],16))
    for l in r["logs"]:
        tp = l["topics"]
        if tp and tp[0].startswith(TR[:20]):
            print("     Transfer", l["address"][:10], "from", "0x"+tp[1][-40:][:8], "to", "0x"+tp[2][-40:][:8], (int(l["data"],16)/1e18 if len(l["data"])>2 else "nft:"+str(int(tp[3],16)) if len(tp)>3 else None))
        else:
            print("     log", l["address"][:10], tp[0][:10] if tp else None, [x[:12] for x in tp[1:]], l["data"][:130])
for pid in F[K3]["pids"][:3]:
    b0 = P[pid]["launch_block"]
    for a in E[pid]["adds"]: show(a["tx"], b0)
    for s in E[pid]["swaps"][:2]: show(s["tx"], b0)
print("launch tx of fam3", T[P[F[K3]["pids"][0]]["launch_tx"]]["from"], T[P[F[K3]["pids"][0]]["launch_tx"]]["nonce"])
print("== fam 4")
for pid in F[K4]["pids"][3:4]:
    b0 = P[pid]["launch_block"]
    for s in E[pid]["swaps"][:4]: show(s["tx"], b0)
    lt = T[P[pid]["launch_tx"]]
    print("launch input", lt["input"][:700])
