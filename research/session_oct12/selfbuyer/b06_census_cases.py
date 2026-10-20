"""B06: the reaction cases in the census (Oct 4 13:52 - Oct 11 13:52 UTC, analyst C's v23.pkl in the session scratchpad, read-only, no RPC):
every fee-100 WETH launch of lc:0a493d1a|13ead562 where anyone other than the launch wallet bought before the launcher's own first buy, in
the order of the swaps12 list (so a buy earlier in the same block counts; REPORT_S's s07 compared blocks only), or bought by +200 in a launch
with no own buy. For each case: the wallet's launches before and after. Also the line's own-first-buy size by 6-hour slice (the regime).
Writes b06_census_pools.json: the case pools and every launch of the case wallets, for an RPC re-fetch in b07. -> b06_census_cases.out"""
import sys, os, json, time
from collections import Counter, defaultdict
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/analysis/C"
sys.path.insert(0, CEN)
import fams
fams.OUT = CEN
OUT = os.path.dirname(os.path.abspath(__file__))
RC = fams.load_rows(); FP = fams.fam_pools(RC)
rs = [r for r in FP["lc:0a493d1a|13ead562"] if r["fee"] == 100 and r["quote"] == "WETH"]
out = [f"census lc:0a493d1a|13ead562 fee 100 WETH launches: {len(rs)}, {rs[0]['launch_utc']} .. {rs[-1]['launch_utc']} (census window Oct 4 13:52 - Oct 11 13:52)"]
def P(s=""): out.append(s)
def own_of(r):
    lw = r["launch"]["from"]; sw = r["swaps12"]
    i = next((i for i, s in enumerate(sw) if s[1] == "B" and s[3] == lw), None)
    return i, (sw[i] if i is not None else None)
cases = []; byw = defaultdict(list)
for r in rs:
    byw[r["launch"]["from"]].append(r)
    i, o = own_of(r); sw = r["swaps12"]; lw = r["launch"]["from"]
    pre = [s for j, s in enumerate(sw) if s[1] == "B" and s[3] != lw and (j < i if i is not None else s[0] <= 200)]
    r["_own"] = o; r["_pre"] = pre
    if pre: cases.append(r)
P(f"cases (an outside buy ahead of the own first buy, list order; or by +200 without an own buy): {len(cases)}")
for r in cases:
    w = r["launch"]["from"]; L = byw[w]; k = L.index(r)
    o = r["_own"]
    P(f"\n  {r['launch_block']} {r['launch_utc'][5:16]} wallet {w[:10]} launch {k + 1}/{len(L)} mint +{r['liq_off']} pool {r['pool']}")
    P(f"     ahead: {[(s[0], round(s[2], 5), s[3][:10], s[5], s[6]) for s in r['_pre']]}")
    P(f"     own first buy {('+%d %.4f' % (o[0], o[2])) if o else 'NONE'}; first pull {r['first_pull_off']}; swaps12 {[(s[0], s[1], round(s[2], 5), s[3][:10]) for s in r['swaps12'][:8]]}")
    for j in range(max(0, k - 2), min(len(L), k + 4)):
        x = L[j]; ox = x["_own"]
        P(f"     {'>>' if j == k else '  '} launch {j + 1}: {x['launch_block']} {x['launch_utc'][5:16]} mint +{x['liq_off']} own {('+%d %.4f' % (ox[0], ox[2])) if ox else 'NONE'} "
          f"ahead {len(x['_pre'])} pull {x['first_pull_off']}")
P("\n=== the line by 6-hour slice: launches, own first buy sizes, cases, pulls by +200")
sl = defaultdict(list)
for r in rs: sl[int(r["launch_ts"] // 21600)].append(r)
for k in sorted(sl):
    xs = sl[k]
    P(f"  {time.strftime('%m-%d %H:%M', time.gmtime(k * 21600))} n {len(xs):3d} wallets {len(set(x['launch']['from'] for x in xs)):2d} own1 {Counter(round(x['_own'][2], 4) if x['_own'] else None for x in xs).most_common(4)} "
      f"cases {sum(1 for x in xs if x['_pre'])} pulled<=+200 {sum(1 for x in xs if x['first_pull_off'] is not None and x['first_pull_off'] <= 200)}")
# pools for the RPC re-fetch: the case pools and every launch of the case wallets
want = []
for w in sorted({r["launch"]["from"] for r in cases}):
    for x in byw[w]:
        qs = x["quote_side"]
        want.append({"pool": x["pool"], "lb": x["launch_block"], "ts": int(x["launch_ts"]), "fee": x["fee"], "qs": qs, "launch_from": w,
                     "launch_nonce": x["launch"]["nonce"], "token": x["token"], "census": True, "case": bool(x["_pre"])})
json.dump(want, open(os.path.join(OUT, "b06_census_pools.json"), "w"), indent=0)
P(f"\nb06_census_pools.json: {len(want)} pools of {len({x['launch_from'] for x in want})} case wallets")
open(os.path.join(OUT, "b06_census_cases.out"), "w").write("\n".join(out) + "\n"); print("\n".join(out))
