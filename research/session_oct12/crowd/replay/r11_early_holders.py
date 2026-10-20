"""The small buyers who already hold before the crowd (r06 'before'): who sends them (EOAs per contract), and whether pools with an
outside holder early (by + 10) differ in what the rule depends on (the crowd's first real buy by + 78/+ 80, the first pull, the replay's
return). A crude look at 'does the operator react to a holder', from the chain alone (no position of ours was ever on chain)."""
from common import *
import collections, statistics as stt
D = json.load(open(J("r06_rows.json"))); R = D["rows"]
who = collections.defaultdict(collections.Counter)
for r in R:
    for b in r["before"]: who[((b[2] or "")[:10], b[3])][b[1]] += 1
for k, c in sorted(who.items(), key=lambda kv: -sum(kv[1].values()))[:6]:
    print(f"{k}: {sum(c.values())} buys from {len(c)} senders; top {c.most_common(3)}")
def grp(lab, f):
    a = [r for r in R if f(r)]; b = [r for r in R if not f(r)]
    for nm, g in ((lab, a), ("not " + lab, b)):
        if not g: continue
        c78 = sum(1 for r in g if r["crowd1_off"] is not None and r["crowd1_off"] <= 80) / len(g)
        po = [r["burn_off"] for r in g if r["burn_off"] is not None]
        print(f"  {nm:<46} n {len(g):>3}: crowd by +80 {c78:.2f}; crowd's 1st median {stt.median([r['crowd1_off'] for r in g if r['crowd1_off'] is not None]):.0f}; "
              f"pull median {stt.median(po):.0f}, by +150 {sum(1 for p in po if p <= 150) / len(g):.2f}; replay 0.0058|2|2 mean {stt.mean(r['r']['0.0058|2|2']['ret'] for r in g)*100:+.2f}% median {stt.median(r['r']['0.0058|2|2']['ret'] for r in g)*100:+.3f}%")
print("pools with / without an early holder:")
grp("0x570759db dust buy at +1", lambda r: any(b[2] and b[2].startswith("0x570759db") and b[0] <= 2 for b in r["before"]))
grp("any non-crowd buy >= 0.001 ETH by +10", lambda r: any(not b[5] and b[4] >= 0.001 and b[0] <= 10 for b in r["before"]))
grp("any non-crowd buy >= 0.001 ETH by +40", lambda r: any(not b[5] and b[4] >= 0.001 and b[0] <= 40 for b in r["before"]))
grp("non-crowd buys >= 0.003 ETH total by +60", lambda r: sum(b[4] for b in r["before"] if not b[5] and b[0] <= 60) >= 0.003)
