# P(sell lands after the pull) per trade; a same-block landing is a coin flip (arrival order)
relay = {5: 1, 6: 3, 7: 1, 8: 1, 13: 1}
tier25 = {5: 36, 6: 7, 7: 2, 8: 2, 10: 1, 11: 1, 12: 2, 14: 3, 15: 1, 18: 1, 19: 1}
norm = lambda d: {k: v / sum(d.values()) for k, v in d.items()}
lat_obs = {1: 6/14, 2: 8/14}
lat_tail = {1: 0.40, 2: 0.50, 3: 0.08, 4: 0.02}
paths = {1: 0.5, 2: 0.5}          # send block after our buy: take profit (+1) on 4/8 live trades, deadline (+2) on 4/8
def p_loss(R, lat, shift=0):
    R = norm(R); tot = 0
    for s, ps in paths.items():
        for l, pl in lat.items():
            land = s + l
            for r, pr in R.items():
                r2 = max(1, r - shift)
                tot += ps * pl * pr * (1.0 if land > r2 else 0.5 if land == r2 else 0.0)
    return tot
for name, R in (("relay 7 trades", relay), ("2-5% tier, 52 reactions", tier25)):
    for lname, lat in (("latency as observed (1-2)", lat_obs), ("latency with a 10% tail at 3-4", lat_tail)):
        print(f"{name:24s} {lname:32s} " + "  ".join(f"operator {s} blk faster: {p_loss(R, lat, s):5.1%}" if s else f"as seen: {p_loss(R, lat, s):5.1%}" for s in (0, 1, 2, 3)))
# the old exit (send at +5) for comparison
paths = {5: 1.0}
print("old exit (sent at +5), relay reactions, observed latency:", f"{p_loss(relay, lat_obs):.1%}", "(live: 3 of 7 lost, 1 more won a same-block race)")
