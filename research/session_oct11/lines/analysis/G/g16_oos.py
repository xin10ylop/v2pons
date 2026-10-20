"""how the out-of-sample selections did across all 123 families: F (picked on days 1-5, all fit slices positive) on days 6-7, W (picked on days
1-6) on day 7"""
from common import *
r = json.load(open(os.path.join(G, "g06_results_q0.0058.json")))
F = [o for o in r if o["F"]]; W = [o for o in r if o["W"]]
fpos = [o for o in F if o["F"]["val"]["n"] and o["F"]["val"]["mean"] > 0]
wpos = [o for o in W if o["W"]["last24"]["n"] and o["W"]["last24"]["mean"] > 0]
print(f"F: families with a pick {len(F)}; positive on days 6-7 {len(fpos)}; sum of validated $/day {sum(o['F']['val_usd_day'] for o in F):.0f}")
print(f"W: families with a pick {len(W)}; positive on day 7 {len(wpos)} of {sum(1 for o in W if o['W']['last24']['n'])} with trades; sum of day-7 $ {sum(o['W']['last24_usd_day'] for o in W):.0f}")
for o in sorted(F, key=lambda o: -o["F"]["val_usd_day"])[:12]:
    print(f"  F {o['fam'][:90]:90s} {o['F']['rule']:20s} fit {o['F']['fit']['mean']*100:+.1f}% val {o['F']['val'].get('mean', 0)*100:+.1f}% (n {o['F']['val']['n']}) ${o['F']['val_usd_day']:.0f}/day")
