"""Rebuild loop A from scanned value>0 txs: dispatchers (>=10 plain outs to crowd), sweeps (>=10 plain ins from crowd), launch wallets
(non-crowd recipients of dispatchers); flag every plain transfer between a loop wallet and an outside address.
Usage: analyze.py file.jsonl [file2.jsonl ...]"""
import sys, json, collections, time
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins/"
E = 1e18
S = json.load(open(D + "state_now.json"))["sets"]
C = set(S["crowdA"])
T = {}
for fn in sys.argv[1:]:
    for l in open(fn):
        r = json.loads(l); T[r[2]] = r
T = sorted(T.values(), key=lambda r: (r[0], r[6]))
plain = [r for r in T if r[7] in ("0x", "")]
utc = lambda ts: time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))
outs = collections.defaultdict(list); ins = collections.defaultdict(list)
for r in plain: outs[r[3]].append(r); ins[r[4]].append(r)
disp = {a: o for a, o in outs.items() if sum(1 for r in o if r[4] in C) >= 10 and a not in C}
sweeps = {a: i for a, i in ins.items() if sum(1 for r in i if r[3] in C) >= 10 and a not in C}
launchw = set()
for a, o in disp.items():
    for r in o:
        if r[4] not in C: launchw.add(r[4])
LOOP = C | set(disp) | set(sweeps) | launchw
print(f"{len(T)} value txs, {len(plain)} plain; dispatchers {len(disp)}, sweeps {len(sweeps)}, launch wallets {len(launchw)}")
# events in time order
ev = []
for a, i in sweeps.items():
    cin = [r for r in i if r[3] in C]; oin = [r for r in i if r[3] not in C]
    o = outs.get(a, [])
    ev.append((min(r[0] for r in i), "SWEEP", a, f"crowd in {len(cin)} = {sum(int(r[5]) for r in cin)/E:.4f}; other in " +
               ", ".join(f"{r[3][:10]}{'(LW)' if r[3] in launchw else '(OUTSIDE)'} {int(r[5])/E:.4f} n{r[6]}" for r in oin) +
               f"; total {sum(int(r[5]) for r in i)/E:.4f}; out " + ", ".join(f"{r[4][:10]}{'' if r[4] in LOOP else '(OUTSIDE)'} {int(r[5])/E:.4f} n{r[6]}" for r in o)))
for a, o in disp.items():
    i = ins.get(a, [])
    lw = [r for r in o if r[4] not in C]; co = [r for r in o if r[4] in C]
    ev.append((o[0][0], "DISP", a, "in " + ", ".join(f"{r[3][:10]}{'' if r[3] in LOOP else '(OUTSIDE)'} {int(r[5])/E:.4f} n{r[6]}" for r in i) +
               f"; to launch/other " + ", ".join(f"{r[4][:10]} {int(r[5])/E:.4f} n{r[6]}" for r in lw) + f"; crowd refills {len(co)} = {sum(int(r[5]) for r in co)/E:.4f}"))
for t in sorted(ev):
    print(t[0], utc(next(r[1] for r in T if r[0] >= t[0])), t[1], t[2], t[3])
print("\nplain transfers crossing the loop boundary (loop = crowd + dispatchers + sweeps + launch wallets):")
for r in plain:
    a, b = r[3] in LOOP, r[4] in LOOP
    if a != b: print("  ", r[0], utc(r[1]), r[3], "(loop)" if a else "", "->", r[4], "(loop)" if b else "", f"{int(r[5])/E:.6f}", "n", r[6], r[2])
print("\nlaunch wallets' calls with value (launch / buys):")
for r in T:
    if r[3] in launchw and r[7] not in ("0x", ""): print("  ", r[0], utc(r[1]), r[3][:10], "->", r[4][:10], f"{int(r[5])/E:.4f}", r[7], "n", r[6])
json.dump({"disp": sorted(disp), "sweeps": sorted(sweeps), "launchw": sorted(launchw)}, open(D + "analyze_last.json", "w"))
