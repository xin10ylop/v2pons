"""backward money trace through the shared block cache: hop to the largest incoming plain transfer; fetches missing 250-block chunks
politely (gentle_post, one process). usage: back2.py addr block hops [maxback]"""
import sys, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import *
from labels import *
def incoming(x, b, maxback):
    got = []
    for c in range(b // bc.CH, (b - maxback) // bc.CH - 1, -1):
        lo = max(c * bc.CH, b - maxback); hi = min(c * bc.CH + bc.CH - 1, b)
        rs = [r for r in touching([x], lo, hi) if r["to"] == x and r["eth"] > 0]
        got += rs
        if got: return got, lo
    return got, b - maxback
x, b, hops = sys.argv[1].lower(), int(sys.argv[2]), int(sys.argv[3]); mb = int(sys.argv[4]) if len(sys.argv) > 4 else 3000
for h in range(hops):
    got, lo = incoming(x, b, mb)
    if not got: print(f"hop {h}: {x} no incoming in [{b - mb}, {b}]", flush=True); break
    # all inputs within 60 blocks of the latest one (a sweep's batch)
    last = max(r["bn"] for r in got)
    batch_ = sorted([r for r in touching([x], last - 60, last) if r["to"] == x and r["eth"] > 0], key=lambda r: -r["eth"])
    tot = sum(r["eth"] for r in batch_)
    print(f"hop {h}: {x} {lab(x)} <- {len(batch_)} inputs, {tot:.4f} ETH, blocks {min(r['bn'] for r in batch_)}-{last}", flush=True)
    for r in batch_[:6]: print("      ", fmt(r), lab(r["from"]), flush=True)
    if len(batch_) > 6: print("       labels of all senders:", collections.Counter(lab(r["from"]) or "-" for r in batch_), flush=True)
    top = batch_[0]
    if top["nonce"] > 60 and lab(top["from"]) not in ("",): print("   stop: top sender is labeled", lab(top["from"])); break
    x, b = top["from"], top["bn"] - 1
print(bc.STATS)
