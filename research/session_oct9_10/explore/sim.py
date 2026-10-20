#!/usr/bin/env python3
"""Rule grid simulator (cheap single-range pricer, same conventions as others/analyze.py, with the task's timing):
  entry  e < 39 : fire at F = b0 + K (K = 2..40)
         e >= 39: fire at F = T + d, T = the first swap buying >= THR ETH (THR = 0.0002, 0.001, 0.01; not in the launch tx; T - b0 <= TMAX),
                  d = 0..10; F must be >= b0 + 2 (the bot cannot fire before it has seen the launch)
  our buy lands at B = F + 1, priced at the END of block B (after the other swaps of its block)
  a pull (negative ModifyLiquidity) at a block <= F is visible: no trade; F < pull <= sell landing: -100% (- gas)
  exit: the first block j in B+1 .. B+H holding a buy (a0 < 0) whose post-swap state prices our sell >= TP after gas -> send at j,
        else send at B+H; the sell lands at send+1, priced at the head of that block = the end-of-block state of `send`
  ret = (ETH out - stake - gas) / stake; gas = 4.2e-6 ETH a round trip; pool fee on both legs.
Output: grid.npy float32 [pool, entry(72), stake(2), TP(4), H(59)] (NaN = no trade), meta.pkl (pool order, per-entry info)."""
import sys, os, pickle, math, bisect
import numpy as np
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__))
Q96 = 2.0 ** 96
STAKES = (0.0012e18, 0.012e18); GAS = 4.2e12
TPS = (0.01, 0.02, 0.03, 0.05); HS = list(range(2, 61)); HMAX = 60
KS = list(range(2, 41)); THRS = (0.0002e18, 0.001e18, 0.01e18); DS = list(range(0, 11))
TMAX = 1000
NE = len(KS) + len(THRS) * len(DS)
Z = "0x" + "0" * 40
FEE_MAX = 10000


def active0(tick0, adds):
    return sum(d for lo, hi, d in adds if lo < tick0 <= hi)


def pool_states(p):
    """event list in order with the state after each event: (bn, kind, a0, sp, L)"""
    sw = p["sw"]; mls = p["mls"]
    ev = [(x[0], x[1], 0, x) for x in sw] + [(m[0], m[1], 1, m) for m in mls]
    ev.sort(key=lambda e: (e[0], e[1]))
    out = []; sp = float(p["sp0"]); L = 0.0; tick = p["tick0"]; swapped = False; ranges = []
    for bn, li, k, x in ev:
        if k == 0:
            sp = float(x[4]); L = float(x[5]); swapped = True
            out.append((bn, 0, x[2], sp, L, x[7]))
        else:
            lo, hi, dl = x[2], x[3], x[4]
            ranges.append((lo, hi, dl))
            if not swapped: L = float(active0(p["tick0"], ranges))
            else:
                # current tick from sqrtP
                t = math.floor(math.log((sp / Q96) ** 2) / math.log(1.0001)) if sp > 0 else 0
                if lo <= t < hi or lo < t <= hi: L = max(0.0, L + dl)
            out.append((bn, 1, dl, sp, L, x[5]))
    return out


def buy_out(s, L, x):          # s = sqrtP (float, not Q96)
    s2 = 1.0 / (1.0 / s + x / L); return L * (s - s2)


def sell_out(s, L, t):
    s2 = s + t / L; return L * (1.0 / s - 1.0 / s2)


