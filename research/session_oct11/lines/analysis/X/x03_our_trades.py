"""Question 1: our sell timing. Every relay trade on a 2.433/3.0 pool, Oct 10-11: buy offset from launch, the bot's T, our sell (blocks after
our buy, and relative to T), our return from the swap amounts, the pull; per 6-hour period. Then what the price did between our buy and T:
the value of our tokens at the end of every block from our buy to T-1 (v4math on the pool state after that block's last swap), and the value
right behind the bot's buy in T's own block, against the actual sell."""
import json, pickle, collections, statistics as st, sys
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
from xcommon import *
D = pickle.load(open("x02_pools.pkl", "rb")); P = {p["pid"]: p for p in D["pools"]}
trades = json.load(open("x02_trades.json"))
def pc(v, q):
    v = sorted(v); return v[min(len(v) - 1, int(q * len(v)))] if v else None
def dist(v): return f"{pc(v,.1)}/{pc(v,.5)}/{pc(v,.9)}" if v else "-"
rows = []
for t in trades:
    if t["line"] == "other" or t["buy_bn"] is None: continue
    p = P[t["pid"]]; lb = p["lb"]; T = p["T"]; Tbn = lb + T if T is not None else None
    r = dict(t, period=period(p["ts"]), buy_off=t["buy_bn"] - lb, T=T, T_q=p["T_q"], pull=p["pull"], fee=p["fee"])
    r["sell_after_buy"] = t["sell_bn"] - t["buy_bn"] if t["sell_bn"] else None
    r["sell_rel_T"] = (t["sell_bn"] - Tbn) if (t["sell_bn"] and Tbn) else None
    r["ret"] = (t["eth_out"] - t["eth_in"]) / t["eth_in"] if t["eth_out"] is not None and t["eth_in"] else None
    r["pull_rel_T"] = p["pull"] - T if (p["pull"] is not None and T is not None) else None
    r["pull_rel_sell"] = (lb + p["pull"] - t["sell_bn"]) if (p["pull"] is not None and t["sell_bn"]) else None
    # the bot's buy: ahead of or behind our buy in the order of the chain
    r["bot_before_us"] = T is not None and p["T_li"] < (t["buy_bn"], t["buy_li"])
    # price path: our tokens' value at the end of each block after our buy, up to the block before T; and right behind the bot's buy
    sw = p["sw"]; tok = t["tok"]; fee = p["fee"]; path = []
    if tok and T is not None and not r["bot_before_us"]:
        # state after our buy
        k = next(i for i, s in enumerate(sw) if s["who"] == "ours" and s["buy"])
        sp, L = sw[k]["sp"], sw[k]["L"]
        endb = {}
        for s in sw[k + 1:]:
            if (s["bn"], s["li"]) >= p["T_li"]: break
            if s["who"] == "ours": continue
            endb[s["bn"]] = (s["sp"], s["L"])
        cur = (sp, L)
        for b in range(t["buy_bn"], Tbn):
            if b in endb: cur = endb[b]
            path.append((b - t["buy_bn"], v4math.sell_out_int(cur[0], cur[1], tok, fee) / t["eth_in"] - 1))
        bot = next(s for s in sw if (s["bn"], s["li"]) == p["T_li"])
        r["ret_behind_T"] = v4math.sell_out_int(bot["sp"], bot["L"], tok, fee) / t["eth_in"] - 1
        # who traded between our buy and the bot's buy (others' buys/sells, ETH)
        mid = [s for s in sw[k + 1:] if (s["bn"], s["li"]) < p["T_li"] and s["who"] != "ours"]
        r["mid_buy_eth"] = sum(s["q"] for s in mid if s["buy"]) / 1e18; r["mid_sell_eth"] = sum(s["q"] for s in mid if not s["buy"]) / 1e18
        r["mid_n"] = len(mid)
    else:
        r["ret_behind_T"] = None
    r["path"] = path
    r["best_pre_T"] = max((v for _, v in path), default=None)
    r["immediate"] = path[0][1] if path else None
    rows.append(r)
json.dump([{k: v for k, v in r.items()} for r in rows], open("x03_rows.json", "w"))
print(f"our relay trades on the lines: {len(rows)} (2.433 {sum(1 for r in rows if r['line']=='2.433')}, 3.0 {sum(1 for r in rows if r['line']=='3.0')}); "
      f"other pools (follow etc.): {sum(1 for t in trades if t['line']=='other')}")
