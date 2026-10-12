"""p11: the remaining numbers for the report (offline): launches by 6-hour slice and calldata length; per-day rates; the outside-buy
contrast with a Fisher test; the p08 lead (buy +60, sell +600) at $5 on the 48 h and census value launches. -> p11_extra.out"""
import sys, os, json, time, statistics as S, collections as C, pickle
from math import comb
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import common as K
X = K.launches(); E = K.events(); P6 = json.load(open(K.J("p06_pools.json"))); meta = json.load(open(K.J("p01_meta.json")))
L = []
def P(*a): L.append(" ".join(str(v) for v in a)); print(*a)
f = lambda t: time.strftime("%m-%d %H:%M", time.gmtime(t))
lens = sorted(set(x["len"] for x in X))
P("LAUNCHES BY 6-HOUR SLICE (UTC) AND CALLDATA LENGTH (selector d27d1e00 in all 102; 356 B = value 0, every other length = value > 0)")
P("  slice start   " + " ".join(f"{l:>5d}" for l in lens) + "   all")
sl = C.defaultdict(C.Counter)
for x in X: sl[int((x["ts"] - meta["from_ts"]) // 21600)][x["len"]] += 1
for k in range(8):
    P(f"  {f(meta['from_ts'] + k * 21600)}   " + " ".join(f"{sl[k][l]:>5d}" for l in lens) + f"   {sum(sl[k].values()):>3d}")
v0 = [x for x in X if x["len"] == 356]; va = [x for x in X if x["len"] != 356]
P(f"last 356-B launch: {f(v0[-1]['ts'])}:{time.gmtime(v0[-1]['ts']).tm_sec:02d} UTC block {v0[-1]['block']}; data end {f(meta['head_ts'])} UTC block {meta['head']}")
aft = [x for x in va if x["block"] > v0[-1]["block"]]; hrs = (meta["head_ts"] - v0[-1]["ts"]) / 3600
P(f"since then: {len(aft)} launches by the code, all value launches, lengths {sorted(C.Counter(x['len'] for x in aft).items())}, value ETH {sorted(set(round(x['value']/1e18,3) for x in aft))}; "
  f"{hrs:.1f} h -> {len(aft)/hrs*24:.1f}/day; value launches over the 48 h: {len(va)} ({len(va)/2:.1f}/day)")
P(f"launch wallets of the value launches since the stop: {len(set(x['from'] for x in aft))} distinct; nonce {sorted(C.Counter(x['nonce'] for x in aft).items())}")
def fisher(a, b, c, d):
    n1, n2, k = a + b, c + d, a + c; N = n1 + n2
    Pk = lambda x: comb(n1, x) * comb(n2, k - x) / comb(N, k); p0 = Pk(a)
    return sum(Pk(x) for x in range(max(0, k - n2), min(k, n1) + 1) if Pk(x) <= p0 * (1 + 1e-9))
P("\nOUTSIDE BUY >= 0.0005 ETH AT +1..+59 vs PUMPED (a fleet buy at/after +60), 48 h")
for kind, lab in (("v0", "356-B value 0"), ("val", "value launches")):
    for sub, cond in (("all", lambda r: True), ("after the census", lambda r: r["post_census"])):
        rs = [r for r in P6 if r["kind"] == kind and cond(r)]
        a = sum(1 for r in rs if r["outside_pre60"] and r["pumped"]); b = sum(1 for r in rs if r["outside_pre60"] and not r["pumped"])
        c = sum(1 for r in rs if not r["outside_pre60"] and r["pumped"]); d = sum(1 for r in rs if not r["outside_pre60"] and not r["pumped"])
        P(f"  {lab:15s} {sub:17s}: with {a+b:2d}, pumped {a:2d} | without {c+d:2d}, pumped {c:2d} | Fisher p {fisher(a, b, c, d):.3f}")
P("\nWHAT FOLLOWED THE OUTSIDE BUYS (value launches): pool, outside buys (offset, ETH, caller), first fleet buy, rule $15 return")
for r in P6:
    if r["kind"] == "val" and r["outside_pre60"]:
        P(f"  {r['pool'][:10]} {[(b[0], round(b[1], 5), b[4]) for b in r['outside_pre60']]} first fleet +{r['first_fleet']} ret {r['q15']['ret']*100:+.2f}%")
P("\nTHE p08 LEAD (buy +60, sell +600) AT $15 AND $5, 48 h value launches")
for q in (0.0058, round(5 / K.ETH_USD, 6)):
    rs = [K.trade(x, E[x["pool"]], 60, 600, q) for x in va]; rs = [r for r in rs if r and r.get("ok")]; rt = [r["ret"] for r in rs]
    P(f"  q {q}: n {len(rt)} mean {S.mean(rt)*100:+.2f}% median {S.median(rt)*100:+.3f}% win {sum(1 for v in rt if v > 0)/len(rt)*100:.1f}% pulled {sum(r['pulled'] for r in rs)} "
      f"${S.mean(rt)*q*K.ETH_USD:.3f}/trade; at the post-stop rate {len(aft)/hrs*24:.1f}/day: ${S.mean(rt)*q*K.ETH_USD*len(aft)/hrs*24:.2f}/day; top 10% of trades = "
      f"{sum(sorted(rt, reverse=True)[:max(1, len(rt)//10)])/sum(rt)*100:.0f}% of the return")
P("\nRULE +60/+260 IN $/DAY")
for kind, lab in (("v0", "356-B value 0 (48 h set)"), ("val", "value launches (48 h set)")):
    for key, usd in (("q15", 0.0058 * K.ETH_USD), ("q5", round(5 / K.ETH_USD, 6) * K.ETH_USD)):
        rs = [r for r in P6 if r["kind"] == kind and r[key] and r[key].get("ok")]; tot = sum(r[key]["ret"] for r in rs) * usd
        P(f"  {lab:27s} {'$15' if key == 'q15' else '$5 '}: n {len(rs)}, total ${tot:.2f} over 48 h = ${tot/2:.2f}/day"
          + (f"; at the post-stop rate ({len(aft)/hrs*24:.1f}/day) ${S.mean([r[key]['ret'] for r in rs])*usd*len(aft)/hrs*24:.2f}/day" if kind == "val" else ""))
open(K.J("p11_extra.out"), "w").write("\n".join(L) + "\n")
# ---- the pull margin of the +600 exit on the value launches (48 h and census)
SCR = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2"
sys.path.insert(0, SCR + "/census")
from load import load_events
F = json.load(open(SCR + "/analysis/G3/opus/families.json")); R = {r["pool"]: r for r in pickle.load(open(SCR + "/analysis/G3/opus/v3rows.pkl", "rb"))}
cv = [p for p in F["lc=89885b75|d27d1e00"] if R[p]["launch"]["calldata_len"] != 356]; CE = load_events(set(cv))
fp48 = sorted(r["first_pull"] for r in P6 if r["kind"] == "val" and r["first_pull"] is not None)
fpc = sorted(min(e[1] for e in CE[p]["ev"] if e[0] == "b" and e[8] > 0) - CE[p]["lb"] for p in cv if any(e[0] == "b" and e[8] > 0 for e in CE[p]["ev"]))
P(f"\nFIRST PULL OFFSETS, value launches: 48 h {len(fp48)} of 45: {fp48}; census {len(fpc)} of {len(cv)}: smallest {fpc[:8]}, <= +600: {sum(1 for v in fpc if v <= 600)}, <= +700: {sum(1 for v in fpc if v <= 700)}")
open(K.J("p11_extra.out"), "w").write("\n".join(L) + "\n")
