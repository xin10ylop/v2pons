"""trace_disp.py addr bn: find the wallet that funded addr (scan back up to 1000 blocks), then that funder's full in/out list in [bn-1500, bn+50]
   (dispatcher view: how much it got, from whom, how many fresh wallets it paid)"""
from B import *
a, bn = sys.argv[1].lower(), int(sys.argv[2])
rr = rows(bn - 1000, bn)
i = [q for q in rr if q[4] == a and int(q[5]) > 0]
print(f"=== trace_disp {a} @ {bn}", flush=True)
for q in i: print("  in:", fmt(q))
if not i: sys.exit()
src = i[-1][3]
rr = rows(bn - 1500, bn + 50)
ins = [q for q in rr if q[4] == src and int(q[5]) > 0]; outs = [q for q in rr if q[3] == src]
print(f"  funder {src}: ins {len(ins)} total {sum(int(q[5]) for q in ins)/1e18:.4f}; outs {len(outs)} total {sum(int(q[5]) for q in outs)/1e18:.4f}")
for q in ins[-8:]: print("    in :", fmt(q))
for q in outs[:4] + outs[-2:]: print("    out:", fmt(q))
if ins:
    big = max(ins, key=lambda q: int(q[5])); j = [q for q in rows(big[0] - 1000, big[0]) if q[4] == big[3] and int(q[5]) > 0]
    for q in j[-6:]: print("    in-of-biggest-in:", fmt(q))
