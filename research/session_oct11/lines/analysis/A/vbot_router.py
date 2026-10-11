"""Step 3: non-vbot pools touched by the volume bot's router 0x1cbaf24d (frb or any of the first 12 swaps), and the vbot skeletons
(037449b1, aff2095f) at other launch values; also every value > 0 group of the 1444-byte ETH no-hook shape with its first-buy routers."""
from common import *
VR = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
rows = rows_nonvbot(); allr = [r for r in all_rows() if not r["quote_pair"]]
fr = [r for r in rows if r.get("frb") and r["frb"]["to"] == VR]
s12 = [r for r in rows if any(s[4] == VR for s in r.get("swaps12") or [])]
print("non-vbot pools whose frb went to the vbot router:", len(fr), " with any of first-12 swaps via it:", len(s12))
for r in s12[:20]:
    print("  ", r["launch_utc"], f"{r['launch']['value_wei']/1e18:.10g}", r["launch"]["calldata_len"], r["fee"], r["tick_spacing"], r["quote"], r["fam"]["tok"][:8], r["known_fp"],
          [(s[0], s[1], round(s[2], 4), s[4][:10]) for s in r["swaps12"] if s[4] == VR][:3])
print("\nvbot router in whole lc family (incl. vbot): frb via it by known_fp/value:",
      C.Counter((r["known_fp"], f"{r['launch']['value_wei']/1e18:.10g}") for r in allr if r.get("frb") and r["frb"]["to"] == VR).most_common(10))
# vbot pools that do NOT carry the vbot values -> none expected
for sk in ("037449b1", "aff2095f"):
    rs = [r for r in allr if r["fam"]["tok"].startswith(sk)]
    print(f"\nskeleton {sk}: {len(rs)} pools; by (value, clen, fee/ts, quote, known_fp):")
    for k, n in C.Counter((f"{r['launch']['value_wei']/1e18:.10g}", r["launch"]["calldata_len"], f"{r['fee']}/{r['tick_spacing']}", r["quote"], r["known_fp"]) for r in rs).most_common(14):
        print("   ", k, n)
    nv = [r for r in rs if not is_vbot(r)]
    print("   non-vbot:", len(nv), "with frb:", sum(1 for r in nv if r.get("frb")), " value>0:", sum(1 for r in nv if r["launch"]["value_wei"] > 0),
          " value>0 values:", C.Counter(f"{r['launch']['value_wei']/1e18:.10g}" for r in nv if r["launch"]["value_wei"] > 0).most_common(8))
# 1444 ETH no-hook value>0: every value with >= 3 launches
ok = [r for r in rows if r["launch"]["calldata_len"] == 1444 and r["quote"] == "ETH" and r["hooks"] == "0x" + "0" * 40 and r["launch"]["value_wei"] > 0]
g = C.defaultdict(list)
for r in ok: g[r["launch"]["value_wei"]].append(r)
print(f"\n1444-byte ETH no-hook value>0 (non-vbot): {len(ok)} pools, {len(g)} distinct values; values with >= 3 launches:")
for v, rs in sorted(g.items(), key=lambda kv: -len(kv[1])):
    if len(rs) < 3: continue
    frb = [r["frb"] for r in rs if r.get("frb")]
    print(f"  {v/1e18:.18g} n={len(rs)} days={[sum(1 for r in rs if day_of(r)==d) for d in range(7)]} wal={len({r['launch']['from'] for r in rs})} nonce50={pct([r['launch']['nonce'] for r in rs],.5)} "
          f"fee={C.Counter(r['fee'] for r in rs).most_common(2)} ts={C.Counter(r['tick_spacing'] for r in rs).most_common(1)} sqrtL={len({(r['sqrt_p0'], r['dec'] and r['dec'].get('mint_liq')) for r in rs})} tok={C.Counter(r['fam']['tok'][:8] for r in rs).most_common(2)} "
          f"anybuy={sum(1 for r in rs if r.get('n_buys'))} fb_off={p1050([r['first_buy_off'] for r in rs if r.get('first_buy_off') is not None])} frb={len(frb)} frb_off={p1050([f['off'] for f in frb])} "
          f"frb_to={C.Counter(f['to'][:10] for f in frb).most_common(2)} pulled={sum(1 for r in rs if r.get('n_pulls'))} pull_off50={pct([r['first_pull_off'] for r in rs if r.get('n_pulls')],.5)}")
