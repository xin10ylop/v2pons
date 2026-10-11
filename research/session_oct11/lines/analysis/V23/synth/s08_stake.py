"""Synthesizer step 8: stake scan of each line's rule (plain replay as s02: no revert model for the buys behind ours; the execution lenses
found 0 reverts for the V2 rules up to 0.2 ETH and for the crowd line, and 3 / 25 trips on the 356-B line at 0.0058 / 0.05 ETH).
Validated = days 6-7. -> s08_stake.out"""
import sys, os, statistics as S
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "s02_lines.py")).read()
exec(src.split("# ---- overlaps")[0]); exec(src[src.index("def v3run"):src.index("def stats")])
s2_ = {k: set(v) for k, v in F2.items()}; s3_ = {k: set(v) for k, v in F3.items()}
v40 = (s2_[SH + "50.0900000"] | s2_[SH + "40.0900000"] | s2_[SH + "40.5900000"]) & s2_[K_70]
L = []
for lab, fn, pools, a, b in (("V3 356-B K60 -> +260", v3run, sorted(s3_[K_356]), 60, 260), ("V3 crowd K20 -> +80", v3run, sorted(s3_[K_CROWD]), 20, 80),
                             ("V2 fleet +20 -> +80", v2run, sorted(s2_[K_FLEET]), 20, 80), ("V2 70adce63 >= 40 ETH +150 -> +250", v2run, sorted(v40), 150, 250)):
    row = [lab]
    for q in (0.0058, 0.02, 0.05, 0.1, 0.2):
        xs = fn(pools, a, b, q); v = [x["ret"] for x in xs if x["ts"] >= FIT_END]
        row.append(f"q {q}: 7d {S.mean(x['ret'] for x in xs)*100:+.2f}% | val {S.mean(v)*100:+.2f}% ${sum(v)*q*ETH_USD/2:.0f}/day")
    L.append("\n   ".join(row))
open(os.path.join(HERE, "s08_stake.out"), "w").write("\n".join(L) + "\n"); print("\n".join(L))
