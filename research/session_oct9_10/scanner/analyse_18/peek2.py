import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs()
K = json.load(open("keys.json"))
# launch calldata of one pool per family, decoded as words + ascii
F = load_families()
for k in K:
    pid = F[k]["pids"][0]; p = P[pid]; t = T[p["launch_tx"]]
    inp = t.get("input") or t["input512"]
    print("=" * 80); print(k, "tx", p["launch_tx"], "gas", t["gas"], "prio", t["max_prio"], "type", t["type"])
    d = bytes.fromhex(inp[10:])
    for i in range(0, len(d), 32):
        w = d[i:i+32]
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in w)
        print("  w%02d %s %s" % (i // 32, w.hex(), asc))
# the deployers of 0x815542e8: all their census pools
for dep in ("0x14a202fb4f4ff73d542a189030d3e112234a830b", "0xbabb7be0b5d6871331cbef588ae95695df8088ba", "0x61ae738f88d8badd55578adb9cdba78c60358013", "0x06cb3a6841c92525e7a1998328e7c9d37e98d937"):
    ps = [p for p in P.values() if p["launch_from"] == dep]
    print(dep, len(ps), collections.Counter((p["launch_to"], p["selector"], p["fee"]) for p in ps).most_common(8))
ps = [p for p in P.values() if p["launch_to"] == "0x815542e8b392389a1389e22e588e4b62a67ade72" or p["selector"] == "7c33638d"]
print("0x815542e8 / 7c33638d pools:", len(ps), collections.Counter((p["launch_to"], p["selector"], p["calldata_len"], p["fee"], p["family"]) for p in ps).most_common(10))
print(collections.Counter(p["launch_from"] for p in ps).most_common(10))
