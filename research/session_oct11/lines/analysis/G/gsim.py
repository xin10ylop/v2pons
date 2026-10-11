"""analyst G's replay core (the brief's method; v4 swap math as src/v4math.py buy_out_int / sell_out_int, both quote sides, after B's replay.py).
State = (sqrtPriceX96, active liquidity). Our buy of q at the head of block A = L + K, every later swap re-applied by its input amount (buys: the
quote in; sells: the token in) with its own event fee and the liquidity of its Swap event; adds/pulls applied when their range holds the
current tick. Our own relay's historical swaps (sender 0x2abb5653) are removed (our hypothetical trade replaces them).
For each K the value of our tokens (sell at the head of a block, net of our buy, the sell fee and $0.02 gas, as a return on q) is recorded at
the end of every block A..A+HMAX-1, plus the in-block maximum (for the take-profit trigger), and every exit rule is read off that path."""
import math, bisect
import numpy as np
Q96 = 1 << 96
DYN = 8388608
OUR_RELAY = "0x2abb5653"
ETH_USD = 2570.0
DEC = {"ETH": 10**18, "WETH": 10**18, "USDG": 10**6, "USDG2": 10**18}
KS = [0, 1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 30, 40, 60, 80, 100, 150, 200]
HS = [3, 5, 8, 10, 15, 20, 30, 40, 60, 100, 200]
TPS = [0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.20, 0.50]
XS = [0.01, 0.03, 0.05, 0.1]
HMAX = 200
RULES = [("H", None, H) for H in HS] + [("TP", t, H) for t in TPS for H in HS] + [("X", x, H) for x in XS for H in HS]
NR = len(RULES)
R_H = np.array([r[2] for r in RULES])
R_TYP = np.array([0 if r[0] == "H" else 1 if r[0] == "TP" else 2 for r in RULES])
R_IDX = np.array([0 if r[0] == "H" else (TPS.index(r[1]) if r[0] == "TP" else XS.index(r[1])) for r in RULES])
R_CIDX = np.where(R_TYP == 2, len(TPS) + R_IDX, R_IDX)
SKIP_NONE, SKIP_PULLED, SKIP_NOLIQ, SKIP_ZERO = 0, 1, 2, 3

def rule_name(K, i):
    t, p, H = RULES[i]
    if t == "H": return f"K{K} hold{H}"
    if t == "TP": return f"K{K} TP{int(round(p*100))}% dl{H}"
    return f"K{K} X>={p} dl{H}"

def q_raw(q_eth, quote):
    return int(round(q_eth * (ETH_USD if quote.startswith("USDG") else 1) * DEC[quote]))

def to_eth(raw, quote):
    x = raw / DEC[quote]
    return x / ETH_USD if quote.startswith("USDG") else x

def swap(sqrt_p, liq, amt_in, fee, z41):
    if liq <= 0 or amt_in <= 0 or sqrt_p <= 0: return 0, sqrt_p
    x = amt_in - (amt_in * fee + 999_999) // 1_000_000
    if x <= 0: return 0, sqrt_p
    if z41:
        num = liq * sqrt_p; den = liq + (x * sqrt_p) // Q96
        s2 = (num + den - 1) // den
        return (liq * (sqrt_p - s2)) // Q96, s2
    s2 = sqrt_p + (x * Q96) // liq
    return (liq * (s2 - sqrt_p) * Q96) // (sqrt_p * s2), s2

def tick_of(sp):
    return math.floor(2 * math.log(sp / Q96) / math.log(1.0001)) if sp > 0 else -887272


