"""forward money trace, cache only: from addr after block b, take its next outgoing plain transfer(s); follow the largest (> min_eth);
print hub fan-outs and labels; stop where the cache ends. usage: fwd2.py addr block steps [window]"""
import sys, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import *
from labels import *
x, b, steps = sys.argv[1].lower(), int(sys.argv[2]), int(sys.argv[3]); win = int(sys.argv[4]) if len(sys.argv) > 4 else 20000
for s in range(steps):
    outs = []; e = b
    for c in range(b // bc.CH, (b + win) // bc.CH + 1):
        if not have(c): print(f"   cache ends at chunk {c * bc.CH}"); break
        lo, hi = max(b, c * bc.CH), c * bc.CH + bc.CH - 1
        rs = touching([x], lo, hi, cached_only=True)
        calls = [r for r in rs if r["from"] == x and not (r["sel"] in ("0x", "") and r["eth"] > 0)]
        for r in calls: print(f"   call: {fmt(r)}")
        outs = [r for r in rs if r["from"] == x and r["sel"] in ("0x", "") and r["eth"] > 0.3]
        if outs:
            allo = [r for r in touching([x], outs[0]["bn"], outs[0]["bn"] + 150, cached_only=True) if r["from"] == x and r["eth"] > 0]
            break
    if not outs: print(f"step {s}: {x} no outgoing > 0.3 ETH found after {b}"); break
    big = max(allo, key=lambda r: r["eth"])
    ins = [r for r in touching([x], outs[0]["bn"] - 60, outs[0]["bn"], cached_only=True) if r["to"] == x and r["eth"] > 0]
    print(f"step {s}: {x} {lab(x)} | {len(ins)} inputs just before ({sum(r['eth'] for r in ins):.4f} ETH; {dict(collections.Counter(lab(r['from']) or '-' for r in ins))}) "
          f"| {len(allo)} outs ({sum(r['eth'] for r in allo):.4f} ETH; {dict(collections.Counter(lab(r['to']) or '-' for r in allo))})")
    print(f"     biggest out: {fmt(big)} {lab(big['to'])}")
    x, b = big["to"], big["bn"]
