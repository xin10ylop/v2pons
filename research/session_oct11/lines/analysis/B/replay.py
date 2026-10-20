"""The brief's replay on Uniswap v4 pools, for either quote side (currency0 = ETH, or the quote as currency1), from the census events.
State = (sqrtPriceX96, active liquidity). Our buy of q at the head of block L+a, every later swap re-applied by its input amount (buys: the
quote in; sells: the token in) with its own event fee, the liquidity taken from each Swap event (and adds/pulls applied when their range
holds the current tick), our sell at the head of block L+b. Any liquidity removal before block L+b = -100% (flagged)."""
import math
Q96 = 1 << 96
DYN = 8388608
GAS_ETH = 0.02 / 2570          # $0.02 per round trip
ETH_PER_USDG = 1 / 2570
DEC = {"ETH": 1e18, "WETH": 1e18, "USDG": 1e6, "USDG2": 1e18}


def to_eth(raw, quote):
    """raw quote units -> ETH-equivalent"""
    x = raw / DEC[quote]
    return x * ETH_PER_USDG if quote.startswith("USDG") else x


def from_eth(eth, quote):
    x = eth / ETH_PER_USDG if quote.startswith("USDG") else eth
    return int(x * DEC[quote])


def swap(sqrt_p, liq, amt_in, fee, zero_for_one):
    """exact-in swap inside one liquidity range (integer, as the PoolManager rounds): -> (amount out, new sqrtP)"""
    if liq <= 0 or amt_in <= 0 or sqrt_p <= 0:
        return 0, sqrt_p
    x = amt_in - (amt_in * fee + 999_999) // 1_000_000
    if x <= 0:
        return 0, sqrt_p
    if zero_for_one:                                       # currency0 in: price down
        num = liq * sqrt_p; den = liq + (x * sqrt_p) // Q96
        s2 = (num + den - 1) // den
        return (liq * (sqrt_p - s2)) // Q96, s2
    s2 = sqrt_p + (x * Q96) // liq                          # currency1 in: price up
    return (liq * (s2 - sqrt_p) * Q96) // (sqrt_p * s2), s2


def tick_of(sqrt_p):
    return math.floor(2 * math.log(sqrt_p / Q96) / math.log(1.0001)) if sqrt_p > 0 else -887272


