"""Step 7: the reaction. Every buy or sell by anyone other than the fleet routers and the sentinel, from the launch to the pull:
its offset from the launch and from the fleet's first buy T, size, and the pull's lag after it; what the fleet did afterwards."""
import collections
from common import *
pools = load_pools()
head = jload("s04_head.json")["head"]
rows = []; per_wallet = collections.defaultdict(list)
for p in pools:
    T = p["T"]; pull = p.get("pull_off")
    sw = p["swaps"]
    others = [s for s in sw if s["k"] in ("other", "r57", "?")]
    for s in others:
        later_fleet = [x for x in sw if x["k"] == "fleet" and x["a0"] < 0 and (x["bn"], x["li"]) > (s["bn"], s["li"])]
        r = dict(pid=p["pid"][:10], L=p["L"], k=s["k"], f=s["f"], to=s["to"], n=s["n"], o=s["o"], dT=(s["o"] - T) if T is not None else None,
                 eth=-s["a0"] / 1e18, side="buy" if s["a0"] < 0 else "sell", pull=pull, lag=(pull - s["o"]) if pull is not None else None,
                 fleet_after=len(later_fleet), fleet_eth_after=sum(-x["a0"] for x in later_fleet) / 1e18, before_T=(T is None or s["o"] < T))
        rows.append(r)
        if s["k"] != "r57": per_wallet[s["f"]].append(r)
print("pools", len(pools), "pulled", sum("pull_bn" in p for p in pools), "head", head)
r57 = [r for r in rows if r["k"] == "r57"]
print(f"r57 (0x57ee6646): {len(r57)} swaps in {len({r['pid'] for r in r57})} pools, sizes {collections.Counter(round(r['eth'],6) for r in r57).most_common(3)},"
      f" before T in {sum(r['before_T'] for r in r57)}, pull lag after it p10/50/min {sorted(r['lag'] for r in r57 if r['lag'] is not None)[len(r57)//10] if r57 else None}/"
      f"{sorted(r['lag'] for r in r57 if r['lag'] is not None)[len(r57)//2] if r57 else None}/{min((r['lag'] for r in r57 if r['lag'] is not None), default=None)}")
print("\nEvery swap by anyone else (k other or unknown tx):")
oth = [r for r in rows if r["k"] != "r57"]
for r in sorted(oth, key=lambda r: (r["L"], r["o"])):
    print(f"  pool {r['pid']} L {r['L']} {r['side']} {r['eth']:+.6f} by {r['f']} (nonce {r['n']}) via {str(r['to'])[:10]} at +{r['o']} (T{'+' if (r['dT'] or 0)>=0 else ''}{r['dT']})"
          f" -> pull +{r['pull']} lag {r['lag']}, fleet buys after {r['fleet_after']} ({r['fleet_eth_after']:.3f} ETH)")
# first outside buy per pool (non-r57, non-dust >= 0) and lag to pull
first = {}
for r in sorted(oth, key=lambda r: (r["L"], r["o"])):
    if r["side"] == "buy" and r["pid"] not in first: first[r["pid"]] = r
lags = sorted(r["lag"] for r in first.values() if r["lag"] is not None)
print("\npools with an outside buy:", len(first), "before T:", sum(r["before_T"] for r in first.values()),
      "| pull lag after the first outside buy:", lags)
print("pulled within 10 blocks of it:", sum(1 for x in lags if x <= 10), "of", len(lags))
nopull = [p for p in pools if p["pid"][:10] not in first]
nl = sorted(p.get("pull_off", 10**9) for p in nopull)
print("pools without an outside buy:", len(nopull), "pull offset p10/50/90", nl[len(nl)//10], nl[len(nl)//2], nl[9*len(nl)//10], "min", nl[:6])
print("\nper outside wallet:")
for f, rs in sorted(per_wallet.items(), key=lambda kv: -len(kv[1])):
    print(f"  {f}: {len(rs)} swaps in {len({r['pid'] for r in rs})} pools, buys {sum(r['side']=='buy' for r in rs)} ({sum(r['eth'] for r in rs if r['side']=='buy'):.6f} ETH),"
          f" sells {sum(r['side']=='sell' for r in rs)} ({-sum(r['eth'] for r in rs if r['side']=='sell'):.6f} ETH back)")
jdump(rows, "s07_reaction.json")
