"""d13: the tables. (1) every stranger (token, buyer) of the last 3 days that bought before its pool's dump, by buy offset: frozen while
holding / moved tokens out before the freeze / never frozen; (2) the same by method, recipient type, gas price, template; (3) the replay's
exactness on our own buy; (4) the first crowd buy per pool and the short holds (h = 1..3 blocks) at every entry +40..+300.
-> d13_tables.out"""
import json, os, sys, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from common import *; import rpc
import importlib.util
T = json.load(open(os.path.join(D, "d10_table.json"))); R = T["rows"]; CROWD = set(T["crowd"])
pre = [r for r in R if r["before_dump"]]
def cls(r):
    if r["frozen"]: return "frozen_holding" if not r["moved_before_freeze"] else ("exited_then_frozen_rest" if r["bal_now"] else "exited_before_freeze")
    return "never_frozen_exited" if r["moves"] else ("never_frozen_dust" if (r["bal_now"] or 0) <= 1 else "never_frozen_holding")
BK = [(0, 20), (20, 40), (40, 60), (60, 100), (100, 200), (200, 260), (260, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000)]
print("(1) strangers before the dump, last 3 days (both templates):", len(pre), C.Counter(cls(r) for r in pre))
print("    buy offset    n  frozen_holding  exited_before_freeze(sold <= 16 blk)  exited_then_frozen_rest  never_frozen_dust | freeze delay min/median/max")
for a, b in BK:
    xs = [r for r in pre if a <= r["off"] < b]
    if not xs: continue
    c = C.Counter(cls(r) for r in xs); dl = sorted(r["delay"] for r in xs if r["frozen"])
    print("    +%4d..+%4d %4d  %14d  %20d  %22d  %17d | %s" % (a, b - 1, len(xs), c["frozen_holding"], c["exited_before_freeze"] + c["never_frozen_exited"], c["exited_then_frozen_rest"],
          c["never_frozen_dust"], ("%d/%d/%d" % (dl[0], dl[len(dl) // 2], dl[-1])) if dl else "-"))
print("    2,995-byte template only (the 1/10/25-BNB pools):", C.Counter(cls(r) for r in pre if r["code"] == 2995))
print("(2) by method (target:selector), recipient type, gas price, tx.from == recipient:")
for key, f in (("method", lambda r: ("router:" if r["tx_to"] == ROUTER else "other:") + (r["sel"] or "?")), ("rtype", lambda r: r["rtype"]),
               ("gas", lambda r: "0.051 (crowd's)" if abs(r["gp_gwei"] - 0.051) < 1e-9 else ("<0.051" if r["gp_gwei"] < 0.051 else ">0.051")), ("self", lambda r: r["self"])):
    t = C.defaultdict(C.Counter)
    for r in pre: t[f(r)][cls(r)] += 1
    print("   ", key, {k: dict(v) for k, v in sorted(t.items(), key=lambda kv: -sum(kv[1].values()))})
ex = [r for r in pre if cls(r) in ("exited_before_freeze", "never_frozen_exited", "exited_then_frozen_rest")]
print("    the strangers that got tokens out before a freeze:", [(r["buyer"][:10], "+%d" % r["off"], "out after %d blk" % (r["first_move_off"] - r["off"]), r["first_move_kind"], r["sel"], r["size"]) for r in ex])
post = [r for r in R if not r["before_dump"]]
print("    after the dump:", len(post), C.Counter(cls(r) for r in post))
# (3) exactness: our buy at L+52 (tx index 35) replayed on the pair's own logs with its real msg.value
P = pairlogs(); TX = txs()
pr = "0x2de2620b04a0382390b18441cd033da7b798e57e"; L = 127550490
evs = sorted([r for r in P if r[4] == pr], key=lambda r: (r[0], r[1], r[2]))
ob = [r for r in evs if r[3] == "0x67dde265f814e1985643d1a3980d20a4ba93030e7feb08c30e7c377a36173eab"]
before = [r for r in evs if (r[0], r[1]) < (ob[0][0], ob[0][1]) and r[5] == "sync"][-1]
lo = launches(); side = [o for o in lo if o["pair"] == pr][0]["side"]
rq, rt = (before[6], before[7]) if side == 0 else (before[7], before[6])
v = int(round(TX["0x67dde265f814e1985643d1a3980d20a4ba93030e7feb08c30e7c377a36173eab"][5]))
print("(3) our buy: msg.value", v, "V2 formula on the reserves before it ->", amount_out(v, rq, rt), "| the pair sent", [r for r in ob if r[5] == "swap"][0][8 + (1 - side) - 0 if side == 0 else 8])
# (4) first crowd buy per pool and short holds
spec = importlib.util.spec_from_file_location("rp", os.path.join(D, "d12_reprice.py"))
src = open(os.path.join(D, "d12_reprice.py")).read().split("out = {\"n_pools\"")[0]
g = {"__file__": os.path.join(D, "d12_reprice.py")}; exec(compile(src, "d12_head", "exec"), g)
LS, replay, ev = g["LS"], g["replay"], g["ev"]
fc = C.defaultdict(list)
for o in LS:
    offs = sorted(r[0] - o["L"] for r in ev[o["pair"]] if r[5] == "swap" and r[11] in CROWD and (r[6] if o["side"] == 0 else r[7]) > 0)
    fc[o["size"]].append(offs[0] if offs else None)
for s in (1.0, 10.0, 25.0): print("(4) size %4s first crowd buy offsets:" % s, sorted(C.Counter(fc[s]).items()))
GAS = g["GAS"]
for size in (1.0, 10.0, 25.0):
    pools = [o for o in LS if o["size"] == size]
    for h in (1, 2, 3):
        res = []
        for K in range(40, 301):
            nt = [(lambda r: (r[2] - r[0] - GAS) / r[0])(r) for r in (replay(o, K, K + h) for o in pools) if r]
            res.append((sum(nt) / len(nt), K, sorted(nt)[len(nt) // 2], sum(1 for x in nt if x > 0) / len(nt)))
        res.sort(reverse=True)
        print("    short hold size %4s h %d: best entries %s; at +50: mean %+.2f%%" % (size, h, ["+%d mean %+.2f%% median %+.2f%% win %.0f%%" % (K, 100 * m, 100 * md, 100 * w) for m, K, md, w in res[:3]],
              100 * [m for m, K, md, w in res if K == 50][0]))
