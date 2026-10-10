"""Every relay trade of ours Oct 8 00:00 -> head: buy block, sell block, the trigger (first real >= 0.0002 ETH non-us buy before
our buy), the trigger tx's fingerprint and nonce, and the first pull (negative liquidityDelta) after our buy.
Writes live_all.json; prints a table."""
import sys, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
HERE = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect/"
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"; US = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
URA = "0x" + UR
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
head = int(rpc("eth_blockNumber", []), 16)
START = 82878144
ours = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + RELAY]}, START, head)
def fp(t):
    inp = t["input"]; n = len(inp) // 2 - 1
    dl = None
    if inp[:10] == "0x3593564c" and len(inp) >= 10 + 64 * 3:
        dl = int(inp[10 + 128:10 + 192], 16) == (1 << 256) - 1
    return {"type": int(t["type"], 16), "prio": int(t.get("maxPriorityFeePerGas", "0x0"), 16), "gas": int(t["gas"], 16), "len": n, "to": t["to"], "dl_max": dl,
            "nonce": int(t["nonce"], 16), "from": t["from"]}
def crowd_fp(f):
    return f["type"] == 2 and f["prio"] == 20_000_000 and f["len"] == 1124 and f["dl_max"] is True and f["gas"] in (220_000, 880_000, 260_000)
out = []
pids = sorted({l["topics"][1] for l in ours}, key=lambda p: min(int(l["blockNumber"], 16) for l in ours if l["topics"][1] == p))
for pid in pids:
    mine = sorted([l for l in ours if l["topics"][1] == pid], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    B = int(mine[0]["blockNumber"], 16)
    il = logs({"address": PM, "topics": [T_INIT, pid]}, B - 3000, B)
    b0 = int(il[0]["blockNumber"], 16) if il else None
    lo = b0 if b0 else B - 400
    ls = sorted(logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, lo, min(head, B + 30000)), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    sw = [(int(l["blockNumber"], 16), int(l["logIndex"], 16), s128(W(l["data"], 0)), l["topics"][2][-40:] == RELAY, l["transactionHash"]) for l in ls if l["topics"][0] == T_SWAP]
    pulls = [(int(l["blockNumber"], 16), int(l["logIndex"], 16)) for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0]
    our_sw = [x for x in sw if x[3]]
    buy = next((x for x in our_sw if x[2] < 0), None); sell = next((x for x in our_sw if x[2] > 0), None)
    pre = [x for x in sw if not x[3] and x[2] <= -2 * 10**14 and (x[0], x[1]) < (buy[0], buy[1])]
    T = pre[0] if pre else None
    trig = None
    if T:
        t = rpc("eth_getTransactionByHash", [T[4]]); trig = fp(t); trig["crowd_fp"] = crowd_fp(trig); trig["value"] = int(t["value"], 16) / 1e18
    # every non-us buy from b0 to our sell: the window check (who bought between the trigger and our sell)
    win = [x for x in sw if not x[3] and x[2] < 0 and T and T[0] - 3 <= x[0] <= (sell[0] if sell else buy[0] + 4)]
    wtx = batch([("eth_getTransactionByHash", [x[4]]) for x in win]) if win else []
    wins = []
    for x, t in zip(win, wtx):
        f = fp(t); wins.append({"rel_T": x[0] - T[0], "eth": -x[2] / 1e18, "crowd_fp": crowd_fp(f), "from": f["from"][:10], "nonce": f["nonce"], "value": int(t["value"], 16) / 1e18})
    pull = pulls[0] if pulls else None
    ts = int(rpc("eth_getBlockByNumber", [hex(B), False])["timestamp"], 16)
    r = {"pid": pid[:10], "utc": time.strftime("%m-%d %H:%M:%S", time.gmtime(ts)), "launch": b0, "buy_off": B - b0 if b0 else None, "T_off": T[0] - b0 if (T and b0) else None,
         "buy_after_T": B - T[0] if T else None, "buy": [buy[0], buy[1]], "sell": [sell[0], sell[1]] if sell else None,
         "sell_after_buy": sell[0] - B if sell else None, "pull_after_buy": pull[0] - B if pull else None, "pull_after_sell": (pull[0] - sell[0]) if (pull and sell) else None,
         "pulled_before_sell": bool(pull and sell and pull < (sell[0], sell[1])),
         "eth_in": -buy[2] / 1e18, "eth_out": sell[2] / 1e18 if sell else 0.0, "trigger": trig, "window_buys": wins}
    out.append(r)
    print(f"{r['utc']} {r['pid']} T+{r['T_off']} buy T+{r['buy_after_T']} sell B+{r['sell_after_buy']} pull B+{r['pull_after_buy']} caught={r['pulled_before_sell']} "
          f"ret {(r['eth_out'] - r['eth_in']) / r['eth_in']:+.4f} trig {trig and (trig['from'][:10], trig['nonce'], round(trig['value'], 4), trig['crowd_fp'])}")
    for w in wins:
        print("      window", w)
json.dump({"head": head, "trades": out}, open(HERE + "live_all.json", "w"), indent=1)
