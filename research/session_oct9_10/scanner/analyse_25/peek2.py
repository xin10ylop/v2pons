import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools()
def show(name, f):
    ps = [p for p in P.values() if f(p)]
    print("==", name, len(ps))
    print("  to:sel:len", collections.Counter("%s:%s:%s" % ((p["launch_to"] or "create")[:10], p["selector"], p["calldata_len"]) for p in ps).most_common(8))
    print("  from", collections.Counter(p["launch_from"][:10] for p in ps).most_common(6))
    print("  fee/ts", collections.Counter((p["fee"], p["tick_spacing"], p["hooks_zero"]) for p in ps).most_common(5))
    print("  values", collections.Counter(p["launch_value_eth"] for p in ps).most_common(5))
    print("  tick0", collections.Counter(p["tick0"] for p in ps).most_common(5))
    print("  n_buys>0", sum(1 for p in ps if p["n_buys"]), "pulled", sum(1 for p in ps if p["n_pulls"]), "eth_in", round(sum(p["eth_in_buys"] or 0 for p in ps), 6))
    print("  first_ts..last_ts", min(p["launch_ts"] for p in ps) if ps else None, max(p["launch_ts"] for p in ps) if ps else None)
    print("  known", collections.Counter(p["known"] for p in ps))
show("to 0xce4c6a28", lambda p: p["launch_to"] == "0xce4c6a284f1160cebaa56ac0d190f66983b09ae6")
show("to 0xd1e3060e", lambda p: p["launch_to"] == "0xd1e3060e2c00ccecddedcb802f45146531192bef")
show("from 0x06cb3a68", lambda p: p["launch_from"] == "0x06cb3a6841c92525e7a1998328e7c9d37e98d937")
show("sel 7fde822e", lambda p: p["selector"] == "7fde822e")
show("to 0xe181b36e", lambda p: p["launch_to"] == "0xe181b36e96e9cab0130707bcb513fc1401e0ba32")
show("from 0x843784a6", lambda p: p["launch_from"] == "0x843784a6d2c839ca170e64c75dcc797dfc4a86a3")
show("sel a25a9a3d", lambda p: p["selector"] == "a25a9a3d")
show("code hash of 0xe181b36e", lambda p: p["to_code_hash"] == "543148c97f031c555ace47108021289f0cbed34a4b6af050362fcc9c5bfc115f")
show("value 0.000100683", lambda p: p["launch_value_wei"] == 100683000000000)
