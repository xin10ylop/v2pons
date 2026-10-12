"""Our wallet's transactions that left no relay Swap (reverted buys / sells) around the live C-1 trades: the nonce gaps between our known relay
swaps (c02/c03) from Oct 11 20:50 to Oct 12 01:30 UTC are located by scanning the blocks between the two neighbouring known transactions
(full blocks, 25 per batch, paced), then their receipts. (The public node keeps no historical state, so eth_getTransactionCount bisection is
not possible.) Writes c04_ours.json."""
from common import *
import rpc
X = json.load(open(J("c01_launches.json"))); bytok = {x["token"].lower(): x for x in X}; bypid = {x["pid"]: x for x in X}
TX = {}
for l in open(J("c03_txs.jsonl")):
    t = json.loads(l); TX[t["hash"]] = t
rel = json.load(open(J("c02_relay_swaps.json")))
known = sorted({(TX[l["transactionHash"]]["nonce"], int(l["blockNumber"], 16)) for l in rel})
lo_b, hi_b = 86125000, 86290000
gaps = [(a, b) for a, b in zip(known, known[1:]) if b[0] - a[0] > 1 and lo_b <= a[1] <= hi_b]
print("nonce gaps:", [(a[0] + 1, b[0] - 1, a[1], b[1]) for a, b in gaps])
found = []
for a, b in gaps:
    want = set(range(a[0] + 1, b[0])); bl = list(range(a[1], b[1] + 1))
    for i in range(0, len(bl), 250):
        ch = bl[i:i + 250]
        for blk in rpc.batch("eth_getBlockByNumber", [[hex(x), True] for x in ch], n=25):
            for t in blk["transactions"]:
                if t["from"].lower() == WALLET and int(t["nonce"], 16) in want:
                    found.append({"nonce": int(t["nonce"], 16), "block": int(t["blockNumber"], 16), "ts": int(blk["timestamp"], 16), "hash": t["hash"], "to": (t.get("to") or "").lower(),
                                  "input": t["input"], "value": int(t["value"], 16), "txindex": int(t["transactionIndex"], 16)})
                    want.discard(int(t["nonce"], 16))
        if not want: break
    print(f"gap {a[0] + 1}..{b[0] - 1}: found {[f['nonce'] for f in found if a[0] < f['nonce'] < b[0]]}, missing {sorted(want)}", flush=True)
for f in found:
    rc = rpc.call("eth_getTransactionReceipt", [f["hash"]]); f.update({"status": int(rc["status"], 16), "gasUsed": int(rc["gasUsed"], 16), "logs": rc["logs"]})
    hit = [x for tk, x in bytok.items() if tk[2:] in f["input"].lower()] + [x for p, x in bypid.items() if p[2:] in f["input"].lower()]
    f["c1"] = hit[0]["pid"] if hit else None
    print(f"nonce {f['nonce']} block {f['block']} {utc(f['ts'])} idx {f['txindex']} to {f['to'][:10]} sel {f['input'][2:10]} n {(len(f['input']) - 2) // 2} value {f['value']} status {f['status']} gas {f['gasUsed']} logs {len(f['logs'])}"
          + (f" | C-1 pool {hit[0]['pid'][:12]} launch {hit[0]['lb']} {utc(hit[0]['ts'])} -> +{f['block'] - hit[0]['lb']}" if hit else ""))
json.dump(found, open(J("c04_ours.json"), "w"))
print("rpc", rpc.STATS)
