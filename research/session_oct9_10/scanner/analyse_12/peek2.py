import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); P = load_pools(); T = load_txs()
KEYS = ["0x575b952fd3c079b3e72f4cd45f546edd2486d8fa|7fde822e|804|10000|200|true",
"0x5bd1fbe78a78fe8236fa00cf48fbeba74ae34661|a80ac0c2|1156|0|200|false",
"0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|3000|60|true",
"0xa0ce0291c181f800e7a5096b433685c37cfbf4df|617ac5de|676|8388608|200|false"]
pids = set(x for k in KEYS for x in F[k]["pids"])
E = load_events(pids)
for k in KEYS[1:]:
    print("=====", k)
    for pid in F[k]["pids"]:
        p = P[pid]; e = E.get(pid); b0 = p["launch_block"]
        lt = T[p["launch_tx"]]
        print(" POOL", pid[:12], "b0", b0, "from", p["launch_from"][:10], "val", p["launch_value_eth"], "sqrt", p["sqrt_p0"], "tick0", p["tick0"])
        if not e: print("   no events"); continue
        for a in e["adds"]: print("   ADD", a["bn"]-b0, a["ti"], a["lo"], a["hi"], a["dl"], a["sender"][:10], a["tx"][:10], "launchtx" if a["tx"]==p["launch_tx"] else "")
        for s in e["swaps"]:
            t = T.get(s["tx"])
            print("   SW", s["bn"]-b0, s["ti"], "%+.7f" % (-s["a0"]/1e18), "fee", s["fee"], "snd", s["sender"][:10], "to", t and t["to"] and t["to"][:10], "from", t and t["from"][:10], "nonce", t and t["nonce"], "sel", t and t["selector"], "clen", t and t["calldata_len"], "val", t and t["value_eth"])
        for s in e["pulls"]: print("   PULL", s["bn"]-b0, s["dl"], s["sender"][:10])
        for s in e["zero_mods"]: print("   ZERO", s["bn"]-b0, s["sender"][:10])
