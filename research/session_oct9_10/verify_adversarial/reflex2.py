import sys, collections
src = open("/home/user/v2pons/research/v4_slowrug_test.py").read()
cut = src.index('print(f"window')
sys.argv = ["x", "/home/user/v2pons/research/data/slowrug.json.gz", "/home/user/v2pons/research/data/slowrug_op.json.gz"]
g = {"__name__": "lib"}
exec(compile(src[:cut], "lib", "exec"), g)
opr = g["opr"]
# per tier and day: reaction gap from the earliest real-size non-op buy that the pull follows within 30 blocks
by = collections.defaultdict(list)
for r in opr:
    if r["pull"] is None: continue
    real = [b for b in r["nonop"] if b[0] <= r["pull"] and b[2] >= 2e-4 and r["pull"] - b[0] <= 30]
    if real: by[("2-5%" if r["fee"] >= 10000 else "<1%", r["day"])].append(r["pull"] - real[0][0])
for k in sorted(by): print(k, sorted(by[k]))
# how many real-size outside buys on the <1% tier were NOT followed by a pull within 30 blocks (no reaction at all)
n = 0; nr = 0; sizes = []
for r in opr:
    if r["fee"] >= 10000: continue
    for b in r["nonop"]:
        if b[2] < 2e-4 or b[1] != "out": continue
        n += 1; react = r["pull"] is not None and 0 <= r["pull"] - b[0] <= 30; nr += react
print("<1% tier: outside buys >=0.0002 ETH", n, "followed by a pull within 30 blocks", nr)
