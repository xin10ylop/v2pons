"""the recurring early wallets on chain now: nonce, ETH balance, and (for the + 1 bot) the line tokens it still holds; the contracts they
use: code size. Wallets from r08_fronters.json (and the + 1 bot)."""
from common import *
import rpc
F = json.load(open(J("r08_fronters.json")))
ws = sorted(F, key=lambda w: -len(F[w]))[:15]
for w in ws:
    n = int(rpc.call("eth_getTransactionCount", [w, "latest"]), 16); b = int(rpc.call("eth_getBalance", [w, "latest"]), 16) / 1e18
    to = F[w][0]["to"]; code = rpc.call("eth_getCode", [to, "latest"]) if to else "0x"
    print(f"{w} pools {len(F[w]):>4} nonce {n:>7} balance {b:.4f} ETH  via {to} code {(len(code) - 2) // 2} B")
BOT = next((w for w in F if w.startswith("0x776e5a2a")), None)
if BOT:
    P = {x["pool"]: x for x in json.load(open(J("r01_launches.json")))}
    sample = [x for x in F[BOT] if x["pull"] is not None][-8:]
    for x in sample:
        tok = P[x["pool"]]["token"]
        bal = int(rpc.call("eth_call", [{"to": tok, "data": "0x70a08231" + BOT[2:].zfill(64)}, "latest"]), 16)
        print(f"  +1 bot in {x['pool'][:10]} (pulled +{x['pull']}): bought {x['ein']:.5f} ETH, sold {x['frac']:.0%}; token balance now {bal / 1e18:,.0f}")
print(rpc.STATS)
