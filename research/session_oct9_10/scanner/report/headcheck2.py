# Breakdown of the post-census "other" ETH-pair launches by (fee, tick spacing, hooks zero, sqrtP) to spot a re-fingerprinted volume bot.
import sys, json, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, logs, PM, T_INIT, W, sgn
a = 85203898; head = json.load(open("headcheck.json"))["head"]
ZERO = "0x" + "0"*64
L = logs({"address": PM, "topics": [T_INIT, None, ZERO]}, a, head)
c = collections.Counter(); ex = {}
for l in L:
    d = l["data"]; fee = W(d, 0); ts = sgn(W(d, 1)); hz = d[2+64*2+24:2+64*3] == "0"*40; sp = W(d, 3)
    k = (fee, ts, hz, sp if True else None); c[k] += 1; ex.setdefault(k, (int(l["blockNumber"], 16), l["transactionHash"]))
rows = [{"fee": k[0], "ts": k[1], "hooks_zero": k[2], "sqrtP": str(k[3]), "n": n, "first_bn": ex[k][0], "tx": ex[k][1]} for k, n in c.most_common(25)]
json.dump(rows, open("headcheck_other.json", "w"), indent=1)
for r in rows: print(r)
