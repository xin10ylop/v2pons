#!/usr/bin/env python3
"""opAtiming.py [LINE_JSON]: operator A's crowd line, pool by pool -- is there a timed seat?

Reads lineprobe.py's line file (out/line_rh_0x3194e326_644.json). For each pool:
  wave     the crowd's real buys (crew wallets, 0.005 ETH+): first and last offset, count, ETH in
  pull     the launcher's first liquidity removal (offset)
  gap      blocks from the last crowd buy to the pull: room to sell after the wave
  fee      the pool's fee (v4 Initialize)
  paper    a timed trade: in just before the wave (at the first crowd buy - LEAD blocks, else launch + 2), out right after the last
           crowd buy, or EXIT_BEFORE_PULL blocks before the pull if that comes first; return from the pool's native reserve after each
           swap (full-range v4: price ~ reserve^2), both legs paying the pool fee; a pull before our exit = -100%
  reaction pools where a real outsider (not crew, not launcher, 0.001 ETH+) bought before the wave: did the wave still come, and did the
           pull come sooner than in clean pools?
Read-only (the line file)."""
import sys, json, statistics as st, collections

D = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "out/line_rh_0x3194e326_644.json"))
P = D["pools"]; crew = set(D["crew"])
DUST = {"0xe71a69f434a719cd5afa411568b69716aab3b84a"}           # the chain-wide 2e-6 ETH dust bot
LEAD = int(__import__("os").environ.get("LEAD", "10")); EXIT_BEFORE_PULL = int(__import__("os").environ.get("EBP", "30"))
rows = []
for p in P:
    ev = sorted(p["ev"])                                          # (off, nat, sender, to, sel, txidx, res, txhash)
    real = [e for e in ev if e[2] in crew and e[2] not in DUST and e[1] >= 0.005]
    pull = min((o for o, _ in p["pulls"]), default=None)
    fee = (p.get("fee") or 0) / 1e6
    outs = [e for e in ev if e[2] not in crew and e[2] != p["launcher"] and e[2] not in DUST and e[1] >= 0.001]
    w0 = real[0][0] if real else None; w1 = real[-1][0] if real else None
    early_out = [e for e in outs if w0 is None or e[0] < w0]
    # timed paper: reserve before entry and at exit (native virtual reserve after each swap)
    paper = None
    if real:
        entry = max(2, w0 - LEAD)
        exit_ = w1 + 1
        if pull is not None and pull - EXIT_BEFORE_PULL < exit_:
            exit_ = pull - EXIT_BEFORE_PULL
        if pull is not None and pull <= entry:
            paper = -1.0
        elif exit_ > entry:
            pre = [e for e in ev if e[0] < entry and e[6]]
            post = [e for e in ev if e[0] <= exit_ and e[6]]
            if pre and post and pre[-1][6] and post[-1][6]:
                ratio = (post[-1][6] / pre[-1][6]) ** 2
                paper = ratio * (1 - fee) ** 2 - 1
    rows.append({"id": p["id"], "w0": w0, "w1": w1, "n": len(real), "eth": sum(e[1] for e in real), "pull": pull, "fee": fee,
                 "gap": (pull - w1) if (pull is not None and w1 is not None) else None, "paper": paper,
                 "early_out": [(e[0], round(e[1], 4)) for e in early_out[:3]], "outs": len(outs)})

def med(xs):
    xs = [x for x in xs if x is not None]
    return f"{st.median(xs):g}" if xs else "-"
print(f"{len(rows)} pools; crew {len(crew)}")
print(f"wave start (blocks after launch): median {med([r['w0'] for r in rows])}; wave end: median {med([r['w1'] for r in rows])}; crowd buys per pool: median {med([r['n'] for r in rows])}; crowd ETH per pool: median {med([round(r['eth'],3) for r in rows])}")
print(f"pull: median +{med([r['pull'] for r in rows])}; gap from the last crowd buy to the pull: median {med([r['gap'] for r in rows])} blocks (p10 {sorted([r['gap'] for r in rows if r['gap'] is not None])[len([r for r in rows if r['gap'] is not None])//10] if any(r['gap'] is not None for r in rows) else '-'})")
fees = collections.Counter(round(r["fee"] * 100, 2) for r in rows)
print(f"fees (%): {fees.most_common(8)}")
ps = [r["paper"] for r in rows if r["paper"] is not None]
if ps:
    print(f"timed paper (in at wave start - {LEAD}, out after the wave or {EXIT_BEFORE_PULL} before the pull): n {len(ps)}, mean {st.mean(ps):+.1%}, median {st.median(ps):+.1%}, won {sum(x>0 for x in ps)}, -100% {sum(x<=-1 for x in ps)}")
# reaction
fr = [r for r in rows if r["early_out"]]; cl = [r for r in rows if not r["early_out"] and r["w0"] is not None]
print(f"\nreaction: {len(fr)} pools with a real outsider before the wave, {len(cl)} clean")
if fr:
    print(f"  wave came: {sum(1 for r in fr if r['w0'] is not None)}/{len(fr)} fronted vs {sum(1 for r in rows if not r['early_out'] and r['w0'] is not None)}/{sum(1 for r in rows if not r['early_out'])} clean")
    print(f"  crowd ETH: fronted median {med([round(r['eth'],3) for r in fr])} vs clean {med([round(r['eth'],3) for r in cl])}")
    print(f"  pull: fronted median +{med([r['pull'] for r in fr])} vs clean +{med([r['pull'] for r in cl])}")
    fp = [r['paper'] for r in fr if r['paper'] is not None]; cp = [r['paper'] for r in cl if r['paper'] is not None]
    if fp and cp:
        print(f"  timed paper: fronted mean {st.mean(fp):+.1%} (n {len(fp)}) vs clean {st.mean(cp):+.1%} (n {len(cp)})")
    for r in fr[:15]:
        print(f"    {r['id'][:14]} outsider {r['early_out']} -> wave {r['w0']}..{r['w1']} ({r['n']} buys, {r['eth']:.3f} ETH), pull +{r['pull']}, fee {r['fee']:.2%}, paper {r['paper'] if r['paper'] is None else format(r['paper'], '+.1%')}")
