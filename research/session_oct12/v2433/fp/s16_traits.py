"""Which launches share a trait with the 2.4333 fingerprint: its exact value, a value within 10%, its sqrtPriceX96 or liquidity (exact, or
within 3%: a scaled or rounded copy), the same implied ETH (L / sqrtP) or token amount (L * sqrtP) of a full-range mint, 1,444-byte calldata,
fee 2500 or 5000 with tick spacing 50/100. Per cluster, with first..last launch."""
import collections, time
from clusters import load
from common import V2433, SQRTP_2433, LIQ_2433
rows = load(); Q = 2 ** 96
X0 = LIQ_2433 / (SQRTP_2433 / Q); Y0 = LIQ_2433 * (SQRTP_2433 / Q)
print("2.4333 full-range mint: ETH %.6f, tokens %.6e, launch tick from sqrtP %.2f" % (X0 / 1e18, Y0 / 1e18, __import__('math').log((SQRTP_2433 / Q) ** 2, 1.0001)))
def near(a, b, tol): return b and abs(a / b - 1) <= tol
tests = {
    "value == 2.4333285": lambda r: int(r["value"]) == V2433,
    "value within 10% of 2.4333": lambda r: near(int(r["value"]), V2433, .10),
    "sqrtP == 2.4333's": lambda r: int(r["sqrtp"]) == SQRTP_2433,
    "sqrtP within 3% (either orientation)": lambda r: near(int(r["sqrtp"]), SQRTP_2433, .03) or (int(r["sqrtp"]) and near(Q * Q / int(r["sqrtp"]), SQRTP_2433, .03)),
    "liquidity == 2.4333's": lambda r: int(r["liq"]) == LIQ_2433,
    "liquidity within 3%": lambda r: near(int(r["liq"]), LIQ_2433, .03),
    "implied ETH (L/sqrtP) within 3% of 2.4333": lambda r: int(r["sqrtp"]) and near(int(r["liq"]) / (int(r["sqrtp"]) / Q), X0, .03),
    "calldata 1,444 B": lambda r: r["clen"] == 1444,
    "fee 2500 ts 50 or fee 5000 ts 100": lambda r: (r["fee"], r["ts"]) in ((2500, 50), (5000, 100)),
}
for name, f in tests.items():
    m = [r for r in rows if f(r)]
    g = collections.defaultdict(list)
    for r in m: g[r["fam"]].append(r)
    print("\n== %s: %d launches in %d clusters" % (name, len(m), len(g)))
    for k, v in sorted(g.items(), key=lambda kv: -len(kv[1]))[:14]:
        print("   %4d  %-62s %s..%s  senders %d  e.g. value %.6f sqrtP %.4e liq %.4e range %s..%s" % (len(v), k[:62], time.strftime("%d %H:%M", time.gmtime(v[0]["t"])), time.strftime("%d %H:%M", time.gmtime(v[-1]["t"])),
              len({r["from"] for r in v}), int(v[-1]["value"]) / 1e18, int(v[-1]["sqrtp"]), int(v[-1]["liq"]), v[-1]["lo"], v[-1]["hi"]))
