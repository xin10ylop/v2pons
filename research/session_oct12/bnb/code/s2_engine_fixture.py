"""s2_engine_fixture: tests/data/bnb_launch.json, the fixture of tests/test_bnb_engine.py: one real launch of the PancakeSwap V2 launcher 0xc9b7cc61
(pair 0xea87b24f, block 127093739, 1 BNB) read from a public BNB RPC, read-only: its PairCreated and creating transaction, the pair's
Sync/Mint/Burn/Swap logs to +1100 (the dump at +1039), the transactions of its swaps, a WBNB pair launched through the router 65 blocks
earlier, and the USDT/WBNB pair's reserves at L+49 and L+259. An archive endpoint is needed (the block is older than publicnode keeps):
    python3 research/session_oct12/bnb/code/s2_engine_fixture.py https://bsc.rpc.sentio.xyz tests/data/bnb_launch.json"""
import json, sys, time, urllib.request
from eth_utils import keccak
RPC = sys.argv[1] if len(sys.argv) > 1 else "https://bsc.rpc.sentio.xyz"
OUT = sys.argv[2] if len(sys.argv) > 2 else "bnb_launch.json"
PAIR = "0xea87b24f8410b8d669c45133cdbf18ca361ac96f"; L = 127093739; UNTIL = 1100
FACTORY = "0xca143ce32fe78f1f7019d7d551a6402fc5350c73"; USDT_PAIR = "0x16b9a82891338f9ba80e2d6970fdda79d1eb0dae"
WBNB = "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
T = {n: "0x" + keccak(text=s).hex() for n, s in (("pc", "PairCreated(address,address,address,uint256)"), ("sync", "Sync(uint112,uint112)"),
     ("mint", "Mint(address,uint256,uint256)"), ("burn", "Burn(address,uint256,uint256,address)"), ("swap", "Swap(address,uint256,uint256,uint256,uint256,address)"))}


def rpc(m, p):
    for i in range(6):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                                                         {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}), timeout=60))
            if "result" in r: return r["result"]
            print("err", r.get("error")); time.sleep(1 + i)
        except Exception as e:
            print("exc", e); time.sleep(1 + i)
    raise SystemExit(m)


KEEP_LOG = ("address", "topics", "data", "blockNumber", "transactionHash", "transactionIndex", "logIndex", "blockHash")
KEEP_TX = ("hash", "from", "to", "input", "value", "gasPrice", "blockNumber", "transactionIndex", "nonce", "gas")
slim = lambda l: {k: l[k] for k in KEEP_LOG if k in l}
slimtx = lambda t: {k: t[k] for k in KEEP_TX if k in t}
fac = rpc("eth_getLogs", [{"address": FACTORY, "fromBlock": hex(L - 300), "toBlock": hex(L + 60), "topics": [T["pc"]]}])
print("PairCreated in [L-300, L+60]:", len(fac))
launch = [l for l in fac if l["data"][26:66] == PAIR[2:]]
assert len(launch) == 1, launch
others = []
for l in fac:
    if l is launch[0]: continue
    t0, t1 = "0x" + l["topics"][1][26:], "0x" + l["topics"][2][26:]
    if WBNB in (t0, t1):
        tx = rpc("eth_getTransactionByHash", [l["transactionHash"]])
        print("other WBNB pair", l["data"][26:66], int(l["blockNumber"], 16) - L, tx["to"], tx["input"][:10], int(tx["value"], 16) / 1e18)
        if tx["to"] == "0x10ed43c718714eb63d5aa57b78b54704e256024e" and not others:
            others.append((l, tx))
ltx = rpc("eth_getTransactionByHash", [launch[0]["transactionHash"]])
print("launch tx to", ltx["to"], ltx["input"][:10], len(ltx["input"]) // 2 - 1, int(ltx["value"], 16) / 1e18, "from", ltx["from"])
logs = rpc("eth_getLogs", [{"address": PAIR, "fromBlock": hex(L), "toBlock": hex(L + UNTIL), "topics": [[T["sync"], T["mint"], T["burn"], T["swap"]]]}])
print("pair logs", len(logs))
txs = {}
for l in logs:
    off = int(l["blockNumber"], 16) - L
    if l["topics"][0] == T["swap"]:
        d = l["data"][2:]; a = [int(d[i:i + 64], 16) for i in range(0, 256, 64)]
        print("  swap off", off, a, "sender", l["topics"][1][-40:], "to", l["topics"][2][-40:])
        txs[l["transactionHash"]] = slimtx(rpc("eth_getTransactionByHash", [l["transactionHash"]]))
o_l, o_tx = others[0] if others else (None, None)
usdt = {}
for b in (L + 49, L + 259):
    usdt[str(b)] = rpc("eth_call", [{"to": USDT_PAIR, "data": "0x0902f1ac"}, hex(b)])
usdt_t0 = rpc("eth_call", [{"to": USDT_PAIR, "data": "0x0dfe1681"}, "latest"])
head = rpc("eth_getBlockByNumber", [hex(L), False])
fx = {"source": "PancakeSwap V2 launch by 0xc9b7cc61 (selector 50b6f139), read from " + RPC.split("/")[2] + " on 2026-10-12",
      "pair": PAIR, "launch_block": L, "launch_ts": int(head["timestamp"], 16), "launch_log": slim(launch[0]), "launch_tx": slimtx(ltx),
      "pair_logs": [slim(l) for l in logs], "txs": txs, "other_log": slim(o_l) if o_l else None, "other_tx": slimtx(o_tx) if o_tx else None,
      "usdt_pair": USDT_PAIR, "usdt_token0": "0x" + usdt_t0[-40:], "usdt_reserves": usdt}
json.dump(fx, open(OUT, "w"), indent=1)
print("wrote", OUT, len(json.dumps(fx)))