print(f"wallets that sent our buys: {collections.Counter(r['eoa'] for r in rows)}")
print("\n=== per 6-hour period (2.433 line): n, stake mix, buy offset, T, sell after buy, sell vs T, return, pull vs T, pull vs our sell")
print(f"{'period':12s} {'n':>4s} {'stakes (ETH:n)':34s} {'buy@':>6s} {'T p10/50/90':>11s} {'sell-buy':>9s} {'sell-T dist':40s} {'ret% p10/50/90':>18s} {'mean%':>6s} {'pull-T':28s} {'pull-sell':22s} {'$net':>7s}")
for per in sorted(set(r["period"] for r in rows), key=lambda s: (s[3:5], s[6:])):
    v = [r for r in rows if r["period"] == per and r["line"] == "2.433"]
    if not v: continue
    stakes = collections.Counter(round(r["eth_in"] / 1e18, 4) for r in v).most_common(4)
    rets = [r["ret"] for r in v if r["ret"] is not None]
    srT = collections.Counter(r["sell_rel_T"] for r in v); prt = collections.Counter(r["pull_rel_T"] for r in v); prs = collections.Counter(r["pull_rel_sell"] for r in v)
    usd = sum(((r["eth_out"] or 0) - r["eth_in"]) / 1e18 * USD for r in v)
    print(f"{per:12s} {len(v):4d} {str(stakes)[:34]:34s} {str(collections.Counter(r['buy_off'] for r in v).most_common(2))[:6]:>6s} {dist([r['T'] for r in v if r['T'] is not None]):>11s} "
          f"{dist([r['sell_after_buy'] for r in v if r['sell_after_buy'] is not None]):>9s} {str(sorted(srT.items(), key=lambda kv: -kv[1])[:4])[:40]:40s} "
          f"{dist([round(100*x,1) for x in rets]):>18s} {100*st.mean(rets) if rets else 0:6.2f} {str(sorted(prt.items(), key=lambda kv: -kv[1])[:3])[:28]:28s} {str(sorted(prs.items(), key=lambda kv: -kv[1])[:3])[:22]:22s} {usd:7.1f}")
print("\nbuy offsets by period:", {per: dict(collections.Counter(r['buy_off'] for r in rows if r['period'] == per and r['line'] == '2.433')) for per in sorted(set(r['period'] for r in rows))})
print("\n=== 3.0 trades")
for r in rows:
    if r["line"] == "3.0":
        print(f"  {utc(r['ts'])} buy +{r['buy_off']} {r['eth_in']/1e18:.4f} ETH T {r['T']} sell {r['sell_after_buy']} after buy, ret {r['ret']} pull +{r['pull']}")
print("\n=== sell relative to T, Oct 10 vs Oct 11 (2.433, bot bought after our buy)")
for day in ("Oct10", "Oct11"):
    v = [r for r in rows if r["line"] == "2.433" and r["period"].startswith(day) and r["T"] is not None and not r["bot_before_us"]]
    c = collections.Counter(r["sell_rel_T"] for r in v)
    print(f"  {day}: n {len(v)}; sell at T+k: " + ", ".join(f"{k}: {n}" for k, n in sorted(c.items(), key=lambda kv: (kv[0] is None, kv[0] if kv[0] is not None else 0))))
    print(f"         buy offset: {dict(collections.Counter(r['buy_off'] for r in v))}; T: {dist([r['T'] for r in v])}; sell-after-buy: {dist([r['sell_after_buy'] for r in v if r['sell_after_buy']])}; "
          f"T - buy: {dist([r['T'] - r['buy_off'] for r in v])}")
print("\n=== could we have sold earlier? (2.433, trades with the bot's buy after ours)")
for day in ("Oct10", "Oct11"):
    v = [r for r in rows if r["line"] == "2.433" and r["period"].startswith(day) and r["path"]]
    imm = [100 * r["immediate"] for r in v]; best = [100 * r["best_pre_T"] for r in v]; act = [100 * r["ret"] for r in v if r["ret"] is not None]; bt = [100 * r["ret_behind_T"] for r in v if r["ret_behind_T"] is not None]
    print(f"  {day}: n {len(v)}; value of our tokens at the end of our buy's block: p10/50/90 {dist([round(x,2) for x in imm])}%; best block before T: {dist([round(x,2) for x in best])}% "
          f"(max {max(best):.2f}%, > +1%: {sum(1 for x in best if x > 1)}); right behind the bot's buy: {dist([round(x,2) for x in bt])}%; actual: {dist([round(x,2) for x in act])}%")
    print(f"         others between our buy and T: buys ETH p50/p90 {pc([r['mid_buy_eth'] for r in v],.5):.5f}/{pc([r['mid_buy_eth'] for r in v],.9):.5f}, sells ETH p50/p90 {pc([r['mid_sell_eth'] for r in v],.5):.5f}/{pc([r['mid_sell_eth'] for r in v],.9):.5f}")
