import sys, os, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
C = json.load(open("rpc_cache.json"))
F = load_families(); P = load_pools()
K2 = "0x5bd1fbe78a78fe8236fa00cf48fbeba74ae34661|a80ac0c2|1156|0|200|false"
K3 = "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|3000|60|true"
K4 = "0xa0ce0291c181f800e7a5096b433685c37cfbf4df|617ac5de|676|8388608|200|false"
E = load_events(set(F[K2]["pids"] + F[K3]["pids"] + F[K4]["pids"]))
TR = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f179063b0aef6f42d3b1c2bc"
print("== family 3 adds")
for pid in F[K3]["pids"]:
    for a in E[pid]["adds"]:
        t = C["tx:" + a["tx"]]; r = C["rc:" + a["tx"]]
        print(pid[:10], "add", a["bn"] - P[pid]["launch_block"], "from", t["from"][:10], "to", t["to"][:10], "sel", t["input"][:10], "len", (len(t["input"])-2)//2, "val", int(t["value"],16)/1e18, "nonce", int(t["nonce"],16), "status", r["status"], "nlogs", len(r["logs"]))
def show(h, b0):
    r = C["rc:" + h]; t = C.get("tx:" + h)
    print("  tx", h[:10], "bn+", int(r["blockNumber"],16)-b0, "from", r["from"][:10], "to", r["to"][:10], "val", t and int(t["value"],16)/1e18, "status", r["status"], "gas", int(r["gasUsed"],16))
    for l in r["logs"]:
        tp = l["topics"]
        if tp and tp[0].startswith(TR[:20]):
            print("     Transfer", l["address"][:10], "from", "0x"+tp[1][-40:][:8], "to", "0x"+tp[2][-40:][:8], int(l["data"],16)/1e18)
        else:
            print("     log", l["address"][:10], tp[0][:10] if tp else None, l["data"][:130])
print("== family 2 swaps")
for pid in F[K2]["pids"]:
    for s in E[pid]["swaps"][:6]:
        print(pid[:10], "swap a0", s["a0"]/1e18, "a1", s["a1"]/1e18)
        show(s["tx"], P[pid]["launch_block"])
print("== family 4 swaps")
for pid in F[K4]["pids"][3:5]:
    for s in E[pid]["swaps"][:4]:
        print(pid[:10], "swap a0", s["a0"]/1e18, "a1", s["a1"]/1e18)
        show(s["tx"], P[pid]["launch_block"])
