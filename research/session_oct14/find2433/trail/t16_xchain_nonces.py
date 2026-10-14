"""Do the 2.433 operator's Robinhood-Chain keys act on other chains? Nonce and balance now, on Ethereum, BSC, Base, Arbitrum, Unichain and
Optimism (publicnode), of the hub 0x6c3bd8f6, all 2.433 launch wallets known from Oct 11-12 (skeptic k01, 286) and the 31 buyer wallets
(k09), plus the decoy funders/fronters. Output t16_xchain_nonces.json and a summary."""
import sys, json, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/trail")
import xrpc
from common import jl, HUB
LW = sorted({r["from"] for r in jl("/home/user/v2pons/research/session_oct12/v2433/skeptic/k01_launches_cache.jsonl") if int(r.get("value", 0)) == 2433328500000000000})
BUY = sorted(json.load(open("/home/user/v2pons/research/session_oct12/v2433/skeptic/k09_buyers.json"))["callers2433"])
OTH = ["0x544ef4354283261fb9e258247a80d49c86b9f107", "0x488faf521a2d5f16ee55d1335841bb3ba9a0946e", "0xe322fc6ddb6b29d110b7f84c728d2d743e904616",
       "0x8cf143ddc84dedcd7bedd2b362b63af154dfa4f7", "0xb8c879dcd96d5ce0719e6fb056738f09b33bc33c", "0x0c628d6535b781f6c703ad319af8b1bcec63fbb4",
       "0x39525d91ffdcc126f052eefed6735fda72ad1dee", "0xa65254074287c7458666dbd26a8997c3ec590625"]
role = {a: "launch" for a in LW}; role.update({a: "buyer" for a in BUY}); role.update({a: "other" for a in OTH}); role[HUB] = "hub"
addrs = [HUB] + LW + BUY + OTH
chains = sys.argv[1].split(",") if len(sys.argv) > 1 else ["ethereum", "bsc", "base", "arbitrum", "unichain", "optimism"]
out = {}
for c in chains:
    try:
        n = xrpc.batch(c, "eth_getTransactionCount", [[a, "latest"] for a in addrs], n=20)
        b = xrpc.batch(c, "eth_getBalance", [[a, "latest"] for a in addrs], n=20)
    except Exception as e:
        print(c, "failed", e); continue
    out[c] = {a: (int(x, 16) if x else None, int(y, 16) / 1e18 if y else None) for a, x, y in zip(addrs, n, b)}
    act = {a: v for a, v in out[c].items() if v[0]}
    by = collections.Counter(role[a] for a in act)
    print("%-9s addresses with nonce > 0: %d %s; with balance > 0: %d" % (c, len(act), dict(by), sum(1 for v in out[c].values() if v[1])), flush=True)
    for a, v in sorted(act.items(), key=lambda kv: -kv[1][0])[:25]: print("    %s %-6s nonce %6d bal %.6f" % (a, role[a], v[0], v[1] or 0))
json.dump(out, open("/home/user/v2pons/research/session_oct14/find2433/trail/t16_xchain_nonces.json", "w"))
