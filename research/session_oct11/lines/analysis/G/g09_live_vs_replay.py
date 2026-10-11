"""calibration 2: our own engine's real round trips in the census (relay 0x2abb5653 as the Swap sender) vs the replay of the same trade
(our swaps removed, buy of the same amount at the head of our buy block, sell at the head of our sell block)"""
from gstats import *
sys.path.insert(0, CEN)
from load import load_events
import gsim2
rows = {r["pool"]: r for r in load_rows()}
EVc = pickle.load(open(os.path.join(G, "ev.pkl"), "rb"))
ours = [p for p, r in rows.items() if r["ours"] and p in EVc]
E = load_events(set(ours))
out = []; skipped = C.Counter()
for p in ours:
    r = rows[p]; qs = r["quote_side"]; L = r["launch_block"]
    mine = [e for e in E[p]["ev"] if e[0] == "s" and e[5].lower().startswith(OUR_RELAY)]
    buys = []; sells = []
    for e in mine:
        dq = e[6] if qs == 0 else e[7]
        (buys if dq < 0 else sells).append((e[1], abs(dq)))
    if len(buys) != 1 or len(sells) != 1: skipped["not one buy and one sell"] += 1; continue
    (bb, qin), (sb, qout) = buys[0], sells[0]
    s = sb - bb
    if not 1 <= s <= 200: skipped["sell not 1..200 blocks after the buy"] += 1; continue
    actual = (qout - qin) / qin
    ps = gsim2.PoolSim(r, EVc[p]); ps.gas = 0
    sk, v_end, v_max, _ = ps.path(bb - L, qin)
    if sk:
        # a pull before our real sell would be a skip here; the real trade happened
        skipped[f"replay skip {sk}"] += 1; continue
    pulled = ps.pull_bn is not None and ps.pull_bn < sb
    out.append({"pool": p, "day": day(r["launch_ts"]), "buy_off": bb - L, "hold": s, "eth": qin / 1e18, "actual": actual, "replay": float(v_end[s - 1]), "pulled_before_sell": pulled})
a = np.array([o["actual"] for o in out]); b = np.array([o["replay"] for o in out]); d = b - a
print(f"our real round trips matched: {len(out)} (skipped {dict(skipped)})")
print(f"buy offset {C.Counter(o['buy_off'] for o in out).most_common(5)}; hold blocks p10/50/90 {np.percentile([o['hold'] for o in out], [10, 50, 90])}; stake ETH median {np.median([o['eth'] for o in out]):.4f}")
print(f"actual (before gas): mean {a.mean()*100:+.2f}% median {np.median(a)*100:+.2f}% win {(a > 0).mean():.1%}")
print(f"replay (before gas): mean {b.mean()*100:+.2f}% median {np.median(b)*100:+.2f}% win {(b > 0).mean():.1%}")
print(f"replay - actual: mean {d.mean()*100:+.3f} pts, median {np.median(d)*100:+.4f} pts, |diff| p90 {np.percentile(abs(d), 90)*100:.3f} pts, p99 {np.percentile(abs(d), 99)*100:.3f} pts")
for dd in sorted(set(o["day"] for o in out)):
    m = np.array([o["day"] == dd for o in out])
    print(f"  day {dd+1}: n {m.sum()} actual {a[m].mean()*100:+.2f}% replay {b[m].mean()*100:+.2f}%")
json.dump(out, open(os.path.join(G, "g09_live_vs_replay.json"), "w"))
