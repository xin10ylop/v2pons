"""Transactions behind the C-1 pools' swaps in [launch, min(first pull, launch + CAP)] and in [first pull - 300, first pull], plus every
pull transaction and every relay swap. Incremental cache c03_txs.jsonl: hash, from, to, sel, n (calldata bytes), value, nonce, block,
gas price, input (full unless the router: first 12 words)."""
from common import *
import rpc
CAP = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
X = {x["pid"]: x for x in json.load(open(J("c01_launches.json")))}
ev = jl(J("c02_events.jsonl"))
pull = {}
for l in ev:
    if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0:
        pid = l["topics"][1]; b = int(l["blockNumber"], 16) - X[pid]["lb"]; pull[pid] = min(pull.get(pid, 1 << 60), b)
need = set()
for l in ev:
    pid = l["topics"][1]; b = int(l["blockNumber"], 16) - X[pid]["lb"]; p = pull.get(pid, 1 << 60)
    if l["topics"][0] == T_ML or b <= min(p, CAP) or p - 300 <= b <= p: need.add(l["transactionHash"])
for l in json.load(open(J("c02_relay_swaps.json"))): need.add(l["transactionHash"])
have = set()
if os.path.exists(J("c03_txs.jsonl")):
    for l in open(J("c03_txs.jsonl")): have.add(json.loads(l)["hash"])
todo = sorted(need - have); print(f"needed {len(need)}, cached {len(need & have)}, to fetch {len(todo)}")
with open(J("c03_txs.jsonl"), "a") as f:
    for i in range(0, len(todo), 400):
        ch = todo[i:i + 400]
        for h, t in zip(ch, rpc.batch("eth_getTransactionByHash", [[h] for h in ch])):
            if t is None: print("missing", h); continue
            to = (t.get("to") or "").lower(); inp = t["input"]
            f.write(json.dumps({"hash": h, "from": t["from"].lower(), "to": to, "sel": inp[2:10], "n": (len(inp) - 2) // 2, "value": int(t["value"], 16),
                                "nonce": int(t["nonce"], 16), "block": int(t["blockNumber"], 16), "gp": int(t.get("gasPrice") or "0x0", 16),
                                "input": inp[:2 + 8 + 64 * 12] if to == ROUTER else inp}) + "\n")
        f.flush(); print(f"  {min(i + 400, len(todo))}/{len(todo)} rpc {rpc.STATS}", flush=True)
