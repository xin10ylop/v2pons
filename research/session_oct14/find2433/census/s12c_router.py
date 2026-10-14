"""0x75379d5d (the 2,020 B family's buyer contract): code vs the Universal Router and the old bot router; a sample first-buy calldata (amountIn
0.05 ETH, amountOutMinimum 0); receipts of one operator buy and one sell. Output: s12c_router.out."""
from common import *
import s07_traits as S
fam = "K1 v4 0x58daec31 0xac9650d8 2020B f3000 ts60 v0 ETH hooked"
pids = [t["pid"] for t in jload("s05_targets.json") if t["fam"] == fam]
R75 = next(t["to"] for t in S.TX.values() if t["to"].startswith("0x75379d5d"))
for a, c in zip((R75, UR, BOT), rpc.batch("eth_getCode", [[a, "latest"] for a in (R75, UR, BOT)], n=5)):
    b = bytes.fromhex(c[2:]); print(a, len(b), "0x" + keccak(b).hex()[:16])
r = S.rows[pids[2]]; sw = S.swaps(S.EV[pids[2]], r)
fb = next(s for s in sw if s["buy"] and S.actor(s["h"]) == "0x75379d5d:0x3593564c"); t = S.TX[fb["h"]]
print("\nfirst buy", fb["h"], "from", t["f"], "nonce", t["n"], "tx value", int(t["v"]) / 1e18, "tokens out", fb["tok"], "eth in", fb["eth"])
inp = t["in"]
for i in range((len(inp) - 10) // 64): print(i, inp[10 + 64 * i: 10 + 64 * (i + 1)])
sl = next(s for s in sw if not s["buy"] and S.actor(s["h"]).startswith("0x75379d5d"))
for name, s, x in zip(("BUY", "SELL"), (fb, sl), rpc.batch("eth_getTransactionReceipt", [[fb["h"]], [sl["h"]]], n=2)):
    print("\n", name, s["h"], "status", x["status"], "logs", len(x["logs"]), "swap eth %.6f tok %.6g" % (s["eth"], s["tok"]))
    for lg in x["logs"]:
        t0 = lg["topics"][0]; nm = {T_TRANSFER: "Transfer", T_SWAP: "Swap"}.get(t0, t0[:10])
        ex = ("from %s to %s amt %.6g" % (lg["topics"][1][-40:][:10], lg["topics"][2][-40:][:10], int(lg["data"], 16))) if t0 == T_TRANSFER else ""
        print("   ", lg["address"][:12], nm, ex)
