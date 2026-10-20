"""C-1: does the launch wallet pull sooner when an outsider buys around the bot's wave? Pools with an outsider buy (census outsider12 /
outsider blocks; shared fingerprints excluded = nf) at or after the first real buy vs without: share pulled within frb+62, pull - frb."""
from cands import *
rows = rows_nonvbot()
rs = [r for r in rows if (CANDS["C1_eth"](r) or CANDS["C1_weth"](r)) and r.get("frb")]
def outsider_after(r, key):
    o = r.get(key) or {}
    lo = o.get("nf_last_off") if key == "outsider12" else o.get("nf_last_off")
    return o.get("nf_n", 0) > 0 and lo is not None and lo >= r["frb"]["off"]
for key in ("outsider12", "outsider"):
    A = [r for r in rs if outsider_after(r, key)]; B = [r for r in rs if not outsider_after(r, key)]
    for lab, g in (("with outsider after frb", A), ("without", B)):
        if not g: continue
        pw = sum(1 for r in g if r.get("n_pulls") and r["first_pull_off"] <= r["frb"]["off"] + 62)
        print(f"[{key}] {lab}: pools {len(g)}, pulled by frb+62: {pw} ({pw/len(g):.3f}), pull - frb p10/50/90 {p1050([r['first_pull_off'] - r['frb']['off'] for r in g if r.get('n_pulls')])}")
