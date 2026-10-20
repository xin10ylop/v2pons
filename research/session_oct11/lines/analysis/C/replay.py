"""Replay of a hypothetical round trip on Uniswap V2 / V3 pools from the census events (analyst C).

V2: constant product with the pair's reserves rebuilt from Mint/Swap/Burn (fee 0.3% on the input, as the V2 pair: out = y*x*997/(X*1000+x*997)).
V3: positions (tickLower, tickUpper, liquidity) from Mint/Burn; the price is synced to the Swap events' sqrtPriceX96 until our buy, then every
swap is re-simulated by amount (exact input) on the simulated state with tick crossing between positions (float math; within one range it is
the v4math formula: 1/s' = 1/s + x/L for token0 in, s' = s + x/L for token1 in), fee = the pool's fee (ppm) on the input.
Before the first swap the price is taken from the first Mint: a single-sided token position puts the price at its boundary on the token
side (any price beyond it trades identically for a buy); a two-sided one gives s = sqrt(pl) + amount1/L.
Rule: buy q ETH at the head of block L+a (after every event of blocks < L+a), re-apply every swap of blocks [L+a, L+b), sell all at the head of L+b.
A pull (V2 Burn, V3 Burn with liquidity > 0) in a block <= L+b counts as -100% (flag `pulled`)."""
import math
Q96 = 2.0 ** 96
GAS_USD = 0.02; ETH_USD = 2570.0
def sq(t): return 1.0001 ** (t / 2.0)


class V2Sim:
    def __init__(self, qs):
        self.qs = qs; self.x = 0; self.y = 0      # x = WETH reserve, y = token reserve (raw ints)
    def apply(self, e, resim=False):
        qs = self.qs
        if e[0] == "mi": self.x += e[6 + qs]; self.y += e[7 - qs]
        elif e[0] == "b": self.x -= e[6 + qs]; self.y -= e[7 - qs]
        elif e[0] == "s":
            qin, tin, qout, tout = (e[6], e[7], e[8], e[9]) if qs == 0 else (e[7], e[6], e[9], e[8])
            if not resim:
                self.x += qin - qout; self.y += tin - tout
            else:
                if qin > 0 and tout > 0: self.buy(qin)
                elif tin > 0: self.sell(tin)
    def buy(self, xin):
        if self.x <= 0 or self.y <= 0: return 0
        out = self.y * xin * 997 // (self.x * 1000 + xin * 997)
        self.x += xin; self.y -= out; return out
    def sell(self, tin):
        if self.x <= 0 or self.y <= 0: return 0
        out = self.x * tin * 997 // (self.y * 1000 + tin * 997)
        self.x -= out; self.y += tin; return out
    def ok(self): return self.x > 0 and self.y > 0
    def price(self): return self.x / self.y if self.y else 0.0   # ETH per token


