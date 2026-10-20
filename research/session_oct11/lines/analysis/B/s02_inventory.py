"""Inventory of angle-B v4 pools: families by lc and tok (>= 10 launches), with their cross-keys, quote, fee/ts, hooks, target, selector, clen."""
import json, collections as C, os
D = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(D, "b_pools.jsonl"))]
def top(c, k=3): return ", ".join(f"{a} x{b}" for a, b in c.most_common(k))
for g in ("lc", "tok"):
    fam = C.defaultdict(list)
    for r in rows: fam[(r["fam"].get(g) or "none")].append(r)
    print(f"=== grouping {g}: {sum(1 for v in fam.values() if len(v)>=10)} families >= 10, pools in them {sum(len(v) for v in fam.values() if len(v)>=10)} of {len(rows)}")
    for k, v in sorted(fam.items(), key=lambda kv: -len(kv[1])):
        if len(v) < 10: continue
        other = "tok" if g == "lc" else "lc"
        c = lambda f: C.Counter(f(r) for r in v)
        print(f"{g}:{k[:8]}{('|'+k.split('|')[1]) if '|' in k else ''} n={len(v)} inA={sum(r['in_A'] for r in v)} frb={sum(1 for r in v if r['frb'])} pulled={sum(1 for r in v if r['n_pulls'])}")
        print("   ", other, top(c(lambda r: (r['fam'].get(other) or 'none')[:8] + (('|'+r['fam'][other].split('|')[1]) if other=='lc' and r['fam'].get(other) and '|' in r['fam'][other] else '')), 4))
        print("    quote", top(c(lambda r: r['quote'])), "| fee/ts", top(c(lambda r: f"{r['fee']}/{r['tick_spacing']}")), "| hooks", top(c(lambda r: r['hooks'][:10]), 2))
        print("    to:sel:clen", top(c(lambda r: f"{(r['launch']['to'] or 'create')[:10]}:{r['launch']['selector']}:{r['launch']['calldata_len']}"), 4), "| value", top(c(lambda r: r['launch']['value_eth']), 3))
