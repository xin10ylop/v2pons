"""d07: when does a holder's token become frozen? For a (token, holder), eth_call transfer(0x...dEaD, 1 unit) from the holder at a series
of past blocks (archive state on keyless endpoints: the call runs on the state AFTER that block), then a binary search for the first block
at which it reverts. Usage: d07_flip.py TOKEN HOLDER FROM_BLOCK TO_BLOCK"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import rpc
DEADA = "000000000000000000000000000000000000dead".rjust(64, "0")
def can(tok, h, b, amt=1):
    r = rpc.call("eth_call", [{"from": h, "to": tok, "gas": hex(300000), "data": "0xa9059cbb" + DEADA + hex(amt)[2:].rjust(64, "0")}, hex(b)], raw=True)
    return r.get("result") is not None and "error" not in r, r
def bal(tok, h, b):
    r = rpc.call("eth_call", [{"to": tok, "data": "0x70a08231" + h[2:].rjust(64, "0")}, hex(b)], raw=True)
    return int(r["result"], 16) if r.get("result") not in (None, "0x") and "error" not in r else None
def flip(tok, h, a, b):
    """first block in (a, b] where transfer reverts, given ok at a and revert at b"""
    while b - a > 1:
        m = (a + b) // 2
        if can(tok, h, m)[0]: a = m
        else: b = m
    return b
if __name__ == "__main__":
    tok, h, a, b = sys.argv[1].lower(), sys.argv[2].lower(), int(sys.argv[3]), int(sys.argv[4])
    pts = sorted(set([a, a + 1, a + 2, a + 5, a + 10, a + 20, a + 50, a + 100, a + 200, b]))
    res = [(p, bal(tok, h, p), can(tok, h, p)) for p in pts if p <= b]
    for p, bl, (ok, r) in res: print(p, "bal", bl, "transfer ok" if ok else "REVERT " + str(r.get("error"))[:80])
    oks = [p for p, bl, (ok, r) in res if ok]; revs = [p for p, bl, (ok, r) in res if not ok and bl]
    if oks and revs and min(revs) > max([o for o in oks if o < min(revs)] or [a]):
        lo = max(o for o in oks if o < min(revs)); f = flip(tok, h, lo, min(revs)); print("first frozen block", f, "(ok at", f - 1, ")")
