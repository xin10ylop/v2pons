"""Follow a few of the fresh (nonce 0) wallets that buy through the 0x65050a9b router: read every block forward from their buy until each
of their transactions (nonce 0 .. current nonce - 1) is found (or MAXB blocks), and print what each transaction does (to, value, selector,
calldata words that look like addresses). Then the same backward from the buy for MAXBACK blocks for any transaction paying them or naming them.
Usage: x08_trace_fresh.py wallet:buy_block [...]"""
import sys, json
from rpc import call, batch, STATS
MAXB = 3000; MAXBACK = int(__import__("os").environ.get("MAXBACK", "0"))
out = open("x08_trace_fresh.jsonl", "a")
def addrs(inp):
    ws = [inp[10 + 64 * i: 10 + 64 * (i + 1)] for i in range((len(inp) - 10) // 64)]
    return ["0x" + w[24:] for w in ws if w[:24] == "0" * 24 and int(w[24:], 16) > 1 << 100]
for arg in sys.argv[1:]:
    w, b0 = arg.split(":"); w = w.lower(); b0 = int(b0)
    n_now = int(call("eth_getTransactionCount", [w, "latest"]), 16)
    found = {}; b = b0
    while len(found) < n_now and b < b0 + MAXB:
        bl = list(range(b, b + 20))
        for bn, blk in zip(bl, batch("eth_getBlockByNumber", [[hex(x), True] for x in bl], 20)):
            for t in (blk or {}).get("transactions", []):
                if t["from"].lower() == w:
                    found[int(t["nonce"], 16)] = {"bn": bn, "to": (t.get("to") or "").lower(), "value": int(t["value"], 16) / 1e18, "sel": t["input"][:10], "len": (len(t["input"]) - 2) // 2,
                                                  "addrs": addrs(t["input"]), "hash": t["hash"]}
                elif w[2:] in (t.get("input") or "").lower() or (t.get("to") or "").lower() == w:
                    found.setdefault("in", []).append({"bn": bn, "from": t["from"].lower(), "to": (t.get("to") or "").lower(), "sel": t["input"][:10], "value": int(t["value"], 16) / 1e18})
        b += 20
    back = []
    if MAXBACK:
        b = b0 - 1
        while b > b0 - MAXBACK and not back:
            bl = list(range(b - 19, b + 1))
            for bn, blk in zip(bl, batch("eth_getBlockByNumber", [[hex(x), True] for x in bl], 20)):
                for t in (blk or {}).get("transactions", []):
                    if (t.get("to") or "").lower() == w or w[2:] in (t.get("input") or "").lower():
                        back.append({"bn": bn, "before": b0 - bn, "from": t["from"].lower(), "to": (t.get("to") or "").lower(), "sel": t["input"][:10], "value": int(t["value"], 16) / 1e18,
                                     "len": (len(t["input"]) - 2) // 2, "hash": t["hash"]})
            b -= 20
    rec = {"w": w, "b0": b0, "nonce_now": n_now, "txs": found, "back": back, "back_scanned": MAXBACK}
    out.write(json.dumps(rec) + "\n"); out.flush()
    print(w, "nonce now", n_now)
    for k in sorted([k for k in found if k != "in"]):
        x = found[k]; print(f"   nonce {k}: +{x['bn'] - b0} blocks, to {x['to']} value {x['value']:.6f} sel {x['sel']} len {x['len']} addrs {x['addrs'][:4]}")
    for x in found.get("in", [])[:5]: print("   in:", x)
    for x in back[:5]: print("   back:", x)
print(STATS)
