import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); F = load_families()
FK = json.load(open("families_in.json"))
deps = {"0x26e8134ecc3af5cce32f34b03e7bd2f318b25158", "0x06cb3a6841c92525e7a1998328e7c9d37e98d937", "0xbbd6d3e018386b28de3730902217bb85b25372ce", "0x735b5c42ab813460c5616d42bf42464a5f116f55"}
tos = {"0x0000ffffbe8efe702c8703ae3477ff5de3d319c0", "0x3493ab3ec9358cb77b335507248c68fcaa84bf5e", "0xd912ed6ccd65370d2ef23c783bd2096e6ddbd68f"}
for d in sorted(deps):
    rows = [p for p in P.values() if p["launch_from"] == d]
    c = collections.Counter(p["family"] for p in rows)
    print("deployer", d, len(rows), "pools;", "fams:", c.most_common(8))
    if rows:
        print("   blocks", min(p["launch_block"] for p in rows), max(p["launch_block"] for p in rows), "pulled", sum(1 for p in rows if p["first_pull_rel"] is not None), "with buys>=0.0002 eth_in", round(sum(p["eth_in_buys"] or 0 for p in rows), 4))
for t in sorted(tos):
    rows = [p for p in P.values() if p["launch_to"] == t]
    print("to", t, len(rows), collections.Counter(p["family"] for p in rows).most_common(5))
# family 4: by code shape / selector across creates
rows = [p for p in P.values() if p["launch_to"] is None and p["selector"] == "60808060"]
c = collections.Counter((p["calldata_len"], p["fee"], p["tick_spacing"], p["launch_from"]) for p in rows)
print("creates 60808060:", len(rows)); 
for k, v in c.most_common(40): print("  ", k, v)
# creates with value >= 1 ETH and buy in launch tx
rows = [p for p in P.values() if p["launch_to"] is None and (p["launch_value_eth"] or 0) >= 1]
c = collections.Counter((p["calldata_len"], p["fee"], p["tick_spacing"], p["launch_from"][:10]) for p in rows)
print("creates with value>=1:", len(rows)); 
for k, v in c.most_common(30): print("  ", k, v)
# 0x0000ffff launcher code hash elsewhere
ch = P[F[FK[0]]["pids"][0]]["to_code_hash"]
rows = [p for p in P.values() if p["to_code_hash"] == ch]
print("code hash of 0x0000ffff:", len(rows), collections.Counter(p["launch_to"] for p in rows).most_common(5))
