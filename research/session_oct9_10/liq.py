import sys, time
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
from chain import *
Q96 = 1 << 96; RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
head = int(rpc("eth_blockNumber", []), 16)
ours = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0"*24 + RELAY]}, head - int(2 * 3600 / 0.103), head)
pids = []
for l in ours:
    if l["topics"][1] not in pids: pids.append(l["topics"][1])
print(f"{'launch':>8} {'fee':>6} {'L':>9} {'range (ticks)':>22} | {'virtual ETH':>11} {'real ETH in before us':>21} {'tokens in pool':>14} | impact of our buy: 0.0012 / 0.03 / 0.1 / 1 ETH")
for pid in pids:
    il = logs({"address": PM, "topics": [T_INIT, pid]}, head - int(3 * 3600 / 0.103), head)[0]; b0 = int(il["blockNumber"], 16); fee = W(il["data"], 0); sp0 = W(il["data"], 3)
    ls = sorted(logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, b0, b0 + 200), key=lambda x: (int(x["blockNumber"], 16), int(x["logIndex"], 16)))
    adds = [(sgn(W(x["data"], 0)), sgn(W(x["data"], 1)), sgn(W(x["data"], 2))) for x in ls if x["topics"][0] == T_ML and sgn(W(x["data"], 2)) > 0]
    my = next(i for i, x in enumerate(ls) if x["topics"][0] == T_SWAP and x["topics"][2][-40:] == RELAY)
    before = [x for x in ls[:my] if x["topics"][0] == T_SWAP]
    eth_in = sum(-s128(W(x["data"], 0)) for x in before)
    sp = W(before[-1]["data"], 2) if before else sp0; L = W(before[-1]["data"], 3) if before else adds[0][2]
    virt = L * Q96 / sp / 1e18
    tok_virtual = L * sp / Q96
    ts = int(rpc("eth_getBlockByNumber", [hex(b0), False])["timestamp"], 16)
    imp = []
    for x in (0.0012, 0.03, 0.1, 1.0):
        sp2 = v4math.sqrt_after_buy(float(sp), L, int(x * 1e18 * (1 - fee / 1e6)))
        imp.append(f"{100 * ((sp / sp2) ** 2 - 1):.2f}%")
    print(f"{time.strftime('%H:%M:%S', time.gmtime(ts)):>8} {fee/1e4:5.3f}% {L:9.2e} {str(adds[0][:2]):>22} | {virt:9.3f}   {eth_in/1e18:17.4f} ETH  {tok_virtual/1e18:12.3e} | " + " / ".join(imp))
