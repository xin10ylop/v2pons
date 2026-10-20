"""cache-wide (no RPC) money-mixing test between four pots. A: crowd A + A hubs (Oct 9) + Oct 8 A hubs/capital; B: crowd B + B hubs +
Oct 8 B hubs/capital + collector + 1,408 copy wallets; D: the 32 wallets swept by 0xdef59ef1 at 13:50 + its hubs; F: the fresh-pot hubs and
every wallet they paid or were paid by (11:45-13:21). Reports direct plain transfers between pots and addresses receiving from / sending to two pots."""
import os, json, sys, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from labels import A, B, DISP, SWEEP, BDISP, BSWEEP
from potsets import A_OCT8, B_OCT8
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch/bc/"
COPY = set(json.load(open("c_tail_senders.json"))) | {"0x3fc5b8b8dada622d7f41a35a0ad8ac2e5d0f8d8a"}
CD = {l.strip() for l in open("crowdD.txt") if l.strip()} | {"0xdef59ef12a5b4a40f2ee0ab4d063532c943670c2", "0x0c8c381eddf7be5e1b5f888b12c418d75f788584",
      "0x8ef3c8f1f06054677f63a75dd4cde6f881e4c253", "0x028561369ba146ac5d5ca498f5dc5b41960a7906", "0xba5dc35a844ac0e69df312868d3fb6076d0172de",
      "0xba3101c3bbf59e418ce5b1a586326faa7977ff5b", "0x9a297073cbbe427d9150361f20d0b95bdc48cdc6"}
FH = {"0x0f77ceece905c99200cb9f12b7e993a57ac7abb7", "0x107b31ad7c9d2eb3d4f05af97b40345efc6b64df", "0x24bc5f3cee26fe0666db054d5da4d11c8abba9a3",
      "0x295c7408cf66c6070340588f5f0a23b8722ce670", "0xf8c511f8de7f0f3d34a1fa3e0f9087f023084955", "0xd4b94999f319d423b479f149b427e9593ebb2ad3",
      "0x5477a0daa7e8510ade3822bc5b7d78cc31494b1c", "0x92b66c43b3f27c258877847c8c420e554daf4fd1", "0xc43b385aa2e3e0fba6dc0929a483da160d9230a6",
      "0x526625f40912ddc0ed48fdae1475ec8b87216156", "0x2ebef43d06628e2f82365c91255c821d168c898c", "0x3782634618fd9cd5582254327498bef1b89f3027",
      "0xcde0aa54a9fc78b43288ac85bac956ccf914e968"}
files = [f for f in sorted(os.listdir(D)) if f.endswith(".json")]
def blocks():
    seen = set()
    for f in files:
        try: d = json.load(open(D + f))
        except Exception: continue
        for k, (ts, tl) in d.items():
            bn = int(k)
            if bn in seen: continue
            seen.add(bn); yield bn, ts, tl
# pass 1: F ring = counterparties of F hubs (plain transfers) within 83285000-83346000
FR = set(FH)
for bn, ts, tl in blocks():
    if 83285000 <= bn <= 83346000:
        for t in tl:
            if t[5] in ("0x", "") and int(t[3]) > 0:
                if t[1] in FH: FR.add(t[2])
                if t[2] in FH: FR.add(t[1])
side = {}
for a in FR: side[a] = "F"
for a in CD: side[a] = "D"
for a in B | BDISP | BSWEEP | B_OCT8 | COPY: side[a] = "B"
for a in A | DISP | SWEEP | A_OCT8: side[a] = "A"
side.pop("0x1343e360bfda648e69d0cbb04da57356a8599f25", None)   # dust spammer mislabeled as an A sweep in pots.json
print("set sizes:", collections.Counter(side.values()))
recv = collections.defaultdict(set); sent = collections.defaultdict(set); direct = collections.Counter(); ex = collections.defaultdict(list); nb = 0
for bn, ts, tl in blocks():
    nb += 1
    for t in tl:
        if not (t[5] in ("0x", "") and int(t[3]) > 0): continue
        sf, st = side.get(t[1]), side.get(t[2])
        if sf and st and sf != st:
            direct[(sf, st)] += 1; ex[(sf, st)].append((bn, t[1], t[2], int(t[3]) / 1e18, t[4]))
        if sf: recv[t[2]].add(sf)
        if st: sent[t[1]].add(st)
print("blocks", nb)
print("direct plain transfers between pots:", dict(direct))
for k, v in ex.items(): print("  ", k, v[:6])
two_in = {a: s for a, s in recv.items() if len(s) > 1}; two_out = {a: s for a, s in sent.items() if len(s) > 1}
print("addresses paid by two pots:", len(two_in)); [print("  ", a, sorted(s), side.get(a)) for a, s in list(two_in.items())[:20]]
print("addresses paying two pots:", len(two_out)); [print("  ", a, sorted(s), side.get(a)) for a, s in list(two_out.items())[:20]]
