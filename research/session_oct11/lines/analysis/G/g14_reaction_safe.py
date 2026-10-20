"""reaction-adjusted grid for the lines whose operator pulls after outside buys: the delay from a stranger's buy to the pull (all fetched buys,
shared fingerprints excluded), then the V selection with every trade whose sell lands more than R blocks after our buy counted as -100%
(R = the 10th percentile of that delay: the operator's pull would come before our sell)"""
from gstats import *
kept = json.load(open(os.path.join(G, "families_kept.json")))
rows = {r["pool"]: r for r in load_rows()}
fams = [k for k in kept if any(k.endswith(s) for s in ("|2.4333285", "|1444|10000|200|nohook|ETH|3.0000000", "|1444|10000|200|nohook|ETH|5.0000000",
                                                       "|2276|100|1|nohook|ETH|0.0000000", "|6276cbbe|196|500|1|nohook|ETH|0.0000000"))] + ["tok=tok:037449b17ce607befceb30d243903e3bbe4542ec090ed8eb9ee79edb4000170a"]
want = set(p for k in fams for p in kept[k])
out = {}
with open(os.path.join(CEN, "pools.jsonl")) as f:
    for line in f:
        if not line.startswith('{"dex":"v4"'): continue
        r = json.loads(line)
        if r["pool"] in want: out[r["pool"]] = r["outsider"]
grid = load_grid(0.0058)
for fk in fams:
    pools = kept[fk]
    delays = [out[p].get("nf_pull_after_last") for p in pools if out[p] and out[p].get("nf_n") and out[p].get("nf_pull_after_last") is not None]
    R = int(pct(delays, 0.1)) if delays else None
    print(f"\n{fk[:100]}\n  stranger buy -> pull delay (blocks) n {len(delays)} p10/50/90 {[pct(delays, q) for q in (0.1, 0.5, 0.9)]}; R = {R}")
    if R is None: continue
    rs = [rows[p] for p in pools]; ts = np.array([r["launch_ts"] for r in rs]); fit = ts < FIT_END; val = ~fit; sl = np.array([slice6(t) for t in ts]); l24 = ts >= LAST24
    ret, pulled, so = fam_returns(grid, pools)
    S = so - np.array(gsim.KS)[None, :, None]                       # blocks from our buy to our sell
    adj = np.where(S > R, -1.0 - (0.02 / ETH_USD) / 0.0058, ret); adj[np.isnan(ret)] = np.nan
    fm, fc, fs = agg(adj, fit); vm, vc, vs = agg(adj, val)
    n3 = np.zeros(fm.shape, int); p3 = np.zeros(fm.shape, int)
    for s in range(28):
        msk = sl == s
        if msk.sum() >= 3:
            m_, c_, _ = agg(adj, msk); n3 += c_ >= 3; p3 += (c_ >= 3) & (m_ > 0)
    ok = (np.arange(18)[:, None] >= 1) & (fc >= 10) & (fm > 0) & (vc >= 5) & (vm > 0)
    clean = ok & (n3 == p3); use = clean if clean.any() else ok
    if not use.any(): print("  no rule positive on fit and validation once a pull R blocks after our buy is assumed"); continue
    a = int(np.argmax(np.where(use, vs, -np.inf))); ki, ri = a // gsim.NR, a % gsim.NR
    v = one(adj[val, ki, ri], pulled[val, ki, ri]); al = one(adj[:, ki, ri], pulled[:, ki, ri]); la = one(adj[l24, ki, ri], pulled[l24, ki, ri])
    print(f"  best rule if the pull comes R blocks after our buy: {gsim.rule_name(gsim.KS[ki], ri)} ({'every slice +' if clean.any() else 'some slice -'} {p3[ki, ri]}/{n3[ki, ri]}): "
          f"val n {v['n']} mean {v['mean']*100:+.1f}% med {v['median']*100:+.1f}% win {v['win']:.0%} ${v['mean']*0.0058*ETH_USD*v['n']/2:.0f}/day; all {al['mean']*100:+.1f}%; last 24 h {la.get('mean', float('nan'))*100:+.1f}% n {la['n']}")