class PoolSim:
    def __init__(self, r, ev):
        self.r = r; self.L = r["launch_block"]; self.qs = r["quote_side"]; self.quote = r["quote"]
        self.fee = r["fee"]; self.sqrt0 = int(r["sqrt_p0"]); self.tick0 = r["tick0"]
        self.z41 = self.qs == 0                                   # our buy: quote in; zeroForOne when the quote is currency0
        sw_all = ev["sw"]
        self.sw = [s for s in sw_all if not s[8].startswith(OUR_RELAY)]
        self.n_ours = len(sw_all) - len(self.sw)
        self.mods = ev["mods"]
        pb = [m[0] for m in self.mods if m[4] < 0]
        self.pull_bn = min(pb) if pb else None
        evs = [(s[0], s[1], 0, s) for s in self.sw] + [(m[0], m[1], 1, m) for m in self.mods]
        evs.sort(key=lambda x: (x[0], x[1]))
        self.evs = evs
        self.ev_bn = [e[0] for e in evs]
        b = [(s[0], s[7]) for s in self.sw if s[2]]; se = [(s[0], s[7]) for s in self.sw if not s[2]]
        self.bf_bn = [x[0] for x in b]; self.bf = [x[1] for x in b]
        self.sf_bn = [x[0] for x in se]; self.sf = [x[1] for x in se]
        self.static_buy = len(set(self.bf)) <= 1; self.static_sell = len(set(self.sf)) <= 1
        self.fee_unknown = self.fee == DYN and not self.sw

    def _fee(self, blk, bn, fs, other_bn, other_fs):
        if fs:
            i = bisect.bisect_left(bn, blk)
            return fs[i] if i < len(fs) else fs[-1]
        if other_fs:
            i = bisect.bisect_left(other_bn, blk)
            return other_fs[i] if i < len(other_fs) else other_fs[-1]
        return self.fee if self.fee != DYN else 0

    def buy_fee(self, blk):
        if self.static_buy and self.bf: return self.bf[0]
        return self._fee(blk, self.bf_bn, self.bf, self.sf_bn, self.sf)

    def sell_fee(self, blk):
        if self.static_sell and self.sf: return self.sf[0]
        return self._fee(blk, self.sf_bn, self.sf, self.bf_bn, self.bf)

    def contains(self, lo, hi, t):
        return (lo < t <= hi) if self.qs == 0 else (lo <= t < hi)

    def state(self, init):
        """state after the events in `init` (a list of evs entries, in order)"""
        last = None
        for i, e in enumerate(init):
            if e[2] == 0: last = i
        if last is not None:
            s = init[last][3]; sp, liq = s[5], s[6]; t = tick_of(sp)
            for e in init[last + 1:]:
                m = e[3]
                if self.contains(m[2], m[3], t): liq += m[4]
            return sp, liq
        sp = self.sqrt0; t = self.tick0
        mods = [e[3] for e in init]
        liq = sum(m[4] for m in mods if self.contains(m[2], m[3], t))
        if liq <= 0:
            adds = [m for m in mods if m[4] > 0]
            if self.qs == 0:
                edge = max((m[3] for m in adds if m[3] <= t and m[2] < m[3]), default=None)
                if edge is not None:
                    sp = min(sp, int(1.0001 ** (edge / 2) * Q96)); liq = sum(m[4] for m in mods if m[2] < edge <= m[3])
            else:
                edge = min((m[2] for m in adds if m[2] >= t and m[2] < m[3]), default=None)
                if edge is not None:
                    sp = max(sp, int(1.0001 ** (edge / 2) * Q96)); liq = sum(m[4] for m in mods if m[2] <= edge < m[3])
        return sp, liq

    def path(self, K, q):
        """-> (skip code, v_end[HMAX], v_max[HMAX], buys [(j, raw quote in)])"""
        L = self.L; A = L + K; k0 = K == 0
        D = L - 1 if k0 else max(L, A - 2)
        if self.pull_bn is not None and self.pull_bn <= D: return SKIP_PULLED, None, None, None
        i0 = bisect.bisect_left(self.ev_bn, A)
        init = self.evs[:i0]; rest = self.evs[i0:]
        if k0:
            init = [e for e in self.evs if e[0] < A or (e[0] == A and e[3][-1])]
            rest = [e for e in self.evs if e[0] >= A and not (e[0] == A and e[3][-1])]
        sp, liq = self.state(init)
        if liq <= 0: return SKIP_NOLIQ, None, None, None
        tok, sp = swap(sp, liq, q, self.buy_fee(A), self.z41)
        if tok <= 0: return SKIP_ZERO, None, None, None
        g = self.gas
        nz = not self.z41
        static_sf = self.sell_fee(A + 1) if (self.static_sell and self.sf) or (not self.sf and not self.bf) else None
        def val(blk):
            f = static_sf if static_sf is not None else self.sell_fee(blk)
            out, _ = swap(sp, liq, tok, f, nz)
            return (out - q - g) / q
        v_end = np.empty(HMAX); v_max = np.empty(HMAX)
        cur = val(A + 1); jlast = -1; buys = []
        end = A + HMAX
        k = 0; n = len(rest)
        while k < n and rest[k][0] < end:
            blk = rest[k][0]; j = blk - A
            if j > jlast + 1:
                v_end[jlast + 1:j] = cur; v_max[jlast + 1:j] = cur
            vm = -1e18
            while k < n and rest[k][0] == blk:
                e = rest[k][3]
                if rest[k][2] == 0:
                    liq = e[6]
                    if e[2]:
                        _, sp = swap(sp, liq, e[3], e[7], self.z41); buys.append((j, e[3]))
                    else:
                        _, sp = swap(sp, liq, e[4], e[7], nz)
                else:
                    if self.contains(e[2], e[3], tick_of(sp)): liq = max(0, liq + e[4])
                v = val(blk + 1)
                if v > vm: vm = v
                k += 1
            cur = v; v_end[j] = cur; v_max[j] = vm; jlast = j
        if jlast < HMAX - 1:
            v_end[jlast + 1:] = cur; v_max[jlast + 1:] = cur
        return SKIP_NONE, v_end, v_max, buys

    def grid(self, q_eth, ks=KS):
        """-> skip codes (len ks), raw returns (len ks, NR) (no pull accounting), sell offsets s (len ks, NR)"""
        q = q_raw(q_eth, self.quote); self.gas = q_raw(0.02 / ETH_USD, self.quote)
        skips = np.zeros(len(ks), np.int8); raw = np.full((len(ks), NR), np.nan, np.float32); S = np.zeros((len(ks), NR), np.int16)
        xr = [q_raw(x, self.quote) for x in XS]
        for ki, K in enumerate(ks):
            sk, v_end, v_max, buys = self.path(K, q)
            skips[ki] = sk
            if sk: continue
            ftp = np.array([(np.argmax(v_max >= t) if (v_max >= t).any() else HMAX) for t in TPS])
            fx = np.array([next((j for j, a in buys if a >= xx), HMAX) for xx in xr])
            F = np.where(R_TYP == 0, HMAX, np.concatenate([ftp, fx])[R_CIDX])
            s = np.where(F < R_H, F + 1, R_H)
            raw[ki] = v_end[s - 1]; S[ki] = s
        return skips, raw, S

    def validate(self, ev, upto=400):
        """re-apply every swap (ours included) up to L+upto from the launch state, no buy of ours: relative error of the simulated sqrtP after
        each swap vs the recorded one (cumulative path, never reset to the recorded value); liquidity jumps between swaps counted"""
        evs = [(s[0], s[1], 0, s) for s in ev["sw"]] + [(m[0], m[1], 1, m) for m in self.mods]
        evs.sort(key=lambda x: (x[0], x[1]))
        sp, liq = None, None; errs = []; jumps = 0; prev_l = None; started = False
        for e in evs:
            if e[0] > self.L + upto: break
            x = e[3]
            if not started:
                if e[2] == 0:
                    init = [y for y in evs if (y[0], y[1]) < (e[0], e[1])]
                    sp, liq = self.state(init); started = True
                else:
                    continue
            if e[2] == 0:
                if prev_l is not None and x[6] != prev_l: jumps += 1
                liq = x[6]; prev_l = liq
                amt = x[3] if x[2] else x[4]
                _, sp = swap(sp, liq, amt, x[7], self.z41 if x[2] else not self.z41)
                if x[5] > 0: errs.append(abs(sp - x[5]) / x[5])
            else:
                if self.contains(x[2], x[3], tick_of(sp)): liq = max(0, liq + x[4])
        return errs, jumps
