"""cache-wide (no RPC) mixing test between the pots: every cached block file under ops/lch/bc. Sets: crowd A (32), crowd B (31),
copy-loop wallets (collector + the 1,408 wallets that sent it leftovers), fresh-pot crowd (fp 'fresh' family is too broad, so not used).
Reports: direct transfers A<->B, A<->copy; addresses that received from >=1 A and >=1 B/copy wallet; addresses that sent to both."""
import os, re, json, sys, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from labels import A, B, DISP, SWEEP, BDISP, BSWEEP
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch/bc/"
COPY = set(json.load(open("c_tail_senders.json"))) | {"0x3fc5b8b8dada622d7f41a35a0ad8ac2e5d0f8d8a"}
FIVE = "0x5861708803b8b73b2df8d985bed333b88c92dcc0"
side = {}
for a in A: side[a] = "A"
for a in DISP | SWEEP: side.setdefault(a, "Ahub")
for a in B | BDISP | BSWEEP: side[a] = "B"
for a in COPY: side[a] = "COPY"
recv = collections.defaultdict(set); sent = collections.defaultdict(set); direct = []; rng = []
files = sorted(os.listdir(D))
seen_blocks = set()
for f in files:
    if not f.endswith(".json"): continue
    try: d = json.load(open(D + f))
    except Exception: continue
    for k, (ts, tl) in d.items():
        bn = int(k)
        if bn in seen_blocks: continue
        seen_blocks.add(bn)
        for t in tl:
            fr, to = t[1], t[2]
            sf, st = side.get(fr), side.get(to)
            if sf and st and sf[0] != st[0] and {sf[0], st[0]} != {"B", "C"}:
                direct.append((bn, fr, sf, to, st, int(t[3]) / 1e18, t[4], t[5]))
            if sf and st and {sf, st} == {"B", "COPY"}: pass
            if t[5] in ("0x", "") and int(t[3]) > 0:
                if sf: recv[to].add(sf)
                if st: sent[fr].add(st)
print("blocks scanned", len(seen_blocks), min(seen_blocks), max(seen_blocks))
print("direct transfers between A/Ahub and B/COPY:", len(direct))
for x in direct[:30]: print("  ", x)
bothin = {a: s for a, s in recv.items() if any(x.startswith("A") for x in s) and (("B" in s) or ("COPY" in s))}
bothout = {a: s for a, s in sent.items() if any(x.startswith("A") for x in s) and (("B" in s) or ("COPY" in s))}
print("addresses receiving from both an A-side and a B/copy-side wallet:", len(bothin)); [print("  ", a, s) for a, s in list(bothin.items())[:30]]
print("addresses sending to both an A-side and a B/copy-side wallet:", len(bothout)); [print("  ", a, s) for a, s in list(bothout.items())[:30]]
json.dump({"direct": direct, "bothin": {a: sorted(s) for a, s in bothin.items()}, "bothout": {a: sorted(s) for a, s in bothout.items()}}, open("mix.json", "w"))
