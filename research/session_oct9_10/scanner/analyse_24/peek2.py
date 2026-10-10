import sys, os, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs()
L1 = "0x815542e8b392389a1389e22e588e4b62a67ade72"
D1 = {"0xbabb7be0b5d6871331cbef588ae95695df8088ba", "0xaca4c6614c08ffa6b6a7e71db9b4c09ec31f33ba", "0xd5755214f14a1dc4cdf00fd5a571ea1c1be9904c", "0x14a202fb4f4ff73d542a189030d3e112234a830b"}
CH = "670175c93d0c34f23f837c43dd67f8e637464cbc960c83482d2c36952c3c5b5b"
g = [p for p in P.values() if p["launch_to"] == L1 or p["launch_from"] in D1 or p["to_code_hash"] == CH or p["selector"] == "7c33638d"]
print(len(g))
c = collections.Counter((p["launch_to"], p["selector"], p["calldata_len"], p["fee"], p["tick_spacing"], p["hooks_zero"], p["tick0"], p["launch_from"][:10]) for p in g)
for k, v in c.most_common(): print(v, k)
for p in g:
    print(p["pid"][:12], p["launch_block"], p["launch_from"][:10], p["launch_nonce"], p["launch_to"] and p["launch_to"][:10], p["selector"], p["calldata_len"], p["fee"], p["tick0"], "nb", p["n_buys"], "eth_in", round(p["eth_in_buys"],5), "fb", p["first_buy_rel"], p["first_buy_eth"], "pull", p["first_pull_rel"], p["first8_swap_to"][:3] if p["first8_swap_to"] else None)
# inspect the launch calldata of one
t = T[g[0]["launch_tx"]]
inp = t.get("input") or t["input512"]
print(t["from"], t["to"], t["selector"], t["calldata_len"])
body = inp[10:]
for i in range(0, len(body), 64): print(i // 64, body[i:i+64])
