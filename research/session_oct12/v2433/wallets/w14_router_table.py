"""Hourly samples (w07): transactions to the volume bot router 0x1cbaf24d per hour by selector and line, the callers (EOAs), and how many
of them are the v2.433 buyer wallets retired at 02:12 Oct 12. Rates are per 1,000 sampled blocks (about 100 s), scaled to an hour."""
from common import *
import collections
S = jl(J("w07_sample.jsonl"))
ini = jl(J("w01_inits_cache.jsonl")); ltx = {t["h"]: t for t in jl(J("w02_ltx_cache.jsonl"))}
tok2fam = {}
for r in ini:
    t = ltx.get(r["tx"])
    if t and r["c0"] == "0x" + "0" * 40:
        tok2fam[r["c1"]] = {2.4333285: "v2.433", 3.0: "v3.0", 5.0: "v5.0"}.get(round(int(t["v"]) / 1e18, 7), "other")
lw2fam = {t["f"]: {2.4333285: "v2.433", 3.0: "v3.0", 5.0: "v5.0"}.get(round(int(t["v"]) / 1e18, 7), "other") for t in ltx.values() if t["to"] == POSM}
retired = set(json.load(open(J("w05_buyers_now.json")))["ws"])
try:
    ch = json.load(open(J("w06_chain.json"))); retired |= {e["f"] for e in ch["events"] if e["nonce"] > 30000}
except Exception: pass
callers_by_hour = {}
print(f"{'hour':>12} {'blocks':>6} {'bot txs':>7} {'per h':>6}  by selector/line; callers; of them v2.433 buyers")
allc = collections.defaultdict(set)
for d in S:
    rows = [r for r in d["rows"] if r["to"] == BOT]
    c = collections.Counter(); callers = set()
    for r in rows:
        sel = r["sel"]
        if sel == "0xc1120e3d" and len(r["inp"]) >= 10 + 64 * 9:
            tok = "0x" + r["inp"][10 + 64 * 2 + 24: 10 + 64 * 3]; fee = int(r["inp"][10 + 64 * 7: 10 + 64 * 8], 16); ts = int(r["inp"][10 + 64 * 8: 10 + 64 * 9], 16)
            fam = tok2fam.get(tok, f"pool<12:00 {fee}/{ts}"); c[("buy", fam)] += 1
        elif sel in ("0x7422a284", "0xa0f7978d"): c[({"0x7422a284": "deploy", "0xa0f7978d": "pull"}[sel], lw2fam.get(r["f"], "?"))] += 1
        else: c[(sel, "")] += 1
        callers.add(r["f"]); allc[d["hour"]].add(r["f"])
    scale = 3600 / max(1, (d["n"] / 9.79))
    print(f"{utc(d['hour']):>12} {d['n']:>6} {len(rows):>7} {len(rows) * scale:>6.0f}  {dict(sorted(c.items(), key=lambda kv: -kv[1]))}; callers {len(callers)}; v2.433 buyers {len(callers & retired)}")
print("v2.433 buyer wallets known:", len(retired))
pre = set().union(*[allc[h] for h in allc if h < 1791770400]); post = set().union(*[allc[h] for h in allc if h >= 1791774000])
print("callers seen before 02:00:", len(pre), "after 03:00:", len(post), "in both:", len(pre & post), "after-only:", len(post - pre))
# clones: the bot's selectors sent to any other address in the sampled blocks
blk = J("w07_blk_cache.jsonl"); sels = {"0xc1120e3d", "0x7422a284", "0xa0f7978d"}
other = collections.Counter(); tot = collections.Counter(); creations = []
for l in open(blk):
    r = json.loads(l)
    for t in r["txs"]:
        if t["sel"] in sels:
            tot[t["to"] == BOT] += 1
            if t["to"] != BOT: other[(t["to"], t["sel"])] += 1
        if t["to"] == "": creations.append((r["n"], t["h"], t["f"]))
print("bot selectors in sampled blocks: to the router", tot[True], "| to any other address", sum(other.values()), other.most_common(5))
json.dump(creations, open(J("w14_creations.json"), "w"))
print("contract creations (to = empty) in sampled blocks:", len(creations))
