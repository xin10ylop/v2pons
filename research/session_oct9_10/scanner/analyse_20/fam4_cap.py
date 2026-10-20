"""family 0x2cf3de56: capacity ahead of its one buy with the minOut decoded from the 0x05ac4ff6 router calldata (word 7), on the pool
output (a1) and on the trader's receipt (0.995 x a1: the hook burns 0.5% of the tokens to 0xdead)."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common20 import *
P = load_pools(); T = load_txs(); M = load_blocks_meta(); F = load_families()
K = json.load(open(os.path.join(HERE, "keys.json")))
pid = [x for x in F[K[3]]["pids"] if x.startswith("0xf22aee7d")][0]
E = load_events({pid}); pl = Pool(P[pid], E[pid], T, M)
s = [x for x in pl.seq if x["buy"]][0]
inp = s["input"]; mo = word(inp, 7); amt = word(inp, 6)
sp, L = pl.launch_state(); fee = s["fee"]
quote = v4math.buy_out_int(int(sp), L, s["eth"], fee)
res = {"pid": pid, "start": pl.start, "amount_word6": amt, "eth_into_pool": s["eth"], "minout_word7": mo, "quote": quote, "a1": s["a1"],
       "minout_over_quote": mo / quote, "minout_over_trader_receipt": mo / (quote * 995 // 1000),
       "cap_eth_on_pool_output": room(sp, L, s["eth"], fee, mo), "cap_eth_if_checked_on_receipt": room(sp, L, s["eth"], fee, mo * 1000 // 995)}
print(res)
json.dump(res, open(os.path.join(HERE, "fam4_cap.json"), "w"), indent=1)
