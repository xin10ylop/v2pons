"""The 2,020 B hooked pump line (a98b3b9e; POSM multicall, fee 3000/ts 60, a fresh wallet and hook per launch): hook bits, first pools'
timelines, swap actors in +400, and per pool the operator router 0x75379d5d's first buy T, its buys, the pull, and every non-operator swap.
Output: s12_2020b.out."""
from common import *
import collections
import s07_traits as S
fam = "K1 v4 0x58daec31 0xac9650d8 2020B f3000 ts60 v0 ETH hooked"
F = sorted([S.rows[t["pid"]] for t in jload("s05_targets.json") if t["fam"] == fam], key=lambda r: r["b"])
FL = ["BI", "AI", "BA", "AA", "BR", "AR", "BS", "AS", "BD", "AD", "BS_RD", "AS_RD", "AA_RD", "AR_RD"]
print("hook flags:", collections.Counter("+".join(n for i, n in enumerate(FL) if int(r["hook"], 16) >> (13 - i) & 1) for r in F))
act = collections.Counter(); wal = collections.defaultdict(set); first = collections.defaultdict(list)
for r in F:
    seen = set()
    for s in S.swaps(S.EV[r["pid"]], r):
        if s["bn"] - r["b"] > 400: continue
        t = S.TX.get(s["h"])
        if not t: continue
        a = (t["to"][:10] + ":" + t["s"], "buy" if s["buy"] else "sell"); act[a] += 1; wal[a].add(t["f"])
        if a not in seen: seen.add(a); first[a].append(s["bn"] - r["b"])
print("\nswap actors in +400:")
for a, n in act.most_common(8):
    fs = sorted(first[a]); print("  ", a, "swaps", n, "pools", len(fs), "wallets", len(wal[a]), "first offset p10/50/90", fs[len(fs) // 10], fs[len(fs) // 2], fs[9 * len(fs) // 10])
print("\nper pool:")
for r in F:
    sw = S.swaps(S.EV[r["pid"]], r); pl, _ = S.pulls(S.EV[r["pid"]])
    op = [s for s in sw if S.actor(s["h"]).startswith("0x75379d5d")]
    T = next((s["bn"] - r["b"] for s in op if s["buy"]), None)
    others = [(s["bn"] - r["b"], "B" if s["buy"] else "S", round(s["eth"] or 0, 6), S.actor(s["h"])) for s in sw if not S.actor(s["h"]).startswith("0x75379d5d") and S.actor(s["h"]) != "?"]
    print("%s L %d from %s n %d sqrtP %.4e  T %s  op buys (txs known) %d  pull %s  swaps %d  non-operator %s" % (hm(r["t"]), r["b"], r["frm"][:10], r["n"], int(r["sqrtp"]), T, sum(s["buy"] for s in op), (pl[0] - r["b"]) if pl else None, len(sw), others[:4]))
