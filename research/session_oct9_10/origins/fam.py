"""Pot wallets of each crowd family (A, B) from the cached plain transfers, and every cross-family plain transfer / shared counterparty."""
import json, pickle, collections, time
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/"
V = pickle.load(open(D + "origins/vt.pkl", "rb")); TX = V["tx"]
b = json.load(open(D + "ops/b_list.json")); CA = set(b["A"]); CB = set(b["B"])
E = 1e18
P = [t for t in TX if t[7] in ("0x", "") and t[5] > 0]
inc = collections.defaultdict(list); out = collections.defaultdict(list)
for t in P: inc[t[4]].append(t); out[t[3]].append(t)
def utc(ts): return time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))
fam = {a: "A" for a in CA}; fam.update({a: "B" for a in CB})
role = {}
# sweeps and dispatchers: >=5 distinct crowd-F counterparties within 300 blocks
def groups(lst, key):
    lst = sorted(lst); res = []
    for t in lst:
        if res and t[0] - res[-1][-1][0] <= 300: res[-1].append(t)
        else: res.append([t])
    return res
changed = True; rounds = 0
while changed and rounds < 6:
    changed = False; rounds += 1
    for F, C in (("A", CA), ("B", CB)):
        for x, ins in inc.items():
            if x in fam: continue
            for g in groups(ins, 0):
                n = len({t[3] for t in g if t[3] in C})
                if n >= 5: fam[x] = F; role[x] = "sweep"; changed = True; break
        for x, os_ in out.items():
            if x in fam: continue
            for g in groups(os_, 0):
                n = len({t[4] for t in g if t[4] in C})
                if n >= 5: fam[x] = F; role[x] = "disp"; changed = True; break
    # capital edges: dispatcher's first out (launch wallet), sweep's first big out, senders of >0.3 ETH into sweeps (payouts)
    for x in list(fam):
        r = role.get(x)
        if r == "disp":
            o = sorted(out[x])
            if o and o[0][4] not in fam: fam[o[0][4]] = fam[x]; role[o[0][4]] = "launchw"; changed = True
        if r == "sweep":
            big = [t for t in sorted(out[x]) if t[5] > 1 * E]
            if big and big[0][4] not in fam: fam[big[0][4]] = fam[x]; role[big[0][4]] = "sweep_next"; changed = True
            for t in inc[x]:
                if t[5] > 0.3 * E and t[3] not in fam: fam[t[3]] = fam[x]; role[t[3]] = "payer"; changed = True
print("rounds", rounds, collections.Counter((fam[x], role.get(x, "crowd")) for x in fam))
# cross-family plain transfers
cross = [t for t in P if t[3] in fam and t[4] in fam and fam[t[3]] != fam[t[4]]]
print("\nplain transfers between A-family and B-family wallets:", len(cross))
for t in cross[:50]: print("  ", t[0], utc(t[1]), t[3], fam[t[3]], role.get(t[3], "crowd"), "->", t[4], fam[t[4]], role.get(t[4], "crowd"), round(t[5] / E, 5), "nonce", t[6])
# shared counterparties: non-family addresses with plain transfers with both families
cp = collections.defaultdict(lambda: {"A": [], "B": []})
for t in P:
    a, c = t[3], t[4]
    if a in fam and c not in fam: cp[c][fam[a]].append(("out_to", t))
    if c in fam and a not in fam: cp[a][fam[c]].append(("in_from", t))
both = {x: v for x, v in cp.items() if v["A"] and v["B"]}
print("\nnon-family addresses transacting (plain ETH) with BOTH families:", len(both))
for x, v in sorted(both.items(), key=lambda kv: -len(kv[1]["A"]) - len(kv[1]["B"]))[:40]:
    def s(lst): return "; ".join(f"{d} {t[3][:10] if d=='in_from' else t[4][:10]} {t[5]/E:.4f} blk {t[0]}" for d, t in lst[:3])
    print("  ", x, "A:", len(v["A"]), s(v["A"]), "| B:", len(v["B"]), s(v["B"]))
pickle.dump({"fam": fam, "role": role}, open(D + "origins/fam.pkl", "wb"))
# B non-family counterparties summary (inflows / outflows), excluding launcher contracts
print("\nB family: plain inflows from non-family senders (>0.001 ETH):")
rows = []
for t in P:
    if t[4] in fam and fam[t[4]] == "B" and t[3] not in fam and t[5] > 1e15: rows.append(t)
for t in rows[:80]: print("  ", t[0], utc(t[1]), t[3], "->", t[4], role.get(t[4], "crowd"), round(t[5] / E, 5), "sender nonce", t[6])
print(len(rows))
print("\nB family: plain outflows to non-family (>0.001 ETH):")
rows = []
for t in P:
    if t[3] in fam and fam[t[3]] == "B" and t[4] not in fam and t[5] > 1e15: rows.append(t)
for t in rows[:80]: print("  ", t[0], utc(t[1]), t[3], role.get(t[3], "crowd"), "->", t[4], round(t[5] / E, 5), "nonce", t[6])
print(len(rows))
