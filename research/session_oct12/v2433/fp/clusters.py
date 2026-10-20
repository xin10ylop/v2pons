"""Fingerprint clusters for s03's launches: named families by exact rules, everything else by (to, selector, calldata length, fee, tick spacing)."""
import json
from common import p, POSM, V2433
E = "0x" + "0" * 40
OPA = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
SS_SQRTP = "1582215647010059227437223098794680"   # filled from the data at load (see fam)
def fam(r):
    v = int(r["value"]); to = r["to"]; eth = r["c0"] == E; h0 = r["hooks"] == E
    if to == POSM and r["clen"] == 1444 and eth and h0:
        if v == V2433: return "VB 2.4333 (fee %d)" % r["fee"]
        if v == 3 * 10 ** 18 and r["fee"] == 10000: return "VB 3.0"
        if v == 5 * 10 ** 18 and r["fee"] == 10000: return "VB 5.0"
        if 9333333333333333000 <= v <= 9333333333333334000: return "VB 9.333"
        if v == 4 * 10 ** 18 and 10000 < r["fee"] < 10500: return "VB 4.0 (fees 1005x)"
        if v in (32 * 10 ** 18,) or 33333333333333333000 <= v <= 33333333333333334000 or v == 40 * 10 ** 18: return "VB big (32/33.3/40)"
        if v == 2 * 10 ** 18 and 10000 < r["fee"] < 10500: return "VB 2.0 (fees 100xx)"
    if to == OPA: return "operator A (0x3194e326)"
    if to == POSM and r["clen"] == 2276 and r["fee"] == 100 and r["ts"] == 1 and v == 0: return "C-1 (POSM 2276 B, fee 100/ts 1)"
    if r["fee"] == 2500 and r["ts"] == 25 and r["lo"] == -160100 and r["hi"] == 198050: return "single-sided 2500/25 (NFT to 0x23f82095)"
    return "other %s %s %dB fee %d ts %d%s" % ((to or "CREATE")[:10], r["sel"], r["clen"], r["fee"], r["ts"], "" if eth else " non-ETH")
def load():
    rows = [json.loads(l) for l in open(p("s03_launches_cache.jsonl"))]
    for r in rows: r["fam"] = fam(r)
    return rows
