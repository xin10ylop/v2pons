"""The e1e75b94 family (a fresh launch contract and a fresh hook per launch, 5,572 B, fee 2500/ts 25): hook permission bits, the first pools'
timelines, and every swap in all 151 pools by actor and wallet. Output: s11_e1e7.out."""
from common import *
import collections
import s07_traits as S
F = sorted([r for r in S.rows.values() if r["sel"] == "0xe1e75b94"], key=lambda r: r["b"])
FL = ["BI", "AI", "BA", "AA", "BR", "AR", "BS", "AS", "BD", "AD", "BS_RD", "AS_RD", "AA_RD", "AR_RD"]   # bit 13 .. bit 0
def flags(h):
    v = int(h, 16) & 0x3FFF
    return "+".join(n for i, n in enumerate(FL) if v >> (13 - i) & 1)
print("hook flags:", collections.Counter(flags(r["hook"]) for r in F))
for r in F[:6]:
    p = S.EV.get(r["pid"])
    print("\n", hm(r["t"]), "L", r["b"], "pool", r["pid"][:12], "to", r["to"][:12], "from", r["frm"][:10], "n", r["n"], "hook", r["hook"][:12])
    ev = [("S", s["bn"], s["li"], s) for s in S.swaps(p, r)] + [("M", m[0], m[2], m) for m in p["ml"]]
    for k, bn, li, x in sorted(ev, key=lambda e: (e[1], e[2]))[:14]:
        if k == "S":
            t = S.TX.get(x["h"], {})
            print("   +%-4d %s %.5f ETH  actor %s wallet %s n %s" % (bn - r["b"], "BUY " if x["buy"] else "SELL", x["eth"] or 0, S.actor(x["h"]), t.get("f", "?")[:10], t.get("n")))
        else:
            d = x[5]; t = S.TX.get(x[3], {})
            print("   +%-4d LIQ %s %d..%d dL %.4g  tx.to %s sel %s from %s" % (bn - r["b"], "ADD" if sgn(W(d, 2)) > 0 else "REMOVE", sgn(W(d, 0)), sgn(W(d, 1)), sgn(W(d, 2)), t.get("to", "?")[:10], t.get("s"), t.get("f", "?")[:10]))
allact = collections.Counter(); wal = collections.Counter(); offs = collections.defaultdict(list)
for r in F:
    for s in S.swaps(S.EV[r["pid"]], r):
        t = S.TX.get(s["h"]); allact[(S.actor(s["h"]), "buy" if s["buy"] else "sell")] += 1
        if t: wal[(t["f"][:10], "buy" if s["buy"] else "sell")] += 1; offs[t["f"][:10]].append(s["bn"] - r["b"])
print("\nall swaps in the family's pools by actor:", allact.most_common(12)); print("by wallet:", wal.most_common(12))
for k, v in offs.items(): print("  offsets", k, sorted(v)[len(v) // 10], sorted(v)[len(v) // 2], sorted(v)[9 * len(v) // 10], "n", len(v))