def sim_pool(p):
    b0 = p["b0"]; fee = p["fee"] / 1e6
    res = np.full((NE, 2, len(TPS), len(HS)), np.nan, dtype=np.float32)
    info = [None] * NE
    if "sw" not in p or p["hooks"] != Z or p["fee"] > FEE_MAX: return res, info, None
    st = pool_states(p)
    bns = [e[0] for e in st]
    pulls = [e[0] for e in st if e[1] == 1 and e[2] < 0]
    pull = pulls[0] if pulls else None
    # triggers
    trig = []
    for thr in THRS:
        t = next((e[0] for e in st if e[1] == 0 and -e[2] >= thr and e[5] != p["tx"] and e[0] >= b0), None)
        trig.append(t if t is not None and t - b0 <= TMAX else None)
    def end_state(j):
        i = bisect.bisect_right(bns, j) - 1
        if i < 0: return float(p["sp0"]), 0.0
        return st[i][3], st[i][4]
    cache = {}
    def run(F):
        B = F + 1
        if B in cache: return cache[B]
        r = None
        if pull is not None and pull <= F: cache[B] = ("pulled_before", None); return cache[B]
        sp, L = end_state(B)
        if L <= 0 or sp <= 0: cache[B] = ("noliq", None); return cache[B]
        s = sp / Q96; xv = L / s / 1e18     # virtual ETH reserve
        outs = []
        for stake in STAKES:
            xn = stake * (1 - fee); tok = buy_out(s, L, xn); tn = tok * (1 - fee)
            def ret(spc, Lc):
                if Lc <= 0 or spc <= 0: return -1.0 - GAS / stake
                so = 1.0 / (1.0 / (spc / Q96) + xn / Lc)
                return (sell_out(so, Lc, tn) - stake - GAS) / stake
            mb = [-9.0] * (HMAX + 1); er = [None] * (HMAX + 1)
            i0 = bisect.bisect_right(bns, B); i1 = bisect.bisect_right(bns, B + HMAX)
            for i in range(i0, i1):
                e = st[i]
                if e[1] == 0 and e[2] < 0:
                    v = ret(e[3], e[4]); j = e[0] - B
                    if v > mb[j]: mb[j] = v
            for j in range(0, HMAX + 1):
                a, b = end_state(B + j); er[j] = ret(a, b)
            arr = np.empty((len(TPS), len(HS)), dtype=np.float32)
            pr = (pull - B) if pull is not None else None
            for ti, tp in enumerate(TPS):
                ftp = next((j for j in range(1, HMAX + 1) if mb[j] >= tp), None)
                for hi_, H in enumerate(HS):
                    send = ftp if (ftp is not None and ftp <= H) else H
                    if pr is not None and pr <= send + 1: arr[ti, hi_] = -1.0 - GAS / stake
                    else: arr[ti, hi_] = er[send]
            outs.append(arr)
        cache[B] = ("ok", outs, xv)
        return cache[B]
    e = 0
    for K in KS:
        F = b0 + K; r = run(F)
        if r[0] == "ok": res[e, 0] = r[1][0]; res[e, 1] = r[1][1]
        info[e] = (K, None, r[0], r[2] if r[0] == "ok" else None); e += 1
    for ti, thr in enumerate(THRS):
        for d in DS:
            T = trig[ti]
            if T is None: info[e] = (None, None, "no_trig", None); e += 1; continue
            F = T + d
            if F < b0 + 2: info[e] = (F - b0, T - b0, "too_early", None); e += 1; continue
            r = run(F)
            if r[0] == "ok": res[e, 0] = r[1][0]; res[e, 1] = r[1][1]
            info[e] = (F - b0, T - b0, r[0], r[2] if r[0] == "ok" else None); e += 1
    return res, info, {"pull": (pull - b0) if pull is not None else None, "trig": [(t - b0) if t is not None else None for t in trig]}


def work(pid):
    return pid, sim_pool(P[pid])


if __name__ == "__main__":
    P = pickle.load(open(os.path.join(HERE, "pools.pkl"), "rb"))
    pids = sorted([pid for pid, p in P.items() if "sw" in p and p["hooks"] == Z and p["fee"] <= FEE_MAX and len(p["sw"]) > 0], key=lambda q: P[q]["b0"])
    print("pools to simulate", len(pids), flush=True)
    G = np.lib.format.open_memmap(os.path.join(HERE, "grid.npy"), mode="w+", dtype=np.float32, shape=(len(pids), NE, 2, len(TPS), len(HS)))
    meta = {"pids": pids, "info": {}, "pinfo": {}, "TPS": TPS, "HS": HS, "KS": KS, "THRS": THRS, "DS": DS, "STAKES": STAKES, "TMAX": TMAX}
    idx = {p: i for i, p in enumerate(pids)}
    with Pool(4) as pool:
        for n, (pid, (res, info, pinfo)) in enumerate(pool.imap_unordered(work, pids, chunksize=8)):
            G[idx[pid]] = res; meta["info"][pid] = info; meta["pinfo"][pid] = pinfo
            if n % 500 == 0: print(n, flush=True)
    G.flush()
    pickle.dump(meta, open(os.path.join(HERE, "meta.pkl"), "wb"))
    print("done")
