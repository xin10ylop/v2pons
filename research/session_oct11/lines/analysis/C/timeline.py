"""Print one pool's event timeline: python3 timeline.py <pool> [max_rows]"""
import sys, os, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
R = load_rows(); E = pickle.load(open(os.path.join(OUT, "ev.pkl"), "rb")); T = pickle.load(open(os.path.join(OUT, "tx.pkl"), "rb"))
def show(p, n=60):
    r = R[p]; o = E[p]; qs = r["quote_side"]; lb = o["lb"]
    print(p, r["dex"], r["launch_utc"], "qs", qs, "fam", r["fam"]["tok"][:8], (r["fam"]["lc"] or "")[:8], "launch from", r["launch"]["from"], "value", r["launch"]["value_eth"])
    x = y = 0
    for e in o["ev"][:n]:
        t = T.get(e[-1], {}); who = (t.get("from") or "?")[:10]; sel = t.get("selector"); to = (t.get("to") or "?")[:10]
        if r["dex"] in ("v2a", "v2b"):
            if e[0] == "mi": dq, dt = e[6 + qs], e[7 - qs]; x += dq; y += dt; k = "MINT"
            elif e[0] == "b": dq, dt = -e[6 + qs], -e[7 - qs]; x += dq; y += dt; k = "BURN"
            else:
                qin, tin, qout, tout = (e[6], e[7], e[8], e[9]) if qs == 0 else (e[7], e[6], e[9], e[8])
                dq, dt = qin - qout, tin - tout; x += dq; y += dt; k = "BUY " if dq > 0 else "SELL"
            px = x / y if y else 0
            print(f"  +{e[1]-lb:5d} {k} dETH {dq/1e18:+.5f} dTok {dt/1e18:+.4g} resETH {x/1e18:.4f} px {px:.4g} {who} {to} {sel}")
        else:
            if e[0] == "s":
                dq, dt = (e[7], e[8]) if qs == 0 else (e[8], e[7]); k = "BUY " if dq > 0 else "SELL"
                print(f"  +{e[1]-lb:5d} {k} dETH {dq/1e18:+.5f} dTok {dt/1e18:+.4g} sqrtP {e[9]:.6g} L {e[10]:.4g} tick {e[11]} {who} {to} {sel}")
            else:
                print(f"  +{e[1]-lb:5d} {e[0].upper()} lo {e[6]} hi {e[7]} L {e[8]:.4g} a0 {e[9]/1e18:.4g} a1 {e[10]/1e18:.4g} {who} {to} {sel}")
if __name__ == "__main__":
    show(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 60)
