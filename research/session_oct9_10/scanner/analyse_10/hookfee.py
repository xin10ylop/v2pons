"""Family 2 (launcher 0x2a53386d, hook 0xe5e70264, flags BEFORE_INITIALIZE|AFTER_SWAP|AFTER_SWAP_RETURNS_DELTA): measure the hook's
take on buys and sells from a few receipts (one POST, cached)."""
import sys, json, os, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from load import *
from chain import batch
F = load_families(); P = load_pools(); T = load_txs()
key = "0x2a53386daf0bf3eedd9e715d162649764358c7b5|3d9ab7c9|292|0|200|false"
pids = F[key]["pids"]; E = load_events(set(pids))
CACHE = "hookfee_rcpts.json"
want = []
for pid in pids[:4]:
    sw = [s for s in E[pid]["swaps"] if s["tx"] in T]
    buys = [s for s in sw if s["a0"] < 0 and T[s["tx"]]["to"] == "0x8876789976decbfcbbbe364623c63652db8c0904"]
    sells = [s for s in sw if s["a0"] > 0 and T[s["tx"]]["to"] == "0x8876789976decbfcbbbe364623c63652db8c0904"]
    want += [x["tx"] for x in buys[:2] + sells[:1]]
    want.append(P[pid]["launch_tx"])
want = list(dict.fromkeys(want))
if os.path.exists(CACHE): R = json.load(open(CACHE))
else:
    R = dict(zip(want, batch([("eth_getTransactionReceipt", [h]) for h in want]))); json.dump(R, open(CACHE, "w"))
HOOK = "0xe5e702641ea86f4ae6cc3cdaed2b886f976be044"
TR = "0xddf252ad1be2c69b068fc378daa20e8a4dd28d89dd5a7a8e1e7c8d8f5b2a3c4d"[:10]
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16)
txpid = {}
for pid in pids:
    for s in E[pid]["swaps"]: txpid.setdefault(s["tx"], (pid, s))
for h, r in R.items():
    t = T[h]
    print("==", h[:12], "to", t["to"][:10], "value", t["value_wei"], "sel", t["selector"], "status", r["status"])
    pid, s = txpid.get(h, (None, None))
    if s: print("   swap a0", s["a0"], "a1", s["a1"], "fee", s["fee"], "token", P[pid]["token"][:10])
    for l in r["logs"]:
        a = l["address"]; t0 = l["topics"][0][:10] if l["topics"] else None
        tag = "HOOK" if a == HOOK else ("PM" if a == "0x8366a39cc670b4001a1121b8f6a443a643e40951" else ("TOKEN" if pid and a == P[pid]["token"] else a[:10]))
        extra = ""
        if t0 == "0xddf252ad" and len(l["data"]) >= 66 and len(l["topics"]) == 3: extra = f"from {l['topics'][1][-40:][:8]} to {l['topics'][2][-40:][:8]} amt {W(l['data'], 0)}"
        print(f"   {tag:8s} {t0} n_topics {len(l['topics'])} {extra} data {l['data'][:200]}")
