"""Independent: every Swap sent by our relay from Oct 8 00:00 to the head (eth_getLogs topic2 = relay), paired into buy/sell per pool;
the first negative ModifyLiquidity on each pool; sell - buy and pull - buy in blocks."""
import sys, json, collections, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import rpc, logs, batch, PM, T_SWAP, T_ML, W, sgn
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
head = int(rpc("eth_blockNumber", []), 16); print("head", head)
A = 82878144
ls = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + RELAY[2:]]}, A, head)
print("relay swaps", len(ls))
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
by = collections.defaultdict(list)
for l in ls:
    d = l["data"]; a0 = s128(W(d, 0)); a1 = s128(W(d, 1))
    by[l["topics"][1]].append((int(l["blockNumber"], 16), int(l["logIndex"], 16), a0, a1, l["transactionHash"]))
rows = []
for pid, sw in by.items():
    sw.sort()
    buy = next((s for s in sw if s[2] < 0), None); sell = next((s for s in sw if s[2] >= 0 and buy and s[0] >= buy[0]), None)
    ml = logs({"address": PM, "topics": [T_ML, pid]}, buy[0] - 400, min(head, buy[0] + 30000))
    pulls = sorted((int(l["blockNumber"], 16), int(l["transactionIndex"], 16)) for l in ml if sgn(W(l["data"], 2)) < 0)
    blk = rpc("eth_getBlockByNumber", [hex(buy[0]), False])
    rows.append({"pid": pid[:10], "utc": time.strftime("%m-%d %H:%M:%S", time.gmtime(int(blk["timestamp"], 16))), "buy": buy[0], "eth_in": -buy[2] / 1e18,
                 "sell_after_buy": (sell[0] - buy[0]) if sell else None, "eth_out": (sell[2] / 1e18) if sell else None, "tokens_sold": (-sell[3]) if sell else None,
                 "pull_after_buy": (pulls[0][0] - buy[0]) if pulls else None})
rows.sort(key=lambda r: r["buy"])
for r in rows: print(r)
json.dump(rows, open("rv3.json", "w"), indent=0)
