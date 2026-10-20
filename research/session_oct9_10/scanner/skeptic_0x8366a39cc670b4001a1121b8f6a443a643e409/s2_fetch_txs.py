"""Fetch (cached) the transactions of: every swap within add+600 in the 192 pools; every swap in the 80 blocks before each pull;
the add txs; the pull txs. Cache: txcache.jsonl (hash -> compact row)."""
import sys, os, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from load import *
from chain import batch
HERE = os.path.dirname(os.path.abspath(__file__))
KEY = "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|true"
F = load_families(); pids = F[KEY]["pids"]
E = load_events(set(pids)); T = load_txs()
CP = os.path.join(HERE, "txcache.jsonl")
cache = {}
if os.path.exists(CP):
    for l in open(CP): r = json.loads(l); cache[r["hash"]] = r
want = set()
for p in pids:
    e = E[p]; a = e["adds"][0]["bn"]; want.add(e["adds"][0]["tx"])
    for pl in e["pulls"]: want.add(pl["tx"])
    pb = e["pulls"][0]["bn"] if e["pulls"] else None
    for s in e["swaps"]:
        if s["bn"] <= a + 600 or (pb and pb - 80 <= s["bn"] <= pb): want.add(s["tx"])
def compact(h, t):
    return {"hash": h, "from": t["from"].lower(), "to": (t.get("to") or "").lower(), "value": int(t["value"], 16) if isinstance(t["value"], str) else t["value"],
            "nonce": int(t["nonce"], 16) if isinstance(t["nonce"], str) else t["nonce"], "sel": t["input"][2:10], "len": (len(t["input"]) - 2) // 2,
            "bn": int(t["blockNumber"], 16), "ti": int(t["transactionIndex"], 16), "gp": int(t.get("gasPrice") or "0x0", 16),
            "input": t["input"] if len(t["input"]) < 8000 else t["input"][:8000]}
# reuse census rows where the full input exists
for h in list(want - set(cache)):
    t = T.get(h)
    if t and t.get("input"):
        cache[h] = {"hash": h, "from": t["from"], "to": t["to"] or "", "value": t["value_wei"], "nonce": t["nonce"], "sel": t["selector"], "len": t["calldata_len"],
                    "bn": t["bn"], "ti": t["ti"], "gp": t["gas_price"] or 0, "input": t["input"]}
        with open(CP, "a") as f: f.write(json.dumps(cache[h]) + "\n")
todo = sorted(want - set(cache)); print("want", len(want), "todo", len(todo), flush=True)
for i in range(0, len(todo), 500):
    ch = todo[i:i + 500]
    res = batch([("eth_getTransactionByHash", [h]) for h in ch])
    with open(CP, "a") as f:
        for h, r in zip(ch, res):
            if r: cache[h] = compact(h, r); f.write(json.dumps(cache[h]) + "\n")
    print(i + len(ch), "of", len(todo), "missing", sum(1 for h in ch if h not in cache), flush=True)
    time.sleep(1)
print("done", len(want & set(cache)), "of", len(want))
