"""family 0x1eef016f (hook 0x4e346895): capacity ahead of the first scheduled buy with the minOut decoded from router 0x65050a9b's calldata
(4d819a2a: word 2 = ETH in, word 3 = minOut, word 4 = deadline). The router passes 99% of the value to the pool; the hook keeps 1.3% of
the tokens, so minOut is compared with the receipt (0.987 x pool output) here (and with the pool output, for the record)."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common20 import *
P = load_pools(); T = load_txs(); M = load_blocks_meta(); F = load_families()
TX = json.load(open(os.path.join(HERE, "hookfee_txs.json")))
K = json.load(open(os.path.join(HERE, "keys.json")))
pids = F[K[1]]["pids"]; E = load_events(set(pids)); out = []
for pid in pids:
    pl = Pool(P[pid], E.get(pid), T, M)
    b = [x for x in pl.seq if x["buy"] and x["sender"] != "0x6f02324d20cc679d0e585290caa6b16bacbc0f77"]
    if not b: continue
    x = b[0]; t = TX[x["tx"]]; inp = t["input"]; w = lambda i: int(inp[10 + 64 * i: 74 + 64 * i], 16)
    mo, dl = w(3), w(4)
    sp, L = pl.launch_state(); fee = x["fee"]; quote = v4math.buy_out_int(int(sp), L, x["eth"], fee)
    r = {"pid": pid, "rel": x["bn"] - pl.b0, "eth": x["eth"] / 1e18, "from": t["from"], "minout": mo, "deadline_minus_launch_ts": dl - P[pid]["launch_ts"],
         "quote": quote, "minout_over_receipt_quote": mo / (quote * 987 // 1000),
         "cap_eth_on_receipt": room(sp, L, x["eth"], fee, mo * 1000 // 987 + 1), "cap_eth_on_pool_output": room(sp, L, x["eth"], fee, mo)}
    print(r); out.append(r)
json.dump(out, open(os.path.join(HERE, "fam2_cap.json"), "w"), indent=1, default=str)
