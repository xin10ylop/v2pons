import sys, json, collections, datetime
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs(); ids = json.load(open("pids.json"))
DEP = "0xdc7a139c58701faac4b1c0b209989f1230ae5489"; HOOK2 = "0xdbebc6a7b2a38197932b6e01fb0e57e71d726aec"
print("pools launched by the F2 deployer (any family):", sum(1 for p in P.values() if p["launch_from"] == DEP))
print("pools with the F2 hook (any launcher):", collections.Counter((p["launch_from"], p["selector"], (p["to_code_hash"] or "")[:8]) for p in P.values() if p["hooks"] == HOOK2))
print("pools with to_code 8ce82419:", sum(1 for p in P.values() if (p["to_code_hash"] or "").startswith("8ce82419")))
print("pools with selector ec64ddcf:", collections.Counter((p["calldata_len"], p["fee"], p["tick_spacing"]) for p in P.values() if p["selector"] == "ec64ddcf"))
print("hooks ending 00cc/40cc/80cc/c0cc (flag 0xcc), ec64ddcf excluded:", collections.Counter(p["selector"] for p in P.values() if (int(p["hooks"][-4:], 16) & 0x3fff) == 0xcc and p["selector"] != "ec64ddcf").most_common(5))
for fam in ("F1", "F2"):
    ts = sorted(P[x]["launch_ts"] for x in ids[fam])
    hrs = collections.Counter(datetime.datetime.utcfromtimestamp(t).strftime("%m-%d %H") for t in ts)
    print(fam, datetime.datetime.utcfromtimestamp(ts[0]), "->", datetime.datetime.utcfromtimestamp(ts[-1]), "per hour:", sorted(hrs.items()))
# F1 launch wallets: who funded? (the launch tx's from, nonce 2) -> just the tx gas price etc.
f1 = [T[P[x]["launch_tx"]] for x in ids["F1"]]
print("F1 launch tx gas price p50", sorted(t["gas_price"] for t in f1)[len(f1)//2], "types", collections.Counter(t["type"] for t in f1), "max_prio", collections.Counter(t["max_prio"] for t in f1).most_common(3))
