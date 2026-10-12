"""The compact table of the asked exits (offline, s04_exits.json): per exit, n / mean / median / up / pulled before the sell, for the holder
regime (T-aligned: ours + holders + 0xbd9dc5f6 from 13:15, n 31), the strict regime (held from <= T+5: ours + early holders, n 10), the
holder-aligned regime (mean, pulled) and the no-holder pools (n 154); 0.002 ETH, and the regime mean at 0.0058 ETH."""
from groups import *
X = json.load(open(S("s04_exits.json"))); R = X["rows"]
REG = lambda r: r["group"] in ("ours", "holder") or r["bd13"]; STRICT = lambda r: r["group"] == "ours" or r["sub"] == "early"; NONE = lambda r: r["group"] == "none" and not r["bd13"]
EX = [f"hold {n}" for n in (5, 10, 15, 20, 25, 30, 40, 60)] + [f"tp {t}% cap {c}" for c in (30, 60) for t in (2, 3, 4, 6, 8)]
def st(rows, kind, e, s="0.002"):
    v = sorted(r["res"][f"{kind} {s}"][e] for r in rows if f"{kind} {s}" in r["res"]); n = len(v)
    med = v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2
    return n, sum(v) / n, med, sum(1 for x in v if x > 0), sum(1 for x in v if x <= -1)
print(f"{'exit':14s} | {'REGIME T-aligned (n, mean, median, up, pulled)':46s} | {'0.0058':>7s} | {'STRICT held from T+2':30s} | {'holder-aligned':16s} | {'NO HOLDER':36s}")
for e in EX:
    a = st([r for r in R if REG(r)], "T", e); a2 = st([r for r in R if REG(r)], "T", e, "0.0058"); b = st([r for r in R if STRICT(r)], "T", e)
    h = st([r for r in R if REG(r)], "H", e); c = st([r for r in R if NONE(r)], "T", e)
    print(f"{e:14s} | n {a[0]} {a[1]:+6.2%} med {a[2]:+6.2%} up {a[3]:2d} pulled {a[4]}       | {a2[1]:+6.2%} | n {b[0]} {b[1]:+7.2%} up {b[3]} pulled {b[4]}  | {h[1]:+6.2%} pulled {h[4]} | n {c[0]} {c[1]:+6.2%} med {c[2]:+6.2%} up {c[3]:3d} pulled {c[4]}")
