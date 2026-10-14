"""Step 12: is the pull a reaction to an outside buy? For the first outside buy of at least `thr` ETH in a pool (age a = blocks after
the launch), compare 'pulled within W blocks' with the same-age rate in control pools (alive at a, no such buy up to a+W).
Also the fleet's buys in the W blocks after it vs the controls at the same age."""
import collections
from common import *
pools = load_pools()
DUST = {"0x353887ec7ee0d1b5fedc6c865eb282ec62dc82b0", "0xdf24e301a392a35b778e86549804bc61ae265ea3"}
def first_out(p, thr):
    for s in p["swaps"]:
        if s["k"] == "other" and s["a0"] < 0 and -s["a0"] >= thr * 1e18: return s
    return None
def fleet_buys(p, a, b): return sum(1 for s in p["swaps"] if s["k"] == "fleet" and s["a0"] < 0 and a < s["o"] <= b)
for thr in (0.00003, 0.0003, 0.001):
    ev = [(p, first_out(p, thr)) for p in pools]
    with_ = [(p, s) for p, s in ev if s]
    print(f"\n== first outside buy >= {thr} ETH: {len(with_)} pools (before T: {sum(1 for p, s in with_ if p['T'] is None or s['o'] < p['T'])})")
    for W in (5, 10, 30, 60, 100, 200, 600):
        obs = 0; exp = 0.0; fb_obs = 0; fb_exp = 0.0
        for p, s in with_:
            a = s["o"]; pull = p.get("pull_off", 10**9)
            obs += pull <= a + W
            ctrl = [q for q in pools if q.get("pull_off", 10**9) > a and (first_out(q, thr) is None or first_out(q, thr)["o"] > a + W)]
            if ctrl:
                exp += sum(q.get("pull_off", 10**9) <= a + W for q in ctrl) / len(ctrl)
                fb_exp += sum(fleet_buys(q, a, a + W) for q in ctrl) / len(ctrl)
            fb_obs += fleet_buys(p, a, a + W)
        print(f"  pulled within {W:3d}: observed {obs:3d} of {len(with_)} ({obs/len(with_):5.1%}), same-age expected {exp:5.1f} ({exp/len(with_):5.1%})"
              f" | fleet buys in that window: {fb_obs/len(with_):.2f} a pool vs {fb_exp/len(with_):.2f} same-age")
    lag = sorted(p.get("pull_off", 10**9) - s["o"] for p, s in with_)
    print("  lags:", lag[:40])