class Pool:
    """one pool's events, parsed: swaps [(bn, li, buy, qin, tin, sqrt, liq, fee)], mods [(bn, li, lo, hi, delta)]"""
    def __init__(self, r, o):
        self.r = r; self.qs = r["quote_side"]; self.L0 = r["launch_block"]; self.quote = r["quote"]
        self.fee = r["fee"]; self.sqrt0 = r["sqrt_p0"]; self.tick0 = r["tick0"]
        self.sw, self.mods = [], []
        for e in o["ev"]:
            if e[0] == "s":
                a0, a1 = e[6], e[7]
                dq, dt = (a0, a1) if self.qs == 0 else (a1, a0)
                buy = dq < 0
                self.sw.append((e[1], e[3], buy, -dq if buy else 0, -dt if not buy else 0, e[8], e[9], e[11], abs(dq)))
            elif e[0] == "m":
                self.mods.append((e[1], e[3], e[6], e[7], e[8]))
        self.pulls = [m for m in self.mods if m[4] < 0]
        self.buy_z41 = self.qs == 0                          # a buy is zeroForOne when the quote is currency0

    def contains(self, lo, hi, tick, sqrt_p):
        # the range that a buy enters first: quote currency0 -> price moves down: lo < tick <= hi; quote currency1 -> lo <= tick < hi
        return (lo < tick <= hi) if self.qs == 0 else (lo <= tick < hi)

    def state_at(self, blk):
        """(sqrtP, liquidity, n_events_before) at the head of block blk"""
        sp, liq, last = self.sqrt0, 0, (-1, -1)
        lastsw = None
        for s in self.sw:
            if s[0] < blk: lastsw = s
            else: break
        if lastsw is not None:
            sp, liq, last = lastsw[5], lastsw[6], (lastsw[0], lastsw[1])
            t = tick_of(sp)
            for m in self.mods:
                if (m[0], m[1]) > last and m[0] < blk and self.contains(m[2], m[3], t, sp): liq += m[4]
        else:
            t = self.tick0
            for m in self.mods:
                if m[0] < blk and self.contains(m[2], m[3], t, sp): liq += m[4]
            if liq <= 0:
                # the position sits just beside the launch price (e.g. upper tick = tick0 - 1): a buy crosses the empty gap at no cost,
                # so the pool starts at the range's edge on the buy side
                adds = [m for m in self.mods if m[0] < blk and m[4] > 0]
                if self.qs == 0:
                    edge = max((m[3] for m in adds if m[3] <= t and m[2] < m[3]), default=None)
                    if edge is not None:
                        sp = min(sp, int(1.0001 ** (edge / 2) * Q96)); liq = sum(m[4] for m in self.mods if m[0] < blk and m[2] < edge <= m[3])
                else:
                    edge = min((m[2] for m in adds if m[2] >= t and m[2] < m[3]), default=None)
                    if edge is not None:
                        sp = max(sp, int(1.0001 ** (edge / 2) * Q96)); liq = sum(m[4] for m in self.mods if m[0] < blk and m[2] <= edge < m[3])
        return sp, liq

    def fee_near(self, blk):
        if self.fee != DYN: return self.fee
        nxt = [s[7] for s in self.sw if s[0] >= blk]
        if nxt: return nxt[0]
        prv = [s[7] for s in self.sw if s[0] < blk]
        return prv[-1] if prv else 0

    def validate(self):
        """per swap: relative error of the model's sqrtP after it, from the previous event's sqrtP and this event's liquidity;
        jumps = swaps whose liquidity differs from the previous swap's (a range crossed, or an add/pull between them)"""
        errs = []; jumps = 0; prev_sp = self.sqrt0; prev_l = None
        for s in self.sw:
            if prev_l is not None and s[6] != prev_l: jumps += 1
            amt = s[3] if s[2] else s[4]
            z41 = self.buy_z41 if s[2] else not self.buy_z41
            _, s2 = swap(prev_sp, s[6], amt, s[7], z41)
            if s[5] > 0: errs.append(abs(s2 - s[5]) / s[5])
            prev_sp, prev_l = s[5], s[6]
        return errs, jumps

    def replay(self, a, b, q_eth, oracle_to=None):
        """buy q at the head of L+a, sell at the head of L+b. -> dict(ret, pulled, pulled_before_buy, liq_change, tokens, best (oracle), best_b)"""
        A, B = self.L0 + a, self.L0 + b
        pulled = any(p[0] < B for p in self.pulls)
        pbb = any(p[0] < A for p in self.pulls)
        sp, liq = self.state_at(A)
        if liq <= 0:
            return {"skip": "no liquidity at the buy"}
        q = from_eth(q_eth, self.quote); gas = from_eth(GAS_ETH, self.quote)
        tok, sp = swap(sp, liq, q, self.fee_near(A), self.buy_z41)
        if tok <= 0:
            return {"skip": "zero out"}
        lchg = 0; t = None
        end = max(B, self.L0 + oracle_to) if oracle_to else B   # oracle_to: an offset from the launch
        best, best_b = None, None
        evs = [("s", s) for s in self.sw if A <= s[0] < end] + [("m", m) for m in self.mods if A <= m[0] < end]
        evs.sort(key=lambda x: (x[1][0], x[1][1]))
        def sell_value(blk):
            out, _ = swap(sp, liq, tok, self.fee_near(blk), not self.buy_z41)
            return (out - q - gas) / q
        ret_b = None; i = 0
        blocks = sorted({e[1][0] for e in evs})
        # walk block by block: value at the head of each block after an event block (and at B)
        cur = A
        for kind, e in evs + [(None, None)]:
            blk = e[0] if e is not None else end
            if blk >= B and ret_b is None:
                ret_b = sell_value(B)
            if e is None: break
            if oracle_to and blk > cur and blk > A:
                # the sell at the head of `blk` sees everything before it; also the head of cur+1 (same state)
                v = sell_value(blk)
                if not any(p[0] < blk for p in self.pulls) and (best is None or v > best): best, best_b = v, blk - self.L0
            cur = blk
            if kind == "s":
                amt = e[3] if e[2] else e[4]
                z41 = self.buy_z41 if e[2] else not self.buy_z41
                if e[6] != liq: lchg += 1
                liq = e[6]
                _, sp = swap(sp, liq, amt, e[7], z41)
            else:
                if self.contains(e[2], e[3], tick_of(sp), sp): liq = max(0, liq + e[4])
        if oracle_to:
            v = sell_value(end)
            if not any(p[0] < end for p in self.pulls) and (best is None or v > best): best, best_b = v, end - self.L0
        ret = -1.0 - (gas / q) if pulled else ret_b
        return {"ret": ret, "raw": ret_b, "pulled": pulled, "pbb": pbb, "lchg": lchg, "best": best, "best_b": best_b}
