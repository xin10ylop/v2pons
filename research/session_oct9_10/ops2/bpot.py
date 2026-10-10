"""B-pot (4.86 ETH) dispatchers and sweeps in the local plain-transfer windows (money/part*.jsonl + win.jsonl): inputs, outputs, labels."""
import json, glob, collections
M = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/money/"
T = {}
for f in sorted(glob.glob(M + "part*.jsonl")) + [M + "win.jsonl"]:
    for line in open(f):
        try: bn, h, fr, to, v, nonce = json.loads(line)
        except Exception: continue
        T[h] = (bn, h, fr, to, v, nonce)
T = sorted(T.values())
b = json.load(open('../ops/b_list.json')); B = set(b['B']); A = set(b['A'])
L = json.load(open(M + "launches_now.json")); dep = {x["deployer"]: x for x in L}
lab = {w: '[B]' for w in B}; lab.update({w: '[A]' for w in A})
for d, x in dep.items(): lab[d] = "[DEP %d fee %d]" % (x["block"], x["fee"])
inc = collections.defaultdict(list); out = collections.defaultdict(list)
for t in T: inc[t[3]].append(t); out[t[2]].append(t)
E = 1e18
disp = {a: o for a, o in out.items() if len(o) >= 20 and o[0][5] == 0}
Bd = [a for a in disp if 4 * E < sum(t[4] for t in inc[a]) < 6 * E]
def s(t): return f"{t[0]} {t[2]} {lab.get(t[2],'')} -> {t[3]} {lab.get(t[3],'')} {t[4]/E:.5f} n{t[5]} {t[1][:14]}"
for a in sorted(Bd, key=lambda a: out[a][0][0]):
    print("=== B dispatcher", a)
    for t in inc[a]: print("  IN ", s(t))
    o = out[a]; print("  OUT first:", s(o[0])); print("  OUT to B wallets:", sum(1 for t in o if t[3] in B), "to A wallets:", sum(1 for t in o if t[3] in A), "other:", [s(t) for t in o[1:] if t[3] not in B])
    sw = inc[a][0][2]
    ii = inc[sw]
    print("  its sweep", sw, "inputs:", len(ii), "from B:", sum(1 for t in ii if t[2] in B), "from A:", sum(1 for t in ii if t[2] in A), "total %.4f" % (sum(t[4] for t in ii) / E))
    for t in ii:
        if t[2] not in B: print("     non-B input:", s(t))
    print("  sweep outs:", [s(t) for t in out[sw]])
# any plain transfer between B-side and A-side addresses in the windows
Bside = set(B) | set(Bd) | {inc[a][0][2] for a in Bd}
Aside = set(A) | {a for a in disp if a not in Bd}
x = [t for t in T if (t[2] in Bside and t[3] in Aside) or (t[2] in Aside and t[3] in Bside)]
print("\nplain transfers between B-side and A-side addresses in windows:", len(x)); [print("  ", s(t)) for t in x[:20]]
print("window blocks covered: from", T[0][0], "to", T[-1][0], "transfers", len(T))
