"""Small counts quoted in REPORT.md: USDG non-vbot pools' first-real-buy share and repeat buyers; odd2 line's distinct first-real-buy EOAs."""
from cands import *
rows = rows_nonvbot()
u = [r for r in rows if r["quote"] in ("USDG", "USDG2")]
fr = [r["frb"] for r in u if r.get("frb")]
top = C.Counter(f"{f['to'][:10]}:{f['sel']}" for f in fr).most_common(3)
print(f"USDG/USDG2 non-vbot pools {len(u)}: with a first real buy {len(fr)} ({len(fr)/len(u):.3f}); distinct frb EOAs {len({f['eoa'] for f in fr})}; top frb fingerprints {top}")
o = [r for r in rows if CANDS["odd2_1444"](r) and r.get("frb")]
print(f"odd2_1444 frb pools {len(o)}: distinct frb EOAs {len({r['frb']['eoa'] for r in o})}; frb EOA bought in >= 3 pools: {sum(1 for r in o if (r['frb'].get('eoa_npools_bought') or 0) >= 3)}; frb fingerprints {C.Counter(r['frb']['to'][:10] + ':' + r['frb']['sel'] for r in o).most_common(3)}")
