"""Batched multi-address log scan: Transfer to/from and Approval by any address in the list, [START, END] in 30k chunks.
Usage: mlogs.py START END out.json addrfile"""
import sys, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops")
from lib import *
START, END, OUT, AF = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
END = int(rpc("eth_blockNumber", []), 16) if END == "head" else int(END)
S = sorted({l.split()[0].lower() for l in open(AF) if l.startswith("0x")})
TW = ["0x" + "0" * 24 + w[2:] for w in S]
filters = [[T_TR, None, TW], [T_TR, TW], [T_AP, TW]]
jobs = [(f, a, min(a + 29999, END)) for a in range(START, END + 1, 30000) for f in filters]
out = []
def run(jobs):
    for i in range(0, len(jobs), 20):
        ch = jobs[i:i + 20]
        for k in range(10):
            try: r = post([{"jsonrpc": "2.0", "id": j, "method": "eth_getLogs", "params": [{"topics": f, "fromBlock": hex(a), "toBlock": hex(b)}]} for j, (f, a, b) in enumerate(ch)])
            except RuntimeError: r = None
            if isinstance(r, list) and len(r) == len(ch): break
            time.sleep(2 + 2 * k)
        else: raise RuntimeError("logs")
        redo = []
        for x in sorted(r, key=lambda x: x["id"]):
            f, a, b = ch[x["id"]]
            if "result" in x: out.extend(x["result"])
            else:
                if b <= a: raise RuntimeError(str(x))
                m = (a + b) // 2; redo += [(f, a, m), (f, m + 1, b)]
        if redo: run(redo)
        print(time.strftime("%H:%M:%S"), "jobs", i, len(jobs), "logs", len(out), flush=True)
run(jobs)
uniq = {(l["transactionHash"], l["logIndex"]): l for l in out}
json.dump({"start": START, "end": END, "addrs": S, "logs": list(uniq.values())}, open(OUT, "w"))
print("done", len(uniq))
