"""Step 4: one row per launch (v4 Initialize and V3 PoolCreated, Oct 12 00:00 UTC -> s01 head) with its shape key
(tx target, selector, calldata length, fee, tick spacing, ETH value to 4 significant digits, quote), the known-family label, and the family table.
Writes s04_launches.json (compact rows) and prints s04_shapes.out."""
import collections
from common import *
bt = BT()
TX = {r["h"]: r for r in jl_load("s02_tx_cache.jsonl") if "miss" not in r}
QUOTES = {E: "ETH", WETH: "WETH", USDG: "USDG"}
EP = "0x5ff137d4b0fdcd49dca30c7cf57e578a026d2789"
OPA = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
def vr(v):
    v = int(v)
    return "0" if v == 0 else "%.4g" % (v / 1e18)
def known(r):
    v = int(r["v"]); to = r["to"]; q = r["q"]
    if r["ven"] == "v4":
        if to == POSM and r["clen"] == 1444 and q == "ETH" and r["hook"] == E and r["fee"] == 10000 and r["ts"] == 200 and v in (3 * 10**18, 5 * 10**18):
            return "VB %.1f" % (v / 1e18)
        if to == POSM and r["clen"] == 1444 and v == V2433: return "VB 2.433"
        if to == POSM and r["clen"] == 2276: return "C-1 (POSM 2276 B)"
        if to == PM and r["clen"] == 196 and r["fee"] == 500 and r["ts"] == 1 and q == "ETH": return "pm500 direct init" + (" (hooked)" if r["hook"] != E else "")
        if r["hook"].startswith("0x4e346895"): return "S1 coin factory hook 0x4e346895"
        if r["hook"].startswith("0x2c668601") or r["sel"] == "0x7866fa39": return "S2 lift.fun 7866fa39"
        if r["sel"] == "0xa25a9a3d": return "S3 a25a9a3d"
        if r["sel"] == "0x7fde822e": return "S4 7fde822e launchpads"
        if to == OPA: return "operator A"
        if r["fee"] == 2500 and r["ts"] == 25 and q == "ETH": return "single-sided 2500/25 (REPORT_2433STOP)"
    else:
        if to == NPM3 and r["clen"] == 836: return "V3 crowd (836 B NPM)"
    return ""
rows = []
for l in jl_load("s01_v4init_cache.jsonl"):
    d = l["d"]; c0 = "0x" + l["t"][2][-40:]; c1 = "0x" + l["t"][3][-40:]
    tx = TX.get(l["h"]); 
    if not tx: continue
    q = QUOTES.get(c0) or QUOTES.get(c1) or ("c0:" + c0[:10])
    tok = c1 if c0 in QUOTES else (c0 if c1 in QUOTES else c1)
    r = dict(ven="v4", b=l["b"], t=round(bt(l["b"])), h=l["h"], li=l["li"], pid=l["t"][1], c0=c0, c1=c1, tok=tok, q=q, fee=W(d, 0), ts=sgn(W(d, 1)),
             hook="0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3], sqrtp=str(W(d, 3)), tick=sgn(W(d, 4)),
             frm=tx["from"], to=tx["to"], sel=tx["in"][:10], clen=(len(tx["in"]) - 2) // 2, v=tx["v"], n=tx["n"], gas=tx["gas"], gp=tx["gp"], idx=tx["idx"])
    rows.append(r)
for l in jl_load("s01_v3pc_cache.jsonl"):
    d = l["d"]; t0 = "0x" + l["t"][1][-40:]; t1 = "0x" + l["t"][2][-40:]
    tx = TX.get(l["h"])
    if not tx: continue
    q = QUOTES.get(t0) or QUOTES.get(t1) or ("t0:" + t0[:10])
    tok = t1 if t0 in QUOTES else (t0 if t1 in QUOTES else t1)
    r = dict(ven="v3", b=l["b"], t=round(bt(l["b"])), h=l["h"], li=l["li"], pid="0x" + d[2 + 64 + 24: 2 + 128], c0=t0, c1=t1, tok=tok, q=q,
             fee=int(l["t"][3], 16), ts=sgn(W(d, 0)), hook=E, sqrtp="", tick=None,
             frm=tx["from"], to=tx["to"], sel=tx["in"][:10], clen=(len(tx["in"]) - 2) // 2, v=tx["v"], n=tx["n"], gas=tx["gas"], gp=tx["gp"], idx=tx["idx"])
    rows.append(r)
rows.sort(key=lambda r: (r["b"], r["li"]))
for r in rows:
    r["key"] = "%s %s %s %dB f%d ts%d v%s %s" % (r["ven"], (r["to"] or "CREATE")[:10], r["sel"], r["clen"], r["fee"], r["ts"], vr(r["v"]), r["q"])
    r["fam"] = known(r)
jdump(rows, "s04_launches.json")
print("launches", len(rows), "v4", sum(r["ven"] == "v4" for r in rows), "v3", sum(r["ven"] == "v3" for r in rows), "missing tx", len(jl_load("s01_v4init_cache.jsonl")) + len(jl_load("s01_v3pc_cache.jsonl")) - len(rows))
H = (rows[-1]["t"] - rows[0]["t"]) / 3600
print("window %s .. %s (%.1f h)" % (hm(rows[0]["t"]), hm(rows[-1]["t"]), H))
kf = collections.Counter(r["fam"] for r in rows if r["fam"])
print("\n== known families (excluded)"); [print("%6d  %s" % (v, k)) for k, v in kf.most_common()]
fams = collections.defaultdict(list)
for r in rows:
    if not r["fam"]: fams[r["key"]].append(r)
print("\n== other shape keys:", len(fams), "keys,", sum(len(v) for v in fams.values()), "launches;", sum(1 for v in fams.values() if len(v) >= 15), "keys with >= 15")
print("%5s %5s %5s %6s %-62s %s" % ("n", "/day", "senders", "hooks", "key", "first..last, sender nonce p50"))
for k, v in sorted(fams.items(), key=lambda kv: -len(kv[1])):
    if len(v) < 8: continue
    snd = len({r["frm"] for r in v}); hk = collections.Counter(r["hook"][:10] for r in v)
    ns = sorted(r["n"] for r in v)
    print("%5d %5.0f %5d %6s %-62s %s..%s n50=%d hooks=%s" % (len(v), len(v) / H * 24, snd, len(hk), k, hm(v[0]["t"]), hm(v[-1]["t"]), ns[len(ns) // 2], dict(hk.most_common(2))))
