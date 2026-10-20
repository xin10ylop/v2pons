"""The wallets behind the decoy-router buys in the volume bot's pools (v2.433 / v3.0 / v5.0), Oct 11 12:00 to the head: from, nonce, value."""
from common import *
import collections, bisect
exec(open(J("w09_decoy_table.py")).read().split("print(len(sw)")[0])
buys = [x for x in sw if x["a0"] < 0 and fam(x["pid"]) in ("v2.433", "v3.0", "v5.0")]
OUT = J("w10_dtx_cache.jsonl"); have = {d["h"] for d in jl(OUT)}
need = sorted({x["tx"] for x in buys} - have)
with open(OUT, "a") as f:
    for i in range(0, len(need), 20):
        ch = need[i:i + 20]
        for hsh, t in zip(ch, rpc.batch("eth_getTransactionByHash", [[x] for x in ch], n=20)):
            if t: f.write(json.dumps({"h": hsh, "f": t["from"].lower(), "nonce": int(t["nonce"], 16), "v": str(int(t["value"], 16)), "to": (t.get("to") or "").lower(), "tip": int(t.get("maxPriorityFeePerGas", "0x0"), 16), "mf": int(t.get("maxFeePerGas", t.get("gasPrice", "0x0")), 16)}) + "\n")
tx = {d["h"]: d for d in jl(OUT)}
rows = []
for x in buys:
    t = tx.get(x["tx"])
    if t: rows.append((T(x["b"]), x["r"][:10], fam(x["pid"]), t["f"], t["nonce"], int(t["v"]) / 1e18, -x["a0"] / 1e18))
rows.sort()
for r in (DECOY_R[:10], FRONT_R2[:10]):
    rr = [x for x in rows if x[1] == r]
    print(f"\n== router {r}: {len(rr)} buys in the bot's lines; wallets {len({x[3] for x in rr})}; fresh (nonce<=1) {sum(1 for x in rr if x[4] <= 1)}")
    ww = collections.defaultdict(list)
    for x in rr: ww[x[3]].append(x)
    rec = sorted(((len(v), w, v) for w, v in ww.items() if len(v) >= 3), reverse=True)
    for n, w, v in rec[:10]:
        print(f"  recurring {w} {n} buys, nonce {v[0][4]}..{v[-1][4]}, {utc(v[0][0])}..{utc(v[-1][0])}, lines {dict(collections.Counter(x[2] for x in v))}, size p50 {sorted(x[6] for x in v)[len(v)//2]:.6f}")
    c = collections.defaultdict(collections.Counter)
    for x in rr: c[time.strftime("%m-%d %H", time.gmtime(x[0]))][(x[2], "fresh" if x[4] <= 1 else "recurring")] += 1
    for hh in sorted(c): print("  ", hh, dict(c[hh]))
    if rr: print("  last 5:", [(utc(x[0]), x[2], x[3][:10], x[4], round(x[6], 6)) for x in rr[-5:]])
print(rpc.STATS)
