"""for each traced launch: buy txs (from p1 buys) -> tx sender + nonce (eth_getTransactionByHash, batches of 40). out: nonces.json"""
from B import *
X = {x["h"]: x for x in launches()}; R = json.load(open(D + "p1.json"))
OUT = D + "nonces.json"
res = json.load(open(OUT)) if os.path.exists(OUT) else {}
tr = [json.loads(l) for l in open(D + "traces.jsonl")]
SK = {PM, "0x" + "0" * 40, "0x3194e32622c5d860a0572c74edda99dcfd8fc827", "0x8876789976decbfcbbbe364623c63652db8c0904"}
for d in tr:
    h = d["launch"]
    if h in res: continue
    buys = [(n, t, th) for n, t, th in R[h]["buys"] if t not in SK and t != X[h]["from"]]
    hs = list(dict.fromkeys(th for n, t, th in buys))
    txs = []
    for i in range(0, len(hs), 40):
        for k in range(8):
            try:
                r = post([{"jsonrpc": "2.0", "id": j, "method": "eth_getTransactionByHash", "params": [x]} for j, x in enumerate(hs[i:i+40])])
                if isinstance(r, list) and all(x.get("result") for x in r): break
            except RuntimeError: pass
            time.sleep(2 + 2 * k)
        txs += [x["result"] for x in sorted(r, key=lambda x: x["id"])]
        time.sleep(0.3)
    first = {}
    for t in txs:
        f = t["from"].lower()
        if f not in first: first[f] = int(t["nonce"], 16)
    res[h] = {"tag": d["tag"], "bn": d["bn"], "senders": first}
    nn = sorted(first.values())
    print(d["tag"], d["bn"], "buy txs", len(hs), "senders", len(first), "nonce min/med/max", nn[0] if nn else None, nn[len(nn)//2] if nn else None, nn[-1] if nn else None, flush=True)
    json.dump(res, open(OUT, "w"))
