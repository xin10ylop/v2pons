"""scan.py tag a b addr...: every tx touching addrs in [a,b] (cached full blocks)"""
from B import *
tag, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); ad = [x.lower() for x in sys.argv[4:]]
print(f"=== scan {tag} [{a},{b}] {len(ad)} addrs", flush=True)
for q in touching(ad, a, b): print("  ", fmt(q))
