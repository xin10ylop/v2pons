import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); TF = load_to_families(); LF = load_loose_families()
# 2020-byte POSM group
g = [p for p in P.values() if p["launch_to"] == "0x58daec3116aae6d93017baaea7749052e8a04fa7" and p["calldata_len"] == 2020]
print("POSM 2020:", len(g), "fees", collections.Counter((p["fee"], p["tick_spacing"]) for p in g).most_common(30))
print("  with buys", sum(1 for p in g if p["n_buys"]), "pulled", sum(1 for p in g if p["n_pulls"]), "deployers", len(set(p["launch_from"] for p in g)))
print("  buy pools:", [(p["fee"], p["n_buys"], p["first_buy_rel"], p["first_buy_eth"], p["first8_swap_to"][:3]) for p in g if p["n_buys"]][:20])
print("  hooks", collections.Counter(p["hooks"] for p in g).most_common(4))
# hook of family 1
h = "0xbba868de24cb83dc5851fae9ec27cb905c5fa0cc"
gh = [p for p in P.values() if p["hooks"] == h]
print("hook bba868de pools:", len(gh), collections.Counter(p["family"] for p in gh).most_common(5))
g1 = [p for p in P.values() if p["launch_to"] == "0x34c0d66f3a57a4cad3c5f792f5028d9c1da83d12"]
print("launcher 34c0d66f pools:", len(g1), collections.Counter(p["family"] for p in g1).most_common(5))
g2 = [p for p in P.values() if p["selector"] == "7fde822e"]
print("7fde822e pools:", len(g2), "with real buy", sum(1 for p in g2 if any((s or 0) for s in [p["first_buy_eth"]]) and (p["first_buy_eth"] or 0) >= 0.0002), "pulled", sum(1 for p in g2 if p["n_pulls"]),
      "launchers", collections.Counter(p["launch_to"] for p in g2).most_common(30)[:5], "from", collections.Counter(p["launch_from"] for p in g2).most_common(6))
g2b = [p for p in P.values() if p["launch_to"] == "0x575b952fd3c079b3e72f4cd45f546edd2486d8fa"]
print("launcher 575b952f pools:", len(g2b), collections.Counter(p["family"] for p in g2b).most_common(5))
