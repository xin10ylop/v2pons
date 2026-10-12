"""S03: one row per WETH-side 13ead562 launch of the last 50 h: launch block/time/wallet, the mint (offset, L, range, by whom, via),
the launcher's own buys (offset, ETH, minOut, route), every other swap to +400 (offset, who, direction, ETH, route), pulls (Burn with L > 0:
offset, by whom, call). -> s03_table.out"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scommon import *
D, R = load(); th = json.load(open(os.path.join(OUT, "s01_launches.json")))["t_head"]
out = []
def P(s): out.append(s)
P(f"head {D['head']} (s02); launches listed {len(R)} (WETH side, 13ead562 to the NonfungiblePositionManager); window per pool to +{D['win']}")
P("non-WETH 13ead562 pool creations in the same 50 h (not this line): " + str(sum(1 for x in json.load(open(os.path.join(OUT, 's01_launches.json')))['launches'] if x['qs'] is None)))
for r in R:
    age = (th - r["ts"]) / 3600
    P(f"\n#{r['lb']} {time.strftime('%m-%d %H:%M:%S', time.gmtime(r['ts']))} ({age:.1f} h ago) fee {r['fee']} wallet {r['lw']} nonce {r['nonce']} WETH=token{r['qs']} pool {r['pool']}")
    for m in r["mints"]:
        P(f"   mint +{m['off']} L {m['L']:.4g} ticks [{m['lo']},{m['hi']}] amount0 {m['a0']:.4g} amount1 {m['a1']:.4g} by {'launch wallet' if m['by_lw'] else m['from']} via {m['to'][:10]}:{m['sel']}")
    for s in r["swaps"]:
        if s["off"] > 400: continue
        who = "LAUNCHER" if s["by_lw"] else (s["from"] or "?")
        mo = "" if s.get("min_out") is None else f" minOut {s['min_out']}"
        P(f"   swap +{s['off']} {s['dir']} {s['eth']:.5f} ETH by {who} via {(s.get('to') or '?')[:10]}:{s.get('sel')}/{s.get('len')} value {s.get('value')}{mo}")
    n4 = sum(1 for s in r["swaps"] if s["off"] > 400)
    if n4: P(f"   ({n4} more swaps after +400 to +{r['ev_to'] - r['lb']})")
    for b in r["burns"]:
        P(f"   burn +{b['off']} L {b['L']:.4g} by {'launch wallet' if b['by_lw'] else b['from']} call {b['sel']}{'  <- PULL' if b['L'] > 0 else ' (fee poke)'}")
    if not r["burns"]: P(f"   no burn to +{r['ev_to'] - r['lb']}")
open(os.path.join(OUT, "s03_table.out"), "w").write("\n".join(out) + "\n"); print("\n".join(out[:3])); print(len(out), "lines")
