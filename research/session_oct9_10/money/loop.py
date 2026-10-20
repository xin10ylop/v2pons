"""the operator's money loop from the plain transfers: sweeps (many in -> one ~7 ETH out), dispatchers (one ~7 ETH in -> many out),
which launch each dispatcher funds and which pull each sweep collects; chains of launches; money in and out of the loop"""
import json, glob, collections, sys
T = {}
for f in sorted(glob.glob("part*.jsonl")) + ["win.jsonl"]:
    for line in open(f):
        bn, h, fr, to, v, nonce = json.loads(line); T[h] = (bn, h, fr, to, v, nonce)
T = sorted(T.values())
L = json.load(open("launches_now.json")); dep = {x["deployer"]: x for x in L}
inc = collections.defaultdict(list); out = collections.defaultdict(list)
for t in T:
    inc[t[3]].append(t); out[t[2]].append(t)
E = 1e18
# dispatchers: >= 20 outgoing within 150 blocks starting at nonce 0
disp = {a: o for a, o in out.items() if len(o) >= 20 and o[0][5] == 0}
# sweeps: >= 15 incoming, then an outgoing at nonce 0 of >= 5 ETH
sweeps = {a: (inc[a], o) for a, o in out.items() if o and o[0][5] == 0 and o[0][4] >= 4 * E and len(inc[a]) >= 15}
print(f"{len(T)} plain transfers; {len(L)} launches; dispatchers {len(disp)}; sweeps {len(sweeps)}")
crowd = collections.Counter()
for a, o in disp.items():
    for t in o[1:]: crowd[t[3]] += 1
CROWD = {a for a, n in crowd.items() if n >= max(3, len(disp) // 2)}
print("crowd wallets refilled by most dispatchers:", len(CROWD))
# launch funded by each dispatcher; launch collected by each sweep
funded = {}; collected = {}
for a, o in disp.items():
    first = o[0]
    funded[a] = (first[3], first[4], first[0], dep.get(first[3], {}).get("block"))
for s, (i, o) in sweeps.items():
    froms = [t for t in i if t[2] in dep]
    collected[s] = ([(t[2], t[4], dep[t[2]]["pull"]) for t in froms], o[0][3], o[0][4], len(i), sum(t[4] for t in i))
# chains: launch(pulled) -> sweep -> dispatcher -> launch(funded)
nxt = {}
for s, (froms, d, v, n, tot) in collected.items():
    for (dp, vv, pull) in froms:
        if d in funded: nxt[dp] = (s, d, funded[d][0])
fund_of = {}
for d, (to, v, bn, lb) in funded.items(): fund_of[to] = (d, v, bn)
starts = [x["deployer"] for x in L if x["deployer"] not in {v[2] for v in nxt.values()}]
print("\nlaunch deployers NOT funded by a loop dispatcher (chain starts / outside money):")
for d in starts:
    x = dep[d]
    src = inc.get(d, [])
    print(f"   {x['block']} fee {x['fee']:5d} deployer {d[:10]} funded by: " + ", ".join(f"{t[2][:10]} {t[4]/E:.3f} ETH (blk {t[0]})" for t in src[:3]))
chains = []; seen = set()
for d in starts:
    c = [d]; cur = d
    while cur in nxt and nxt[cur][2] not in seen:
        cur = nxt[cur][2]; c.append(cur); seen.add(cur)
    chains.append(c)
print(f"\n{len(chains)} chains (pots):")
for c in chains:
    print("   " + " -> ".join((f"{dep[d]['block']}/{dep[d]['fee']}" if d in dep else "OTHER:" + d[:10]) for d in c))
# money in/out of the loop: sweeps' totals vs dispatchers' sends
print("\nsweeps (collected, ETH):", sorted(round(v[4] / E, 3) for v in collected.values()))
print("dispatchers (received, ETH):", sorted(round(sum(t[4] for t in inc[a]) / E, 3) for a in disp))
leak = [(s, v[1]) for s, v in collected.items() if v[1] not in disp]
print("sweeps whose 7 ETH did not go to a dispatcher in the scan:", [(s[:10], d[:10]) for s, d in leak])
json.dump({"chains": chains, "crowd": sorted(CROWD), "disp": list(disp), "sweeps": list(sweeps)}, open("loop.json", "w"))

# the two pots: crowd sets refilled by 7.0x vs 4.85x dispatchers, and any overlap between them
pot = lambda a: "A(7.01)" if sum(t[4] for t in inc[a]) > 6 * E else "B(4.86)"
crowd_by = collections.defaultdict(collections.Counter)
for a, o in disp.items():
    for t in o[1:]: crowd_by[pot(a)][t[3]] += 1
for k, c in crowd_by.items(): print(f"pot {k}: {sum(1 for a in disp if pot(a) == k)} dispatchers, {len(c)} crowd wallets refilled")
ks = list(crowd_by)
if len(ks) == 2:
    both = set(crowd_by[ks[0]]) & set(crowd_by[ks[1]]); print("crowd wallets refilled by BOTH pots:", len(both), [x[:10] for x in list(both)[:5]])
# sweeps: inputs from which pot's crowd
for s_, (froms, d, v, n, tot) in collected.items():
    pass
mix = []
for s_ in sweeps:
    srcs = {t[2] for t in inc[s_]}
    a_ = len(srcs & set(crowd_by.get("A(7.01)", {}))); b_ = len(srcs & set(crowd_by.get("B(4.86)", {})))
    if a_ and b_: mix.append((s_[:10], a_, b_))
print("sweeps fed by both crowds:", mix)
# chains with pot labels
for c in chains:
    d0 = fund_of.get(c[0], (None,))[0]
    print("  chain", len(c), "launches, first funded by", (d0 or "?")[:10], pot(d0) if d0 in disp else "")
