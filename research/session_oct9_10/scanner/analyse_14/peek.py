import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
KEYS = ["0x34c0d66f3a57a4cad3c5f792f5028d9c1da83d12|f03e0011|292|0|200|false",
"0x575b952fd3c079b3e72f4cd45f546edd2486d8fa|7fde822e|772|10000|200|true",
"0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|500000|5000|true",
"0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|810000|8100|true"]
P = load_pools(); F = load_families()
pids = set()
for k in KEYS: pids |= set(F[k]["pids"])
E = load_events(pids); T = load_txs()
for k in KEYS:
    f = F[k]
    print("=" * 100); print(k)
    print({x: f[x] for x in f if x not in ("pids",)})
    for pid in f["pids"]:
        p = P[pid]; e = E.get(pid)
        print("-- pool", pid[:12], "bn", p["launch_block"], "ts", p["launch_ts"], "from", p["launch_from"][:10], "nonce", p["launch_nonce"], "val", p["launch_value_eth"], "hooks", p["hooks"][:12], "fee", p["fee"], "tick0", p["tick0"], "liq", p["liq_launch"], "sqrt", p["sqrt_p0"])
        print("   nsw", p["n_swaps"], "nb", p["n_buys"], "ns", p["n_sells"], "npull", p["n_pulls"], "nadd", p["n_adds"], "fb", p["first_buy_rel"], p["first_buy_eth"], "fpull", p["first_pull_rel"], p["first_pull_to"], p["first_pull_selector"], p["first_pull_from"])
        if not e: continue
        for a in e["adds"][:4]: print("   add", a["bn"]-p["launch_block"], a["ti"], a["lo"], a["hi"], a["dl"], a["sender"][:10], a["tx"][:10])
        for s in e["swaps"][:12]:
            t = T.get(s["tx"])
            print("   sw +%d ti%d a0 %.6f a1 %d fee %d liq %d to %s from %s sel %s" % (s["bn"]-p["launch_block"], s["ti"], -s["a0"]/1e18, s["a1"], s["fee"], s["liq"], (t or {}).get("to","?")[:10] if t else "?", (t or {}).get("from","?")[:10] if t else "?", (t or {}).get("selector") if t else "?"))
        for pl in e["pulls"][:3]: print("   pull", pl["bn"]-p["launch_block"], pl["dl"], pl["sender"][:10], pl["tx"][:10])
