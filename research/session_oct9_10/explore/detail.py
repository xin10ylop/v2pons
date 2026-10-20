"""Per-trade detail of one rule on one pool: why (tp/deadline/pulled), send offset, cheap-pricer ret (as sim.py) and an exact replay ret:
our buy inserted at the end of block B, every later swap of the others re-executed by its input amount (exact-in) on the single active
range (L from the logs; L changes from ModifyLiquidity applied), our sell at the end of the send block."""
import sys, os, math, bisect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim
Q96 = sim.Q96

def detail(p, e, s, t, h):
    b0 = p["b0"]; fee = p["fee"] / 1e6; stake = sim.STAKES[s]; TP = sim.TPS[t]; H = sim.HS[h]
    st = sim.pool_states(p); bns = [x[0] for x in st]
    pulls = [x[0] for x in st if x[1] == 1 and x[2] < 0]; pull = pulls[0] if pulls else None
    if e < len(sim.KS): F = b0 + sim.KS[e]; T = None
    else:
        ti, d = divmod(e - len(sim.KS), len(sim.DS)); thr = sim.THRS[ti]
        T = next((x[0] for x in st if x[1] == 0 and -x[2] >= thr and x[5] != p["tx"] and x[0] >= b0), None)
        if T is None or T - b0 > sim.TMAX: return None
        F = T + d
        if F < b0 + 2: return None
    B = F + 1
    if pull is not None and pull <= F: return None
    def end_state(j):
        i = bisect.bisect_right(bns, j) - 1
        return (st[i][3], st[i][4]) if i >= 0 else (float(p["sp0"]), 0.0)
    sp, L = end_state(B)
    if L <= 0: return None
    s0 = sp / Q96; xn = stake * (1 - fee); tok = sim.buy_out(s0, L, xn); tn = tok * (1 - fee)
    def ret(spc, Lc):
        if Lc <= 0: return -1 - sim.GAS / stake
        so = 1 / (1 / (spc / Q96) + xn / Lc); return (sim.sell_out(so, Lc, tn) - stake - sim.GAS) / stake
    send = B + H; why = "deadline"
    for x in st:
        if B < x[0] <= B + H and x[1] == 0 and x[2] < 0 and ret(x[3], x[4]) >= TP: send = x[0]; why = "tp"; break
    land = send + 1
    if pull is not None and pull <= land:
        return {"ret": -1 - sim.GAS / stake, "exact": -1 - sim.GAS / stake, "why": "pulled", "send": send - B, "B": B - b0, "T": (T - b0) if T else None}
    a, b = end_state(send); r = ret(a, b)
    # exact replay
    sw = {(x[0], x[1]): x for x in p["sw"]}
    s_ = 1 / (1 / s0 + xn / L); Lc = L; mlL = None
    evs = [x for x in sorted(p["sw"] + [(m[0], m[1], None, None, None, None, "ml", m) for m in p["mls"]], key=lambda z: (z[0], z[1])) if B < x[0] <= send]
    for x in evs:
        if x[6] == "ml":
            m = x[7]
            Lc = Lc + m[4] if Lc + m[4] > 0 else Lc     # single active range assumption
            continue
        a0, a1, Lx = x[2], x[3], float(x[5])
        Lc = Lx if Lx > 0 else Lc
        if a0 < 0:   # others' buy: ETH in = -a0 (gross); net of fee
            s_ = 1 / (1 / s_ + (-a0) * (1 - fee) / Lc)
        else:        # others' sell: tokens in = -a1 (gross)
            s_ = s_ + (-a1) * (1 - fee) / Lc
    ex = (Lc * (1 / s_ - 1 / (s_ + tn / Lc)) - stake - sim.GAS) / stake
    return {"ret": r, "exact": ex, "why": why, "send": send - B, "B": B - b0, "T": (T - b0) if T else None}
