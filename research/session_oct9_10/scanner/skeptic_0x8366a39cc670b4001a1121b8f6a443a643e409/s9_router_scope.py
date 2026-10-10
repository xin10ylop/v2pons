"""Where else do the crowd routers and the sniper trade (census-wide, first-8 swaps)? Router code and balances now."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from common_s import *
from chain import batch
from eth_utils import keccak
P = load_pools(); T = load_txs()
fam_by = collections.defaultdict(collections.Counter); sizes = collections.defaultdict(list)
for h, t in T.items():
    if t["to"] in CROWD_ROUTERS or t["from"] == SNIPER or t["to"] == "0x4f881c6afe5ced5e4469b15269fd0c1390f089c6":
        k = "crowd" if t["to"] in CROWD_ROUTERS else "sniper"
        for pid, kind, rank in t["refs"]:
            if kind == "swap": fam_by[k][P[pid]["family"]] += 1
for k, c in fam_by.items():
    print(k, "families", len(c), "pool-swaps", sum(c.values())); [print("   ", n, f) for f, n in c.most_common(8)]
addrs = sorted(CROWD_ROUTERS) + ["0x4f881c6afe5ced5e4469b15269fd0c1390f089c6"]
res = batch([("eth_getCode", [a, "latest"]) for a in addrs] + [("eth_getBalance", [a, "latest"]) for a in addrs])
for i, a in enumerate(addrs):
    code = res[i]; bal = int(res[len(addrs) + i], 16) / 1e18
    print(a, "code bytes", (len(code) - 2) // 2, "hash", "0x" + keccak(hexstr=code).hex()[:16] if len(code) > 2 else None, "balance ETH", round(bal, 4),
          "has 7169b574", "637169b574" in code, "is 1167 proxy", code.startswith("0x363d3d373d3d3d363d73"))
    open(os.path.join(HERE, f"code_{a[2:10]}.hex"), "w").write(code)
