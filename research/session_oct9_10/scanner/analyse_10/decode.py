"""decode the launch calldata of the four families (from txs.jsonl)"""
import sys, json, re
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs(); F = load_families()
KEYS = json.load(open("keys.json"))
def words(inp): 
    d = inp[10:]; return [d[i:i+64] for i in range(0, len(d), 64)]
def strings(inp):
    b = bytes.fromhex(inp[2:]); return [s.decode() for s in re.findall(rb"[ -~]{6,}", b)]
out = {}
for k in KEYS:
    pid = F[k]["pids"][0]; t = T[P[pid]["launch_tx"]]
    inp = t.get("input") or t["input512"]
    print("=====", k[:70], "tx", t["hash"][:12], "gas", t["gas"], "max_prio", t["max_prio"], "type", t["type"])
    print("  strings:", strings(inp)[:20])
    ws = words(inp)
    for i, w in enumerate(ws[:40]):
        print(f"   w{i:02d} {w}")
    # selectors embedded (multicall inner)
    if t["selector"] == "ac9650d8":
        inner = re.findall(r"(?:dd46508f|f7020405|0d58b1db|2b67b570|48c89491|1efeed33|5b0d5984|e9ae5c53|db3e2198)", inp)
        print("  inner selectors found:", inner)
