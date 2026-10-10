"""h.py addr [lo hi]: value txs from/to addr in the cached index (vt.pkl); prints sender-side nonces."""
import sys, pickle, time
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/"
V = pickle.load(open(D + "origins/vt.pkl", "rb"))
a = sys.argv[1].lower(); lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0; hi = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
for t in V["tx"]:
    if lo <= t[0] <= hi and (t[3].startswith(a) or t[4].startswith(a)):
        print(t[0], time.strftime("%m-%d %H:%M:%S", time.gmtime(t[1])), t[3], "->", t[4], f"{t[5]/1e18:.5f}", "n", t[6], t[7], t[2][:14])