class V3Sim:
    def __init__(self, qs, fee):
        self.qs = qs; self.fee = fee; self.pos = {}; self.s = None
    def _act(self, s, up):
        # active liquidity for a move up (positions with sl <= s < sh) or down (sl < s <= sh)
        L = 0.0
        for (lo, hi), l in self.pos.items():
            a, b = sq(lo), sq(hi)
            if (a <= s < b) if up else (a < s <= b): L += l
        return L
    def _bounds(self):
        bs = set()
        for (lo, hi), l in self.pos.items():
            if l > 0: bs.add(sq(lo)); bs.add(sq(hi))
        return sorted(bs)
    def apply(self, e, resim=False):
        if e[0] == "mi":
            k = (e[6], e[7]); self.pos[k] = self.pos.get(k, 0) + e[8]
            if self.s is None:
                a, b = sq(e[6]), sq(e[7]); a0, a1 = e[9], e[10]
                if a0 > 0 and a1 > 0: self.s = a + a1 / e[8]
                elif a0 > 0: self.s = a          # only token0: price at/below the lower bound
                else: self.s = b                 # only token1: price at/above the upper bound
        elif e[0] == "b":
            if e[8] > 0:
                k = (e[6], e[7]); self.pos[k] = self.pos.get(k, 0) - e[8]
        elif e[0] == "s":
            if not resim:
                self.s = e[9] / Q96
            else:
                dq, dt = (e[7], e[8]) if self.qs == 0 else (e[8], e[7])
                if dq > 0: self.buy(dq)
                elif dt > 0: self.sell(dt)
    def _swap(self, amt, zero_for_one):
        """exact input amt (raw) of token0 (zero_for_one) or token1; returns the output amount (float)"""
        x = amt * (1 - self.fee / 1e6); out = 0.0; s = self.s
        bs = self._bounds()
        for _ in range(64):
            if x <= 0: break
            if zero_for_one:      # price down
                L = self._act(s, False); nb = [b for b in bs if b < s * (1 - 1e-15)]
                if L <= 0:
                    if not nb: break
                    s = nb[-1]; continue
                tgt = nb[-1] if nb else 0.0
                need = L * (1 / tgt - 1 / s) if tgt > 0 else float("inf")
                if x <= need:
                    s2 = 1.0 / (1.0 / s + x / L); out += L * (s - s2); s = s2; x = 0
                else:
                    out += L * (s - tgt); x -= need; s = tgt
            else:                 # price up
                L = self._act(s, True); nb = [b for b in bs if b > s * (1 + 1e-15)]
                if L <= 0:
                    if not nb: break
                    s = nb[0]; continue
                tgt = nb[0] if nb else float("inf")
                need = L * (tgt - s)
                if x <= need:
                    s2 = s + x / L; out += L * (1 / s - 1 / s2); s = s2; x = 0
                else:
                    out += L * (1 / s - 1 / tgt); x -= need; s = tgt
        self.s = s
        return out
    def buy(self, qin):   # quote in
        return self._swap(qin, self.qs == 0)
    def sell(self, tin):
        return self._swap(tin, self.qs == 1)
    def ok(self): return self.s is not None and any(l > 0 for l in self.pos.values())
    def price(self):      # ETH per token
        if self.s is None: return 0.0
        return 1.0 / self.s ** 2 if self.qs == 0 else self.s ** 2


def make_sim(row):
    if row["dex"] in ("v2a", "v2b"): return V2Sim(row["quote_side"])
    return V3Sim(row["quote_side"], row["fee"])


def is_pull(e, dex):
    return e[0] == "b" and (dex in ("v2a", "v2b") or e[8] > 0)


def replay(row, o, a, b, q_eth=0.0058, drop=None):
    """-> dict(ok, ret, usd, pulled, reason). o = the pool's events dict (load_events row). drop: set of (block, log index) of swaps
    assumed to revert because of our buy (removed from the replay)."""
    lb = o["lb"]; ev = o["ev"]; dex = row["dex"]
    if b <= a: return {"ok": False, "reason": "b<=a"}
    if lb + b > o["ev_to"]: return {"ok": False, "reason": "window"}
    sim = make_sim(row)
    i = 0
    while i < len(ev) and ev[i][1] < lb + a:
        sim.apply(ev[i]); i += 1
    if not sim.ok(): return {"ok": False, "reason": "noliq"}
    pulled = any(is_pull(e, dex) and e[1] <= lb + b for e in ev)
    qw = int(q_eth * 1e18)
    tok = sim.buy(qw)
    while i < len(ev) and ev[i][1] < lb + b:
        if not is_pull(ev[i], dex) and not (drop and (ev[i][1], ev[i][3]) in drop): sim.apply(ev[i], resim=True)
        i += 1
    out = sim.sell(tok) if tok > 0 else 0
    ret = (out - qw) / qw
    if pulled: ret = -1.0
    return {"ok": True, "ret": ret, "usd": ret * q_eth * ETH_USD - GAS_USD, "pulled": pulled, "ret_nopull": (out - qw) / qw}
