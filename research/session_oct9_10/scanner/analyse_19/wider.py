import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common19 import *
P = load_pools()
def grp(name, f):
    ps = [p for p in P.values() if f(p)]
    print("=" * 90); print(name, len(ps))
    for a in ("launch_to", "launch_from", "selector", "calldata_len", "fee", "tick_spacing", "hooks", "launch_value_eth", "tick0", "liq_launch", "known", "family"):
        print("  %-16s %s" % (a, collections.Counter(p[a] for p in ps).most_common(6)))
    print("  n_buys>0", sum(1 for p in ps if p["n_buys"]), "pulled", sum(1 for p in ps if p["first_pull_rel"] is not None), "eth_in_buys sum", round(sum(p["eth_in_buys"] for p in ps), 6),
          "first_buy_eth>=0.0002", sum(1 for p in ps if (p["first_buy_eth"] or 0) >= 0.0002), "max eth_in", max((p["eth_in_buys"] for p in ps), default=0))
    print("  first8_swap_to", collections.Counter(t for p in ps for t in (p["first8_swap_to"] or [])).most_common(5))
    print("  pull to/sel/from", collections.Counter((p["first_pull_to"], p["first_pull_selector"], p["first_pull_from"]) for p in ps if p["first_pull_rel"] is not None).most_common(4))
grp("deployer 0x06cb3a68", lambda p: p["launch_from"] == "0x06cb3a6841c92525e7a1998328e7c9d37e98d937")
grp("to 0xdc416cab", lambda p: p["launch_to"] == "0xdc416cabaed48edab4905176f4eec6a4b22b1366")
grp("to 0xe43be69c", lambda p: p["launch_to"] == "0xe43be69cedf8c5190977e430a12befa2c6b2594e")
grp("to 0x0000ffff", lambda p: p["launch_to"] == "0x0000ffffbe8efe702c8703ae3477ff5de3d319c0")
grp("deployer 0x26e8134e", lambda p: p["launch_from"] == "0x26e8134ecc3af5cce32f34b03e7bd2f318b25158")
grp("deployer 0x5a617b5f", lambda p: p["launch_from"] == "0x5a617b5f4a405788c718360c27e00e5b3acdbac3")
grp("to 0x038ed9c7", lambda p: p["launch_to"] == "0x038ed9c750a8f7c5ff79a14421e3444929dfec1f")
grp("deployer 0xf3bce9e9", lambda p: p["launch_from"] == "0xf3bce9e9d92e2e8648689539475b0de7ba0af3b6")
grp("hook 0x0025115d", lambda p: p["hooks"].startswith("0x0025115d"))
grp("selector f03e0011", lambda p: p["selector"] == "f03e0011")
grp("tick0 198050 liq 50074188046840591947412", lambda p: p["tick0"] == 198050 and p["liq_launch"] == 50074188046840591947412)
