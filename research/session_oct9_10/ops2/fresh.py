"""the 'fresh' family pot (Oct 8 11:45-13:21), cache only: for each fresh deployer, funding chain back to a hub (a wallet with >=8 inputs)
and the hub's input composition; payout destination after the pull"""
import sys, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import *
from labels import *
DEPS = [(83289397, "0x93108985bc375b5084dea1a337be2fe1c4d22cc6", 83289534), (83292456, "0xc3285d402fde630025ba72afede321e84d1c5f67", 83298763),
        (83301893, "0x4d91257455e843c4ab848c71c9f1ec0dbb05c50a", 83311746), (83313345, "0xc121a22a4f0b24d534d0c8d742ca99066090dd9d", 83313728),
        (83314335, "0x56e3d10998fd064bbfa2eb67d7e1e45b2da273bd", 83319245), (83323064, "0x583fec3510ed754c5953559af2598262fbdc7a9a", 83339058),
        (83341600, "0x1b676fa701e2885819b66b08fdcf98f344644dd5", 83342149), (83342440, "0x7261b7d6d7f62bda4132e6e92779584589307291", 83342688)]
CR = [(83240750, 83319749), (83340750, 83342749)]
def cached(b): return any(a <= b <= z for a, z in CR)
def tx(x, lo, hi):
    out = []
    for a, z in CR:
        l, h = max(lo, a), min(hi, z)
        if l <= h: out += touching([x], l, h, cached_only=True)
    return out
HUBS = set()
for L, d, pull in DEPS:
    print(f"== deployer {d[:12]} launch {L}")
    x, b = d, L
    for hop in range(5):
        ins = [r for r in tx(x, b - 3000, b) if r["to"] == x and r["eth"] > 0.05]
        if not ins: print(f"   {x[:12]}: no cached incoming before {b}"); break
        r = max(ins, key=lambda r: r["bn"])
        f = r["from"]; allin = [q for q in tx(f, r["bn"] - 40, r["bn"]) if q["to"] == f]
        print(f"   {x[:12]} <- {f[:12]} {r['eth']:.4f} (sender n{r['nonce']}, blk {r['bn']}); {f[:12]} had {len(allin)} inputs in the 40 blocks before")
        if len(allin) >= 8:
            HUBS.add(f); big = max(allin, key=lambda q: q["eth"])
            print(f"      HUB {f}: {len(allin)} inputs sum {sum(q['eth'] for q in allin):.4f}; labels {dict(collections.Counter(lab(q['from']) or '-' for q in allin))}; largest {big['from']} {big['eth']:.4f} n{big['nonce']}")
            break
        x, b = f, r["bn"] - 1
    outs = [r for r in tx(d, pull, pull + 3000) if r["from"] == d and r["eth"] > 0.05]
    for r in outs[:2]: print(f"   payout: {fmt(r)} {lab(r['to'])}")
    if not outs: print("   payout: not in cached blocks" if not cached(pull + 100) else "   payout: none within 3000 cached blocks")
