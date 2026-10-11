"""curve math (derived from the contract's state and checked against every Buy/Sell event: x*y=k, x = 1.68 ETH virtual + real ETH, y0 = 1e9 tokens,
1% fee taken from the ETH side of both buys and sells, the early surcharge X on non-allowlisted buys, graduation at 4.2 ETH real)."""
VX0 = 1.68e18; Y0 = 10**27; THR = 4.2e18; FEE = 0.01

class Curve:
    def __init__(s): s.x = int(VX0); s.y = Y0
    def real(s): return s.x - int(VX0)
    def price(s): return s.x / s.y
    def apply(s, r):
        """r = packed row (bn, li, tx, kind, topics, words); returns ('B'|'S', eth_gross, tokens) for trades"""
        k = r[3]
        if k == "B":
            ethIn, out, fee, w3 = r[5][:4]; net = ethIn - fee - w3
            s.x += net; s.y -= out; return ("B", ethIn, out)
        if k == "S":
            tin, eout, fee, w3 = r[5][:4]; gross = eout + fee + w3
            s.x -= gross; s.y += tin; return ("S", gross, tin)
        return None
    def apply_sim(s, r):
        """replay another trader's trade on a (modified) state: a buy keeps its net ETH, a sell keeps its tokens"""
        k = r[3]
        if k == "B":
            ethIn, out, fee, w3 = r[5][:4]; net = ethIn - fee - w3
            if s.real() >= THR: return 0
            o = s.y * net // (s.x + net); s.x += net; s.y -= o; return o
        if k == "S":
            tin = r[5][0]; g = s.x * tin // (s.y + tin); s.x -= g; s.y += tin; return g
    def buy(s, eth, surcharge=0.0):
        net = int(eth * (1 - FEE - surcharge)); o = s.y * net // (s.x + net); s.x += net; s.y -= o; return o
    def sell(s, tok):
        g = s.x * tok // (s.y + tok); s.x -= g; s.y += tok; return g * (1 - FEE)
