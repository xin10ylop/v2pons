"""(a) F4b gating: every tx of blocks live+1..live+76 of 3 F4b pools (and 1 F4a pool), the ones whose calldata names the token, and their receipts
   (did anyone try to buy before the crowd's first buy, and did it revert?)
(b) F4a trap test: the transactions of the last 6 swaps before each pull (57 pools) and, as a baseline, of 6 swaps around live+700 in 40 pools
   that were not pulled in the window. Cached in cache/fetch2.json."""
import sys, os, json, random
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from chain import batch
from load import *
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "cache", "fetch2.json")
C = json.load(open(OUT)) if os.path.exists(OUT) else {"blocks": {}, "rcpt": {}, "tx": {}}
P = load_pools(); T = load_txs()
PMA = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
F4 = [p["pid"] for p in P.values() if p["launch_to"] == PMA and p["selector"] == "6276cbbe" and p["calldata_len"] == 196]
F4a = [x for x in F4 if P[x]["fee"] == 500 and P[x]["tick_spacing"] == 1 and P[x]["hooks_zero"]]
F4b = [x for x in F4 if P[x]["fee"] == 500 and P[x]["tick_spacing"] == 1 and not P[x]["hooks_zero"]]
E = load_events(set(F4a) | set(F4b))
# (a)
sample = F4b[:3] + F4a[:1]
need = []
for pid in sample:
    lb = E[pid]["adds"][0]["bn"]
    need += [b for b in range(lb, lb + 77) if str(b) not in C["blocks"]]
res = batch([("eth_getBlockByNumber", [hex(b), True]) for b in need])
for b, r in zip(need, res):
    if r: C["blocks"][str(b)] = [{"hash": t["hash"], "from": t["from"].lower(), "to": (t["to"] or "").lower(), "ti": int(t["transactionIndex"], 16), "input": t["input"][:4000],
                                  "value": int(t["value"], 16)} for t in r["transactions"]]
hits = []
for pid in sample:
    lb = E[pid]["adds"][0]["bn"]; tok = P[pid]["token"][2:]
    for b in range(lb, lb + 77):
        for t in C["blocks"].get(str(b), []):
            if tok in t["input"].lower() or pid[2:] in t["input"].lower(): hits.append((pid, b, t["hash"]))
needr = [h for _, _, h in hits if h not in C["rcpt"]]
res = batch([("eth_getTransactionReceipt", [h]) for h in needr])
for h, r in zip(needr, res):
    if r: C["rcpt"][h] = {"status": int(r["status"], 16), "gasUsed": int(r["gasUsed"], 16), "nlogs": len(r["logs"])}
# (b)
want = set()
for pid in F4a:
    e = E[pid]
    if e["pulls"]:
        pb = e["pulls"][0]["bn"]; prev = [s for s in e["swaps"] if s["bn"] <= pb][-6:]
        want |= {s["tx"] for s in prev}
random.seed(26)
base = [pid for pid in F4a if not E[pid]["pulls"]]; random.shuffle(base)
for pid in base[:40]:
    e = E[pid]; lb = e["adds"][0]["bn"]; prev = [s for s in e["swaps"] if s["bn"] <= lb + 700][-6:]
    want |= {s["tx"] for s in prev}
needt = sorted(h for h in want if h not in C["tx"] and h not in T)
res = batch([("eth_getTransactionByHash", [h]) for h in needt])
for h, r in zip(needt, res):
    if r: C["tx"][h] = {"hash": h, "from": r["from"].lower(), "to": (r["to"] or "").lower(), "nonce": int(r["nonce"], 16), "value_wei": int(r["value"], 16),
                        "selector": r["input"][2:10], "calldata_len": (len(r["input"]) - 2) // 2, "input": r["input"][:3000]}
json.dump(C, open(OUT, "w"))
print("blocks", len(C["blocks"]), "receipts", len(C["rcpt"]), "txs", len(C["tx"]), "hits", len(hits), "fetched blocks", len(need), "rcpts", len(needr), "txs", len(needt))
