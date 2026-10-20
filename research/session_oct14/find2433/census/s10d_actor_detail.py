"""Shape-blind early actors with a semi-stable offset (from s10c): per-pool detail (offset, size, wallet, minOut/got, the launch) for
0x88767899:0x24856bc3, 0x65050a9b:0x4d819a2a, 0xf0b7eaaf:0x39ecce49. Output: s10d_actor_detail.out."""
from common import *
import collections
import s07_traits as S
pools = {p["pid"]: p for p in jl_load("s10_early_cache.jsonl") + jl_load("s05_events_cache.jsonl")}
for A in ("0x88767899:0x24856bc3", "0x65050a9b:0x4d819a2a", "0xf0b7eaaf:0x39ecce49"):
    print("\n==", A); rows = []
    for pid, p in pools.items():
        r = S.rows[pid]
        for s in S.swaps(p, r):
            if not s["buy"] or s["bn"] <= r["b"] or s["bn"] > r["b"] + 30 or (s["eth"] or 0) < 0.002: continue
            t = S.TX.get(s["h"])
            if t and t["to"][:10] + ":" + t["s"] == A: rows.append((r, s, t, S.minout_ratio(s["h"], s["tok"]))); break
    rows.sort(key=lambda x: x[0]["b"])
    for r, s, t, m in rows[:18]:
        print(" ", hm(r["t"]), "+%d" % (s["bn"] - r["b"]), "%.4f ETH" % s["eth"], "wallet", t["f"][:10], "n", t["n"], "minOut/got", m, "| launch", (r["to"] or "CREATE")[:10], r["sel"], r["clen"], "f%d ts%d" % (r["fee"], r["ts"]), "hook", r["hook"][:10], "from", r["frm"][:10], "n", r["n"])
    print("  launch targets:", collections.Counter((r["to"] or "CREATE")[:10] for r, s, t, m in rows).most_common(6))
