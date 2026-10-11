"""Schedule angle, step 1 (public RPC, read-only, logs only; transactions are fetched sparingly in f02). Last N hours:
 - every ERC-20 Transfer from the PoolManager to the volume bot's router 0x1cbaf24d (any token): the token leg of every bot buy and pull,
   all lines, all pools (the router calls the Universal Router, so the Swap's sender is the UR and cannot be filtered on);
 - every ERC-20 Transfer from the bot's router to anyone: the forward to the buying wallet (gives the wallet without fetching the tx);
 - every ETH-pair Initialize; the bot-served pools are the pools of the tokens in the first set;
 - for each bot-served pool launched in the window: every Swap/ModifyLiquidity and every token Transfer to L+400.
-> logs/<kind>.jsonl, written as fetched"""
import sys, json, time, os
from eth_utils import keccak
from rpc import rpc, logs
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
SPAN = 400
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_TR = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
pad = lambda a: "0x" + "0" * 24 + a[2:]
os.makedirs("cache/logs", exist_ok=True)
head = int(rpc("eth_blockNumber", []), 16) - 30
hb = None
while hb is None:
    hb = rpc("eth_getBlockByNumber", [hex(head), False])
    if hb is None: head -= 20
th = int(hb["timestamp"], 16)
t1 = int(rpc("eth_getBlockByNumber", [hex(head - 50000), False])["timestamp"], 16)
bps = 50000 / max(1, th - t1)
start = head - int(hours * 3600 * bps)
json.dump({"head": head, "head_ts": th, "bps": bps, "start": start, "hours": hours}, open("cache/logs/meta.json", "w"))
print(f"head {head} {time.strftime('%m-%d %H:%M:%S', time.gmtime(th))} UTC, {bps:.3f} blocks/s, start {start}", flush=True)
def slim(x, kind):
    return {"k": kind, "addr": x["address"].lower(), "t": x["topics"], "data": x["data"], "bn": int(x["blockNumber"], 16), "li": int(x["logIndex"], 16),
            "ti": int(x["transactionIndex"], 16), "tx": x["transactionHash"]}
out = {k: open(f"cache/logs/{k}.jsonl", "w") for k in ("pm2bot", "bot2any", "init")}
STEP = 10000
n = {k: 0 for k in out}
for a in range(start - 3000, head + 1, STEP):
    b = min(a + STEP - 1, head)
    for k, flt in (("pm2bot", {"topics": [T_TR, pad(PM), pad(BOT)]}), ("bot2any", {"topics": [T_TR, pad(BOT)]}),
                   ("init", {"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]})):
        for x in logs(flt, a, b): out[k].write(json.dumps(slim(x, k)) + "\n"); n[k] += 1
        out[k].flush()
    print(f"  {a}-{b}: {n}", flush=True)
for f in out.values(): f.close()
toks = set(json.loads(l)["addr"] for l in open("cache/logs/pm2bot.jsonl"))
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
pools = []
for l in open("cache/logs/init.jsonl"):
    x = json.loads(l); tok = "0x" + x["t"][3][-40:]
    if tok in toks and x["bn"] >= start: pools.append({"pid": x["t"][1], "token": tok, "lb": x["bn"]})
pools.sort(key=lambda p: p["lb"])
print(f"{len(toks)} tokens bought by the bot; {len(pools)} of their pools launched in the window", flush=True)
f = open("cache/logs/pool.jsonl", "w")
i = 0
while i < len(pools):
    j = i
    while j + 1 < len(pools) and pools[j + 1]["lb"] - pools[i]["lb"] < 2500 and j + 1 - i < 25: j += 1
    grp = pools[i:j + 1]; ids = [p["pid"] for p in grp]; tks = [p["token"] for p in grp]
    a, b = grp[0]["lb"], min(head, grp[-1]["lb"] + SPAN)
    for topic, k in ((T_SWAP, "sw"), (T_ML, "ml")):
        for x in logs({"address": PM, "topics": [topic, ids]}, a, b): f.write(json.dumps(slim(x, k)) + "\n")
    for x in logs({"address": tks, "topics": [T_TR]}, a, b): f.write(json.dumps(slim(x, "tr")) + "\n")
    f.flush()
    print(f"  pools {i}-{j} blocks {a}-{b}", flush=True)
    i = j + 1
f.close()
print("done", flush=True)
