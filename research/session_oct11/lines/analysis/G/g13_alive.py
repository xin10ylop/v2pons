"""for the top 15: token templates inside each family, the last launch time, launches per 6-hour slice over the last 24 h, and hooks"""
from common import *
rows = {r["pool"]: r for r in load_rows()}
kept = json.load(open(os.path.join(G, "families_kept.json")))
top = json.load(open(os.path.join(G, "g07_top.json")))[:15]
for i, o in enumerate(top):
    rs = [rows[p] for p in kept[o["fam"]]]
    toks = C.Counter((r["fam"]["tok"] or "")[:8] for r in rs).most_common(3)
    hooks = C.Counter(r["hooks"][:10] for r in rs).most_common(2)
    last = max(r["launch_ts"] for r in rs)
    per = [sum(1 for r in rs if slice6(r["launch_ts"]) == s) for s in range(20, 28)]
    print(f"#{i+1} {o['fam'][:90]:90s} toks {toks} hooks {hooks} n_hooks {len(set(r['hooks'] for r in rs))} last launch {(END_TS-last)/3600:.1f} h before the end; launches per 6 h, last 48 h: {per}")
