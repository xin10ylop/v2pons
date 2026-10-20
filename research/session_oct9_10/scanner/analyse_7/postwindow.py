# every Swap / ModifyLiquidity of my 48 pools from their launch to the chain head (the census stops at launch + 3,000)
import sys, json, os, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from chain import rpc, logs, PM, T_SWAP, T_ML, W, sgn
from load import *
F = load_families(); P = load_pools()
keys = json.load(open("families_in.json"))
pids = [pid for k in keys for pid in F[k]["pids"]]
out = "postwindow_logs.json"
if os.path.exists(out):
    L = json.load(open(out))
else:
    head = int(rpc("eth_blockNumber", []), 16)
    a = min(P[p]["launch_block"] for p in pids)
    L = {"head": head, "from": a, "logs": []}
    b = a
    while b <= head:
        e = min(b + 99_999, head)
        L["logs"] += logs({"address": PM, "topics": [[T_SWAP, T_ML], pids]}, b, e)
        b = e + 1; time.sleep(0.3)
    json.dump(L, open(out, "w"))
print("head", L["head"], "from", L["from"], "logs", len(L["logs"]))
import collections
c = collections.Counter(); per = collections.defaultdict(list)
for l in L["logs"]:
    pid = l["topics"][1]; bn = int(l["blockNumber"], 16); rel = bn - P[pid]["launch_block"]
    if l["topics"][0] == T_SWAP:
        a0 = sgn(W(l["data"], 0)); a0 = a0 - (1 << 128) if a0 >= (1 << 127) else a0   # int128 inside int256 word: already sign-extended
        per[pid].append(("swap", rel, a0 / 1e18, l["transactionHash"][:10]))
    else:
        dl = sgn(W(l["data"], 2)); per[pid].append(("ml", rel, dl, l["transactionHash"][:10]))
summ = {"head": L["head"], "pools": len(pids), "with_post_window_swap": 0, "with_pull_ever": 0, "post_window_buys_eth": 0.0, "events": {}}
for pid in pids:
    ev = per.get(pid, [])
    post = [x for x in ev if x[0] == "swap" and x[1] > 3000]
    pulls = [x for x in ev if x[0] == "ml" and x[2] < 0]
    summ["with_post_window_swap"] += bool(post); summ["with_pull_ever"] += bool(pulls)
    summ["post_window_buys_eth"] += sum(-x[2] for x in post if x[2] < 0)
    summ["events"][pid] = ev
    print(pid[:10], P[pid]["family"][:10], len(ev), ev[:6])
summ["post_window_buys_eth"] = round(summ["post_window_buys_eth"], 8)
json.dump(summ, open("postwindow.json", "w"), indent=1)
print({k: v for k, v in summ.items() if k != "events"})
