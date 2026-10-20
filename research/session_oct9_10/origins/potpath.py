"""Big (>0.5 ETH) plain transfers touching family-F pot wallets (non-crowd), time-ordered, with F of both ends; marks cache-range boundaries."""
import sys, pickle, time, collections
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/"
V = pickle.load(open(D + "origins/vt.pkl", "rb")); FM = pickle.load(open(D + "origins/fam.pkl", "rb"))
fam, role = FM["fam"], FM["role"]
F = sys.argv[1]; lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0; hi = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
R = V["ranges"]; ri = 0; last_r = None
for t in V["tx"]:
    if not (lo <= t[0] <= hi): continue
    if t[5] < 0.5e18: continue
    a, b = t[3], t[4]
    if (fam.get(a) == F and role.get(a)) or (fam.get(b) == F and role.get(b)):
        r = next(i for i, (x, y) in enumerate(R) if x <= t[0] <= y)
        if r != last_r: print(f"--- cache range {R[r][0]}-{R[r][1]}"); last_r = r
        print(t[0], time.strftime("%m-%d %H:%M:%S", time.gmtime(t[1])), a, fam.get(a, "-"), role.get(a, "crowd" if a in fam else ""), "->", b, fam.get(b, "-"), role.get(b, "crowd" if b in fam else ""), f"{t[5]/1e18:.4f}", "n", t[6], t[7])
