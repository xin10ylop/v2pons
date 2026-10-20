"""cache-only attribution of every launch Oct 8 05:00 -> Oct 9 11:20 to a pot by the deployer's funder (A dispatcher refills crowd A, B refills crowd B, F hubs)"""
from vlib import touching, cached
import json, sys
S = '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/'
sys.path.insert(0, S + 'ops2')
from labels import A, B
FH = {"0x0f77ceece905c99200cb9f12b7e993a57ac7abb7","0x107b31ad7c9d2eb3d4f05af97b40345efc6b64df","0x24bc5f3cee26fe0666db054d5da4d11c8abba9a3","0x295c7408cf66c6070340588f5f0a23b8722ce670","0xf8c511f8de7f0f3d34a1fa3e0f9087f023084955","0xd4b94999f319d423b479f149b427e9593ebb2ad3","0x5477a0daa7e8510ade3822bc5b7d78cc31494b1c","0x92b66c43b3f27c258877847c8c420e554daf4fd1","0xc43b385aa2e3e0fba6dc0929a483da160d9230a6","0x526625f40912ddc0ed48fdae1475ec8b87216156","0x2ebef43d06628e2f82365c91255c821d168c898c","0x3782634618fd9cd5582254327498bef1b89f3027","0xcde0aa54a9fc78b43288ac85bac956ccf914e968"}
d = json.load(open(S + 'ops/launcher_txs.json'))
def classify(f, fb, depth=0):
    o = [y for y in touching([f], fb - 5, fb + 150, fetch=False) if y[2] == f]
    nA = sum(1 for y in o if y[3] in A); nB = sum(1 for y in o if y[3] in B)
    if f in FH: return 'F'
    if nA >= 10: return 'A'
    if nB >= 10: return 'B'
    if depth < 2:
        r = [y for y in touching([f], fb - 600, fb, fetch=False) if y[3] == f]
        if r: return classify(r[0][2], r[0][0], depth + 1)
    return '?'
tot = {}
for x in sorted([x for x in d.values() if x['bn'] >= 83050000], key=lambda x: x['bn']):
    dep = x['from']; b = x['bn']
    if x['nonce'] != 0: k = 'relaunch(F)'
    else:
        r = [y for y in touching([dep], b - 3000, b, fetch=False) if y[3] == dep]
        k = classify(r[0][2], r[0][0]) if r else 'uncached'
    day = 'Oct9' if b >= 83717000 else 'Oct8'
    tot[(day, k)] = tot.get((day, k), 0) + 1
    print(b, day, dep, k)
print(sorted(tot.items()))
