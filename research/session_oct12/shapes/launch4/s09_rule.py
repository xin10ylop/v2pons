"""The simplest rule on every core pool of S2, S3, S4 (12 h): buy 0.002 ETH at launch + B (B = 1, 2, 3), sell at launch + N (N = 60, 600, 3000).
Single-range v4 math with the pool's constant in-range liquidity (each of these pools has one position): a buy with x ETH moves 1/sqrtP by
x_eff/L, a sell of y coins moves sqrtP by y_eff/L. Our buy is placed on the pool state after the last swap at or before L+B; the sell on the
state after the last swap at or before L+N, shifted by our own buy (1/sqrtP + x_eff/L). Fees: S2 hook 1% of the WETH in and 1% of the WETH
out (2% each in the 2,500/100/100-configured runner, measured in s07_fees.out), LP fee 0; S3/S4 LP fee 1% of the input, no hook.
Gross of gas. S1 is not simulated (multi-curve hook liquidity; 2 of 166 pools ever traded; a measured round trip cost 2.0%, s07_fees.out).
Prints s09_rule.out."""
from common import *
D = json.load(open(J("s06_pools.json"))); A = {p["pid"]: p for p in json.load(open(J("s04_pools.json")))["pools"]}
Q = 2 ** 96
def run(p, B, N, x=0.002e18):
    lt = [m for m in A[p["pid"]]["ml"] if m["inlaunch"]]
    L = sum(m["dL"] for m in lt)
    if p["shape"] == "S2":
        fin, fout, lp = (0.02, 0.02, 0) if p["launcher"].startswith("0x6901126c") else (0.01, 0.01, 0)
    else: fin, fout, lp = 0.0, 0.0, 0.01
    def state(off):
        sw = [w for w in p["sw"] if w["off"] <= off]
        sp = sw[-1]["sqrtP"] if sw else min(p["sqrtP0"], int(1.0001 ** (max(m["hi"] for m in lt) / 2) * Q))   # launch price clipped to the range top
        return sp / Q
    s = state(B)
    xe = x * (1 - fin) * (1 - lp)
    s1 = 1 / (1 / s + xe / L); y = L * (s - s1)
    ss = 1 / (1 / state(N) + xe / L)          # sell state shifted by our buy
    ye = y * (1 - lp); s2 = ss + ye / L; out = L * (1 / ss - 1 / s2) * (1 - fout)
    return out / x - 1
for s in ("S2", "S3", "S4"):
    pp = [p for p in D["pools"] if p["shape"] == s]
    print(f"== {s}: {len(pp)} pools")
    for B in (1, 2, 3):
        for N in (60, 600, 3000):
            rr = []
            for p in pp:
                if p["age"] < N: continue
                rr.append((run(p, B, N), p["pid"][:10]))
            v = [r for r, _ in rr]
            best = max(rr)
            print(f"   buy +{B} sell +{N:<4d}: n {len(v):3d} mean {100 * sum(v) / len(v):+7.2f}%  median {100 * pct(v, .5):+6.2f}%  win {sum(1 for r in v if r > 0):3d}  "
                  f"best {100 * best[0]:+8.1f}% ({best[1]})  mean without the best {100 * (sum(v) - best[0]) / (len(v) - 1):+6.2f}%")
