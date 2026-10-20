"""S07: the reaction. Launches where an outsider (not the launch wallet) bought before the launcher's own first buy: did the launcher still buy
(size, offset), and was the pool pulled sooner? Two samples: (1) the fresh 50 h (s02) and (2) the census of Oct 4-11 (analyst C's pickles,
read-only, in the session scratchpad: v23.pkl rows with swaps12 = the first 12 swaps with their senders; ev.pkl = every pool event)."""
import sys, os, pickle, statistics as st
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scommon import *
from s04_shapes import line_shape
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/analysis/C"
out = []
def P(s=""): out.append(s)
def q(xs):
    xs = sorted(xs)
    return f"n {len(xs)} p10/50/90 {xs[int(.1 * (len(xs) - 1))]}/{xs[len(xs) // 2]}/{xs[int(.9 * (len(xs) - 1))]}" if xs else "n 0"
# (1) fresh
D, R = load(); LR = [r for r in R if line_shape(r)]
pre = [(r, [s for s in r["swaps"] if s["dir"] == "B" and not s["by_lw"] and (not r["own1"] or s["off"] < r["own1"]["off"])]) for r in LR]
pre = [(r, p) for r, p in pre if p]
P(f"(1) fresh 50 h, {len(LR)} line launches: outsider buy before the launcher's own first buy in {len(pre)}")
for r, p in pre: P(f"   {r['lb']} outsiders {[(s['off'], round(s['eth'], 5), s['from'][:10]) for s in p]} own1 {r['own1']['off'] if r['own1'] else None} pull {r['pull1']['off'] if r['pull1'] else None}")
# (2) census
sys.path.insert(0, CEN)
import fams
fams.OUT = CEN
RC = fams.load_rows(); FP = fams.fam_pools(RC); rs = [r for r in FP["lc:0a493d1a|13ead562"] if r["fee"] == 100 and r["quote"] == "WETH"]
P(f"\n(2) census Oct 4-11: lc:0a493d1a|13ead562 fee 100 WETH launches: {len(rs)}")
cases, base = [], []
for r in rs:
    lw = r["launch"]["from"]; sw = r["swaps12"]
    own = next((s for s in sw if s[1] == "B" and s[3] == lw), None)
    out_pre = [s for s in sw if s[1] == "B" and s[3] != lw and (own is None or s[0] < own[0])]
    rec = (r, own, out_pre)
    (cases if out_pre else base).append(rec)
P(f"   with an outsider buy before the launcher's first buy (within the first 12 swaps): {len(cases)}; without: {len(base)}")
P(f"   launcher bought afterwards: {sum(1 for r, o, p in cases if o)}/{len(cases)}  vs baseline {sum(1 for r, o, p in base if o)}/{len(base)}")
P(f"   own first buy size, cases {Counter(round(o[2], 4) for r, o, p in cases if o).most_common(5)}  baseline {Counter(round(o[2], 4) for r, o, p in base if o).most_common(5)}")
P(f"   own first buy offset, cases {q([o[0] for r, o, p in cases if o])}  baseline {q([o[0] for r, o, p in base if o])}")
P(f"   pulled (any time in the census window): cases {sum(1 for r, o, p in cases if r['first_pull_off'] is not None)}/{len(cases)}  baseline {sum(1 for r, o, p in base if r['first_pull_off'] is not None)}/{len(base)}")
P(f"   pull offset, cases {q([r['first_pull_off'] for r, o, p in cases if r['first_pull_off'] is not None])}  baseline {q([r['first_pull_off'] for r, o, p in base if r['first_pull_off'] is not None])}")
P(f"   pull - first outsider buy, cases {q([r['first_pull_off'] - p[0][0] for r, o, p in cases if r['first_pull_off'] is not None])}")
P(f"   outsider senders/routes: {Counter((p[0][3][:10], p[0][5]) for r, o, p in cases).most_common(8)}")
P(f"   outsider first buy offset vs mint: {q([p[0][0] - (r['liq_off'] or 0) for r, o, p in cases])}; size ETH {q([round(p[0][2], 5) for r, o, p in cases])}")
P("   every case: launch block, day, wallet, mint, outsider buys before the own buy (off, ETH, sender, sel), own first buy (off, ETH), pull off, n launches of that wallet")
nw = Counter(r["launch"]["from"] for r in rs)
for r, o, p in cases:
    P(f"     {r['launch_block']} {r['launch_utc'][5:16]} {r['launch']['from'][:10]} (x{nw[r['launch']['from']]}) mint +{r['liq_off']} outsiders {[(s[0], round(s[2], 5), s[3][:10], s[5]) for s in p]} "
      f"own {(o[0], round(o[2], 4)) if o else None} pull {r['first_pull_off']}")
# the same wallet's other launches (paired): same wallet, launches without an early outsider
P("\n   paired by wallet (a wallet with both kinds of launch): own buy / pull offset, with vs without an early outsider")
for w in sorted({r["launch"]["from"] for r, o, p in cases}):
    a = [(o[0] if o else None, round(o[2], 3) if o else None, r["first_pull_off"]) for r, o, p in cases if r["launch"]["from"] == w]
    b = [(o[0] if o else None, round(o[2], 3) if o else None, r["first_pull_off"]) for r, o, p in base if r["launch"]["from"] == w]
    if b: P(f"     {w[:10]}: with {a}  without {b[:12]}{' ...' if len(b) > 12 else ''}")
open(os.path.join(OUT, "s07_reaction.out"), "w").write("\n".join(out) + "\n"); print("\n".join(out))
