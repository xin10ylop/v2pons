import sys, collections
src = open("/home/user/v2pons/research/v4_slowrug_test.py").read()
cut = src.index('print(f"window')
sys.argv = ["x", "/home/user/v2pons/research/data/slowrug.json.gz", "/home/user/v2pons/research/data/slowrug_op.json.gz"]
g = {"__name__": "lib"}
exec(compile(src[:cut], "lib", "exec"), g)
opr, P, rows = g["opr"], g["P"], g["rows"]
print("operator launches", len(opr))
for name, sel in (("2-5%", lambda r: r["fee"] >= 10000), ("<1%", lambda r: r["fee"] < 10000)):
    rs = [r for r in opr if sel(r)]
    first_real = collections.Counter(); last_any = collections.Counter(); ex = []
    for r in rs:
        if r["pull"] is None: continue
        nonop = [b for b in r["nonop"] if b[0] <= r["pull"]]
        real = [b for b in nonop if b[2] >= 2e-4]
        if real:
            # earliest real-size non-operator buy that the pull follows within 30 blocks
            near = [b for b in real if r["pull"] - b[0] <= 30]
            if near:
                gfirst = r["pull"] - near[0][0]; first_real[gfirst] += 1
                if gfirst <= 4: ex.append((r["pid"][:12], r["day"], r["fee"], r["pull"], [(b[0], b[1], round(b[2], 5), b[3][:8]) for b in nonop if r["pull"] - b[0] <= 40]))
    print(name, "gap from earliest real-size (>=0.0002) non-op buy within 30 blocks of the pull ->", sorted(first_real.items()))
    for e in ex: print("   ", e)
# last-gap distribution as the research computed it, but recording which buy (size, role) the 3-block cases follow
print()
for name, sel in (("2-5%", lambda r: r["fee"] >= 10000), ("<1%", lambda r: r["fee"] < 10000)):
    rs = [r for r in opr if sel(r)]
    for r in rs:
        if r["pull"] is None: continue
        prior = [b for b in r["nonop"] if b[0] <= r["pull"]]
        if prior and r["pull"] - prior[-1][0] <= 4:
            print(name, "LASTGAP", r["pull"] - prior[-1][0], r["pid"][:12], r["day"], "fee", r["fee"], "pull", r["pull"], "crowd_first", r["crowd_first"], [(b[0], b[1], round(b[2], 5), b[3][:8]) for b in prior if r["pull"] - b[0] <= 60])
