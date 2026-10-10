import sys, collections
src = open("/home/user/v2pons/research/v4_slowrug_test.py").read()
cut = src.index('print(f"window')
sys.argv = ["x", "/home/user/v2pons/research/data/slowrug.json.gz", "/home/user/v2pons/research/data/slowrug_op.json.gz"]
g = {"__name__": "lib"}
exec(compile(src[:cut], "lib", "exec"), g)
P, S, L, T, roles = g["P"], g["S"], g["L"], g["T"], g["roles"]
for pid in P:
    if pid.startswith("0x85a0c6af87") or pid.startswith("0x960a6614e0"):
        b0 = P[pid]["bn"]; print("==", pid[:12], "fee", P[pid]["fee"])
        for x, r, w, t in roles(pid):
            if x[0] - b0 <= 60: print("  +%d idx %s %s %.5f %s %s nonce %s" % (x[0]-b0, x[1], "BUY " if x[3] < 0 else "SELL", abs(x[3])/1e18, r, w[:8], t[2]))
        for x in L.get(pid, []):
            if x[0] - b0 <= 80: print("  +%d ML %.3e by %s" % (x[0]-b0, x[5], T[x[6]][0][:8]))
