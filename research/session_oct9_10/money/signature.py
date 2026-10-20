"""the loop fingerprint over every plain transfer collected so far: SWEEPS (fresh wallet: >= 15 transfers in within 60 blocks, then one
transfer out at nonce 0 carrying >= 90% of it) and DISPATCHERS (fresh wallet: one big transfer in, then >= 15 transfers out within 120 blocks,
starting at nonce 0); each classified by whose wallets it touches (loop A crowd, loop B crowd, or neither)"""
import json, glob, collections
T = {}
files = sorted(glob.glob("part*.jsonl")) + ["win.jsonl"]
for f in files:
    for line in open(f):
        bn, h, fr, to, v, nonce = json.loads(line); T[h] = (bn, h, fr, to, v, nonce)
T = sorted(T.values()); E = 1e18
inc = collections.defaultdict(list); out = collections.defaultdict(list)
for t in T: inc[t[3]].append(t); out[t[2]].append(t)
P = json.load(open("pots.json"))["pots"]; A = set(P["A_7.01"]["crowd"]); B = set(P["B_4.86"]["crowd"])
blocks_covered = len({t[0] for t in T})
print(f"{len(T)} plain transfers from {len(files)} scan files (~{blocks_covered} blocks with at least one)")
def side(addrs):
    a = len(addrs & A); b = len(addrs & B)
    return "loop A" if a and not b else ("loop B" if b and not a else ("A and B!" if a and b else "OTHER"))
sweeps = []; disps = []
for w, o in out.items():
    if not o or o[0][5] != 0: continue
    i = [t for t in inc[w] if t[0] <= o[0][0]]
    if len(i) >= 15 and i[-1][0] - i[0][0] <= 60 and o[0][4] >= 0.9 * sum(t[4] for t in i) and o[0][4] > 0.5 * E:
        sweeps.append((w, len(i), sum(t[4] for t in i) / E, o[0][3], side({t[2] for t in i}), o[0][0]))
    if len(o) >= 15 and o[min(14, len(o) - 1)][0] - o[0][0] <= 120 and inc[w] and inc[w][0][4] > 0.5 * E:
        disps.append((w, len(o), inc[w][0][4] / E, o[0][3], o[0][4] / E, side({t[3] for t in o[1:]}), o[0][0]))
print(f"\nsweeps: {len(sweeps)}  by side: {collections.Counter(s[4] for s in sweeps)}")
print(f"dispatchers: {len(disps)}  by side: {collections.Counter(d[5] for d in disps)}")
for s in sweeps:
    if s[4] == "OTHER": print("  OTHER sweep", s)
for d in disps:
    if d[5] == "OTHER": print("  OTHER dispatcher", d)
