"""Per-candidate detail of the first 12 swaps: for swap index i, offset / side / size / to:sel:clen / whether its EOA is the launch wallet."""
from cands import *
rows = rows_nonvbot()
for name, f in CANDS.items():
    rs = [r for r in rows if f(r)]
    print(f"\n===== {name}: {len(rs)} pools, days {[sum(1 for r in rs if day_of(r)==d) for d in range(7)]}, values {C.Counter(f'{r[chr(108)+chr(97)+chr(117)+chr(110)+chr(99)+chr(104)][chr(118)+chr(97)+chr(108)+chr(117)+chr(101)+chr(95)+chr(119)+chr(101)+chr(105)]/1e18:.18g}' for r in rs).most_common(8)}")
    print("   hooks:", C.Counter(r["hooks"][:12] for r in rs).most_common(3), " fee/ts:", C.Counter((r["fee"], r["tick_spacing"]) for r in rs).most_common(3),
          " sqrt/L distinct:", len({(r["sqrt_p0"]) for r in rs}), " nonce:", C.Counter(r["launch"]["nonce"] for r in rs).most_common(4))
    for i in range(6):
        sw = [r["swaps12"][i] for r in rs if r.get("swaps12") and len(r["swaps12"]) > i]
        if not sw: break
        lw = sum(1 for r in rs if r.get("swaps12") and len(r["swaps12"]) > i and r["swaps12"][i][3] == r["launch"]["from"])
        print(f"   swap{i}: n={len(sw)} off={p1050([s[0] for s in sw])} side={C.Counter(s[1] for s in sw).most_common(2)} eth={p1050([s[2] for s in sw])} "
              f"eth_top={C.Counter(round(s[2], 6) for s in sw).most_common(3)} fp={C.Counter(f'{s[4][:10]}:{s[5]}:{s[6]}' for s in sw).most_common(3)} by_launch_wallet={lw} inlaunchtx={sum(1 for s in sw if s[10])} eoas={len({s[3] for s in sw})}")
