"""Every ModifyLiquidity of the 97 pools (F1 69, F2 28) and every Swap of the F2 pools from the first launch to the head (beyond the census's
3,000-block window), eth_getLogs in 100k-block chunks, cached; plus the F1 hooks' current tax getters (9731aa2e, f4364515)."""
import sys, json, os
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from load import *
from chain import rpc, batch, logs, PM, T_SWAP, T_ML
HERE = os.path.dirname(os.path.abspath(__file__))
ids = json.load(open(os.path.join(HERE, "pids.json"))); P = load_pools()
CACHE = os.path.join(HERE, "postwindow_logs.json")
C = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
head = C.get("head") or int(rpc("eth_blockNumber", []), 16); C["head"] = head
a0 = min(P[x]["launch_block"] for x in ids["F1"] + ids["F2"])
def scan(key, topics0, pids):
    if key in C: return
    out = []
    for i in range(0, len(pids), 40):
        grp = pids[i:i + 40]; a = a0
        while a <= head:
            b = min(a + 99_999, head)
            out += logs({"address": PM, "topics": [topics0, grp]}, a, b); a = b + 1
    C[key] = out; json.dump(C, open(CACHE, "w"))
scan("ml_all", [T_ML], ids["F1"] + ids["F2"])
scan("swap_f2", [T_SWAP], ids["F2"])
if "f1_tax" not in C:
    hooks = [P[x]["hooks"] for x in ids["F1"]]
    r = batch([("eth_call", [{"to": h, "data": "0x" + s}, "latest"]) for h in hooks for s in ("9731aa2e", "f4364515")])
    C["f1_tax"] = {pid: [int(r[2 * i], 16) if r[2 * i] else None, int(r[2 * i + 1], 16) if r[2 * i + 1] else None] for i, pid in enumerate(ids["F1"])}
    json.dump(C, open(CACHE, "w"))
print("head", head, "ml", len(C["ml_all"]), "swaps f2", len(C["swap_f2"]))
import collections
print("f1 current tax bps", collections.Counter(tuple(v) for v in C["f1_tax"].values()).most_common())
