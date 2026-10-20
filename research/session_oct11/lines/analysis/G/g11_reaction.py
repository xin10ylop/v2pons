"""the operator's reaction to outside buys, all fetched buys (census `outsider` block, biased toward pulled pools: README problem 1) and the
first-12-swap block, for the top lines; plus the 3 vbot-3.0 pools whose early stranger buy was followed by a pull"""
from common import *
kept = json.load(open(os.path.join(G, "families_kept.json")))
top = json.load(open(os.path.join(G, "g07_top.json")))[:15]
want = set(p for o in top for p in kept[o["fam"]])
full = {}
with open(os.path.join(CEN, "pools.jsonl")) as f:
    for line in f:
        if not line.startswith('{"dex":"v4"'): continue
        r = json.loads(line)
        if r["pool"] in want: full[r["pool"]] = {k: r.get(k) for k in ("outsider", "outsider12", "first_pull_off", "pull_after_last_buy", "ev_complete", "n_buys", "launch_ts", "swaps12", "pulls", "launch")}
for o in top:
    rs = [full[p] for p in kept[o["fam"]]]
    op = [r for r in rs if r["ev_complete"] and r["outsider"] and r["outsider"].get("nf_n")]
    orr = [r for r in op if r["outsider"].get("nf_reaction")]
    bp = [r for r in rs if r["ev_complete"] and r["n_buys"] and r["outsider"] is not None and r["outsider"]["n_outsider_buys"] == 0]
    bq = [r for r in bp if r.get("pull_after_last_buy") is not None and r["pull_after_last_buy"] <= 30]
    pa = [r["outsider"].get("nf_pull_after_last") for r in op if r["outsider"].get("nf_pull_after_last") is not None]
    print(f"{o['fam'][:95]:95s} all-fetched outsiders (shared fps excl.): pulled <= 30 blocks after {len(orr)}/{len(op)} ({len(orr)/max(1,len(op)):.0%}); "
          f"baseline {len(bq)}/{len(bp)} ({len(bq)/max(1,len(bp)):.0%}); pull after the outsider p50 {pct(pa,0.5)}")
fk = [k for k in kept if k.endswith("|1444|10000|200|nohook|ETH|3.0000000")][0]
print("\nvbot 3.0: pools with a first-12-swap stranger buy (shared fps excluded):")
for p in kept[fk]:
    r = full[p]; o12 = r["outsider12"] or {}
    if o12.get("nf_n"):
        print(" ", p[:14], "stranger last off", o12.get("nf_last_off"), "eth", o12.get("nf_last_eth"), "pull after", o12.get("nf_pull_after_last"), "first pull off", r["first_pull_off"],
              "| swaps12:", [(s[0], s[1], round(s[2], 4), (s[4] or "")[:10]) for s in r["swaps12"]][:12])
