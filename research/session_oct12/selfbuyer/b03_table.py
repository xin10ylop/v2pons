"""B03: one block per WETH-side 13ead562 launch of the b01 window (newest last): time, wallet, nonce, fee, line shape, the mint(s), the dEaD
transfer, the launcher's own buys, every other swap to +400, the pulls. -> b03_table.out"""
from bc import *
M, RR = load(); TH = M["t_head"]
out = [f"head {M['head']} {ts(TH)} UTC; WETH-side 13ead562 launches {len(RR)}, line shape {sum(r['line'] for r in RR)}"]
def P(s): out.append(s)
for r in RR:
    P(f"\n#{r['lb']} {ts(r['ts'])} ({(TH - r['ts']) / 3600:.1f} h ago) fee {r['fee']} {'LINE' if r['line'] else 'not-line'} wallet {r['lw']} nonce {r['nonce']} "
      f"WETH=token{r['qs']} pool {r['pool']} token {r['token']}")
    for m in r["mints"]:
        P(f"   mint +{m['off']} L {m['L']:.4g} [{m['lo']},{m['hi']}] a0 {m['a0']:.4g} a1 {m['a1']:.4g} by {'LW' if m['by_lw'] else m['from']} via {(m['to'] or '?')[:10]}:{m['sel']}/{m['len']}")
    for t in r["tr"]:
        P(f"   LW token transfer +{t[0] - r['lb']} to {t[1]} {t[2] / 1e18:.4g}")
    for s in r["swaps"]:
        if s["off"] > 400: continue
        who = "LW" if s["by_lw"] else (s["from"] or "?")
        P(f"   swap +{s['off']} {s['dir']} {s['eth']:.5f} ETH by {who} via {(s.get('to') or '?')[:10]}:{s.get('sel')}/{s.get('len')} value {s.get('value')} "
          f"minOut {s.get('min_out')} rcpt {(s.get('recipient') or '-')[:10]} type {s.get('type')}")
    n4 = sum(1 for s in r["swaps"] if s["off"] > 400)
    if n4: P(f"   ({n4} more swaps after +400 to +{r['ev_to'] - r['lb']}; buys {sum(1 for s in r['swaps'] if s['off'] > 400 and s['dir'] == 'B')})")
    for b in r["burns"]:
        P(f"   burn +{b['off']} L {b['L']:.4g} by {'LW' if b['by_lw'] else b['from']} call {b['sel']}{'  <- PULL' if b['L'] > 0 else ' (fee poke)'}")
    if not r["burns"]: P(f"   no burn to +{r['ev_to'] - r['lb']}")
open(p("b03_table.out"), "w").write("\n".join(out) + "\n"); print(len(out), "lines")
