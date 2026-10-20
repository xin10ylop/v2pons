"""p04: every Swap / Mint / Burn / Collect of the 102 launch pools (p03) from the launch block to launch + 3,000 (V3 pool events by address list,
groups of <= 20 pools launched within 6,000 blocks). -> p04_events.jsonl (raw logs, one per line, with the pool)"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rpc
J = lambda n: os.path.join(HERE, n)
TOP = ["0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67", "0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde",
       "0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c", "0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0"]
WIN = 3000
X = sorted(json.load(open(J("p03_launches.json"))), key=lambda x: x["block"])
head = int(rpc.call("eth_blockNumber", []), 16)
done = set()
if os.path.exists(J("p04_done.json")): done = set(json.load(open(J("p04_done.json"))))
groups = []; g = []
for x in X:
    if g and (len(g) >= 20 or x["block"] - g[0]["block"] > 6000):
        groups.append(g); g = []
    g.append(x)
if g: groups.append(g)
for g in groups:
    key = g[0]["tx"]
    if key in done: continue
    a = g[0]["block"]; b = min(head, g[-1]["block"] + WIN)
    addrs = ["0x" + x["pool"] for x in g]
    ls = rpc.logs({"address": addrs, "topics": [TOP]}, a, b)
    with open(J("p04_events.jsonl"), "a") as f:
        for l in ls:
            f.write(json.dumps({k: l[k] for k in ("address", "topics", "data", "blockNumber", "transactionHash", "logIndex", "transactionIndex")}) + "\n")
    done.add(key); json.dump(sorted(done), open(J("p04_done.json"), "w"))
    print("group", len(g), a, b, "logs", len(ls), flush=True)
json.dump({"head": head}, open(J("p04_head.json"), "w"))
print("rpc", rpc.STATS)
