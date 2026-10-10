import sys, json, collections, time; sys.path.insert(0, "..")
from chain import *
D = json.load(open("newsch.json")); P, ev, TX, head = D["P"], D["ev"], D["TX"], D["head"]
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
p = [p for p in P if P[p]["b0"] and any(TX[l["transactionHash"]][0].startswith("0x6d5a7e") for l in ev[p])][0]
b0 = P[p]["b0"]
for l in sorted(ev[p], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
    bn = int(l["blockNumber"], 16) - b0
    if bn < 840: continue
    t = TX[l["transactionHash"]]
    if l["topics"][0] == T_SWAP:
        a0 = s128(W(l["data"], 0)); print(f"+{bn} idx {t[3]} {'BUY ' if a0<0 else 'SELL'} {abs(a0)/1e18:.5f} from {t[0][:10]} nonce {t[2]} to {t[1][:10]} sel {t[4]}")
    else:
        print(f"+{bn} idx {t[3]} ML {sgn(W(l['data'],2)):.3e} from {t[0][:10]} nonce {t[2]} sel {t[4]}")
# inits after 17:12 (block of the last operator launch + 1): who launched what
last = max(P[q]["b0"] for q in P)
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, last + 1, head)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
c = collections.Counter()
for l, t in zip(inits, txs):
    d = l["data"]; hook = d[2+64*2+24:2+64*3] != "0"*40
    c[(t["input"][:10], t["to"][:8] if t["to"] else None, "hook" if hook else "nohook", W(d,0))] += 1
print("ETH-pair inits after the last operator launch:", sum(c.values()))
for k, v in c.most_common(15): print("  ", k, v)
