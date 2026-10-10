import sys, json, collections
sys.path.insert(0, '.')
exec(open('react.py').read().split("ops = sorted")[0])
ops = sorted([p for p in P if launcher[p] == OP], key=lambda p: P[p]["bn"])
rows = json.load(open("react_rows.json"))
for r in rows:
    if r["gap"] is not None and r["gap"] <= 4:
        p = r["p"]; b0 = P[p]["bn"]
        rems = sorted((x[0], x[1]) for x in L.get(p, []) if x[5] < 0)
        print(f"launch {p[:12]} fee {P[p]['fee']} buy {r['eth']:.4f} at +{r['off']} gap {r['gap']} first={r['first']} pull at +{rems[0][0]-b0}")
        for x, ro, w, t in roles(p):
            if rems[0][0] - 30 <= x[0] <= rems[0][0]:
                print(f"     +{x[0]-b0} li {x[1]} {ro:5s} {'buy' if x[3]<0 else 'sell'} {abs(x[3])/1e18:.5f} ETH w {w[:10]} to {t[1][:10]}")
# the exactly-5 floor in the 2-5% tier: is the pull's tx the first in its block? positions
