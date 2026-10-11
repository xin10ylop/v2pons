"""analyst G's replay core, range-aware (v2). Same method as gsim.py (the brief's replay) but the pool is the set of liquidity positions built from
the ModifyLiquidity events (tickLower, tickUpper, delta), and every swap (ours and the re-applied ones) walks across the ranges with the
Uniswap v4 math (TickMath sqrt prices at the range edges, fee taken on the input). This fixes the single-range formula's error when a narrow
position sits beside the price (a later concentrated add made a $15 sale look like +2,800x in gsim.py).
Our own relay's historical swaps (sender 0x2abb5653) are removed."""
import math, bisect
import numpy as np
from tickmath import sqrt_at
from gsim import KS, HS, TPS, XS, HMAX, RULES, NR, R_H, R_TYP, R_IDX, R_CIDX, rule_name, q_raw, to_eth, DYN, OUR_RELAY, ETH_USD
Q96 = 1 << 96
MIN_SQRT = 4295128739; MAX_SQRT = 1461446703485210103287273052203988822378723970342
SKIP_NONE, SKIP_PULLED, SKIP_NOLIQ, SKIP_ZERO = 0, 1, 2, 3


def swap_r(sp, pos, amt_in, fee, z41):
    """exact-in swap across ranges. pos: dict (lo, hi) -> liquidity. -> (amount out, new sqrtP, amount in used incl. fee)"""
    if amt_in <= 0: return 0, sp, 0
    x = amt_in - (amt_in * fee + 999_999) // 1_000_000
    if x <= 0: return 0, sp, amt_in
    rng = [(sqrt_at(lo), sqrt_at(hi), L) for (lo, hi), L in pos.items() if L > 0]
    out = 0; rem = x
    for _ in range(200):
        if rem <= 0: break
        if z41:                                           # price down
            L = sum(l for a, b, l in rng if a < sp <= b)
            tgt = max([a for a, b, l in rng if a < sp] + [b for a, b, l in rng if b < sp] + [MIN_SQRT])
            if L <= 0:
                if tgt <= MIN_SQRT or not any(a < sp for a, b, l in rng): break
                sp = tgt; continue
            need = -(-(L * Q96 * (sp - tgt)) // (sp * tgt))  # amount0 to reach tgt (rounded up)
            if rem >= need:
                out += (L * (sp - tgt)) // Q96; rem -= need; sp = tgt
                if tgt <= MIN_SQRT: break
            else:
                den = L + (rem * sp) // Q96; s2 = -(-(L * sp) // den)
                out += (L * (sp - s2)) // Q96; sp = s2; rem = 0
        else:                                             # price up
            L = sum(l for a, b, l in rng if a <= sp < b)
            tgt = min([b for a, b, l in rng if b > sp] + [a for a, b, l in rng if a > sp] + [MAX_SQRT])
            if L <= 0:
                if tgt >= MAX_SQRT or not any(b > sp for a, b, l in rng): break
                sp = tgt; continue
            need = -(-(L * (tgt - sp)) // Q96)               # amount1 to reach tgt (rounded up)
            if rem >= need:
                out += (L * (tgt - sp) * Q96) // (sp * tgt); rem -= need; sp = tgt
                if tgt >= MAX_SQRT: break
            else:
                s2 = sp + (rem * Q96) // L
                out += (L * (s2 - sp) * Q96) // (sp * s2); sp = s2; rem = 0
    used = amt_in if rem <= 0 else amt_in - rem          # an unfilled remainder (no liquidity left) is not taken
    return out, sp, used


class PoolSim:
    def __init__(self, r, ev):
        self.r = r; self.L = r["launch_block"]; self.qs = r["quote_side"]; self.quote = r["quote"]
        self.fee = r["fee"]; self.sqrt0 = int(r["sqrt_p0"]); self.tick0 = r["tick0"]
        self.z41 = self.qs == 0
        sw_all = ev["sw"]
        self.sw = [s for s in sw_all if not s[8].startswith(OUR_RELAY)]
        self.n_ours = len(sw_all) - len(self.sw)
        self.mods = ev["mods"]
        pb = [m[0] for m in self.mods if m[4] < 0]
        self.pull_bn = min(pb) if pb else None
        evs = [(s[0], s[1], 0, s) for s in self.sw] + [(m[0], m[1], 1, m) for m in self.mods]
        evs.sort(key=lambda x: (x[0], x[1]))
        self.evs = evs; self.ev_bn = [e[0] for e in evs]
        b = [(s[0], s[7]) for s in self.sw if s[2]]; se = [(s[0], s[7]) for s in self.sw if not s[2]]
        self.bf_bn = [x[0] for x in b]; self.bf = [x[1] for x in b]
        self.sf_bn = [x[0] for x in se]; self.sf = [x[1] for x in se]
        self.static_buy = len(set(self.bf)) <= 1; self.static_sell = len(set(self.sf)) <= 1

    def _fee(self, blk, bn, fs, other_bn, other_fs):
        if fs:
            i = bisect.bisect_left(bn, blk); return fs[i] if i < len(fs) else fs[-1]
        if other_fs:
            i = bisect.bisect_left(other_bn, blk); return other_fs[i] if i < len(other_fs) else other_fs[-1]
        return self.fee if self.fee != DYN else 0

    def buy_fee(self, blk):
        if self.static_buy and self.bf: return self.bf[0]
        return self._fee(blk, self.bf_bn, self.bf, self.sf_bn, self.sf)

    def sell_fee(self, blk):
        if self.static_sell and self.sf: return self.sf[0]
        return self._fee(blk, self.sf_bn, self.sf, self.bf_bn, self.bf)

    @staticmethod
    def apply_mod(pos, m):
        k = (m[2], m[3]); v = pos.get(k, 0) + m[4]
        if v > 0: pos[k] = v
        else: pos.pop(k, None)

    def state(self, init):
        pos = {}; sp = self.sqrt0
        for e in init:
            if e[2] == 0: sp = e[3][5]
            else: self.apply_mod(pos, e[3])
        return sp, pos

    def path(self, K, q):
        L = self.L; A = L + K; k0 = K == 0
        D = L - 1 if k0 else max(L, A - 2)
        if self.pull_bn is not None and self.pull_bn <= D: return SKIP_PULLED, None, None, None
        i0 = bisect.bisect_left(self.ev_bn, A)
        init = self.evs[:i0]; rest = self.evs[i0:]
        if k0:
            init = [e for e in self.evs if e[0] < A or (e[0] == A and e[3][-1])]
            rest = [e for e in self.evs if e[0] >= A and not (e[0] == A and e[3][-1])]
        sp, pos = self.state(init)
        if not pos: return SKIP_NOLIQ, None, None, None
        tok, sp, used = swap_r(sp, pos, q, self.buy_fee(A), self.z41)
        if tok <= 0: return SKIP_ZERO, None, None, None
        g = self.gas; nz = not self.z41
        static_sf = self.sf[0] if (self.static_sell and self.sf) else (self.sell_fee(A + 1) if not self.sf and not self.bf else None)
        def val(blk):
            f = static_sf if static_sf is not None else self.sell_fee(blk)
            out, _, _ = swap_r(sp, pos, tok, f, nz)
            return (out - q - g) / q
        v_end = np.empty(HMAX); v_max = np.empty(HMAX)
        cur = val(A + 1); jlast = -1; buys = []
        end = A + HMAX; k = 0; n = len(rest)
        while k < n and rest[k][0] < end:
            blk = rest[k][0]; j = blk - A
            if j > jlast + 1:
                v_end[jlast + 1:j] = cur; v_max[jlast + 1:j] = cur
            vm = -1e18
            while k < n and rest[k][0] == blk:
                e = rest[k][3]
                if rest[k][2] == 0:
                    if e[2]:
                        _, sp, _ = swap_r(sp, pos, e[3], e[7], self.z41); buys.append((j, e[3]))
                    else:
                        _, sp, _ = swap_r(sp, pos, e[4], e[7], nz)
                else:
                    self.apply_mod(pos, e)
                v = val(blk + 1)
                if v > vm: vm = v
                k += 1
            cur = v; v_end[j] = cur; v_max[j] = vm; jlast = j
        if jlast < HMAX - 1:
            v_end[jlast + 1:] = cur; v_max[jlast + 1:] = cur
        return SKIP_NONE, v_end, v_max, buys

    def grid(self, q_eth, ks=KS):
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
        """re-apply every swap (ours included) from the launch with the range-aware math, no buy of ours; relative error of the simulated
        sqrtP after each swap vs the recorded one (cumulative path, never reset)"""
        evs = [(s[0], s[1], 0, s) for s in ev["sw"]] + [(m[0], m[1], 1, m) for m in self.mods]
        evs.sort(key=lambda x: (x[0], x[1]))
        sp = self.sqrt0; pos = {}; errs = []
        for e in evs:
            if e[0] > self.L + upto: break
            x = e[3]
            if e[2] == 0:
                amt = x[3] if x[2] else x[4]
                _, sp, _ = swap_r(sp, pos, amt, x[7], self.z41 if x[2] else not self.z41)
                if x[5] > 0: errs.append(abs(sp - x[5]) / x[5])
            else:
                self.apply_mod(pos, x)
        return errs, 0
