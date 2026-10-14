"""Small tell-carrying launches below the 15-launch bar: the 0x82a55dde family (value ~2.40 ETH, fresh wallet, target and hook per launch)
and the two hooked fee-5000/ts-100 launches: swaps, first buys, pull. Output: s15_small.out."""
from common import *
import s07_traits as S
for name, pred in (("0x82a55dde", lambda r: r["sel"] == "0x82a55dde"), ("hooked fee5000/ts100", lambda r: r["fee"] == 5000 and r["ts"] == 100 and r["hook"] != E)):
    F = sorted([r for r in S.rows.values() if pred(r)], key=lambda r: r["b"])
    print("\n==", name, len(F), "launches")
    for r in F:
        p = S.EV.get(r["pid"])
        if not p: print(hm(r["t"]), "v %.5g" % (int(r["v"]) / 1e18), "(events not fetched)"); continue
        sw = S.swaps(p, r); pl, _ = S.pulls(p)
        print(hm(r["t"]), "v %.5g" % (int(r["v"]) / 1e18), "swaps", len(sw), "buys", sum(s["buy"] for s in sw), "ETH in %.4f" % sum((s["eth"] or 0) for s in sw if s["buy"]),
              "pull", (pl[0] - r["b"]) if pl else None, "first buys", [(s["bn"] - r["b"], round(s["eth"] or 0, 5), S.actor(s["h"])) for s in sw if s["buy"]][:5])
