"""b13: the Base engine's test fixture (tests/data/base_launch.json) from the 2.433 operator's 09:42 UTC test pool on Base (launch block
L = 52,590,807; b02/b08): everything tests/test_base_engine.py replays through the stubbed chain and both stubbed websockets.

Read from Tenderly's public Base gateway (it serves old blocks), in JSON-RPC batches, paced at about 4 requests a second:
- the pool's Initialize log (block L), every ModifyLiquidity and Swap log of the pool in L..L+31 (the add at +3, the bot's buys from +8,
  the pull at +30), the block headers L-1..L+32 (number, hash, timestamp, baseFeePerGas only);
- the launch transaction, the add (L+3, to the hook, selector 2346bb56), the bot's first three buys (L+8, +10, +12, to the bot contract
  0x987d5db8...) and the pull (L+30), each as eth_getTransactionByHash returns it (v, r, s, yParity, accessList: enough to re-encode the
  raw signed transaction, which the test checks by its hash), with its receipt;
- the token's runtime code (1,526 B), and the keccak of the launcher's and the hook's runtime code (their code is left out: 11 KB + 9 KB).
usage: python3 research/session_oct14/base2433/b13_fixture.py [out, default tests/data/base_launch.json]"""
import json, os, ssl, sys, time, urllib.request
from eth_utils import keccak

ROOT = "/home/user/v2pons"
CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt") if os.path.exists("/root/.ccr/ca-bundle.crt") else None
RPC = "https://base.gateway.tenderly.co"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
PM = "0x498581ff718922c3f8e6a244956af099b2652b2b"; BOT = "0x987d5db84d105c1f49391af409cc34c6050fb1d0"
L = 52590807; TOKEN = "0x3a73002fcad288a2ce1aff82fad49229b060a777"; HOOK = "0x1c888901220490eb5a1dc0a0e8ee106616c28080"
LAUNCHER = "0xd93bef10148cce1c7d462ea65d2482a8cca50bab"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
_last = [0.0]; REQS = [0]


def batch(calls):
    """[(method, params)] -> [result] in one HTTP request; each call counts as one request against the 4/s pace; 5 tries"""
    body = json.dumps([{"jsonrpc": "2.0", "id": i, "method": m, "params": p} for i, (m, p) in enumerate(calls)]).encode()
    for k in range(5):
        wait = _last[0] - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time() + len(calls) / 4.0; REQS[0] += len(calls)               # the next request waits for this one's share
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, body, H), timeout=60, context=CTX))
            r = sorted(r, key=lambda x: x["id"]) if isinstance(r, list) else [r]
            if len(r) == len(calls) and all("result" in x for x in r):
                return [x["result"] for x in r]
            err = [x.get("error") for x in r if "result" not in x][:1]
        except Exception as e:
            err = str(e)
        time.sleep(2 + 2 * k)
    raise RuntimeError(f"batch failed: {err}")


def chunked(calls, n=6):
    """a long list in batches of n (Tenderly counts each call of a batch against its rate limit)"""
    out = []
    for i in range(0, len(calls), n):
        out += batch(calls[i:i + n])
    return out


def one(m, p):
    return batch([(m, p)])[0]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "tests", "data", "base_launch.json")
    init = [l for l in one("eth_getLogs", [{"fromBlock": hex(L), "toBlock": hex(L), "address": PM, "topics": [T_INIT]}])
            if l["topics"][3][-40:] == TOKEN[2:]]
    assert len(init) == 1, f"{len(init)} Initialize logs with the token at {L}"
    init = init[0]; pid = init["topics"][1]
    pool_logs = one("eth_getLogs", [{"fromBlock": hex(L), "toBlock": hex(L + 31), "address": PM, "topics": [[T_ML, T_SWAP], pid]}])
    pool_logs.sort(key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    heads = chunked([("eth_getBlockByNumber", [hex(n), False]) for n in range(L - 1, L + 33)])
    headers = [{"number": h["number"], "hash": h["hash"], "parentHash": h["parentHash"], "timestamp": h["timestamp"], "baseFeePerGas": h["baseFeePerGas"]} for h in heads]
    adds = [l for l in pool_logs if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) > 0]
    pulls = [l for l in pool_logs if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0]
    buys = []
    for l in pool_logs:                                                            # the first buy in each of the first three blocks with one
        if l["topics"][0] == T_SWAP and sgn(W(l["data"], 0)) < 0:                     # amount0 < 0: the swapper paid ETH (a buy)
            if l["transactionHash"] not in buys and len(buys) < 3:
                buys.append(l["transactionHash"])
    want = {"launch": [init["transactionHash"]], "add": [adds[0]["transactionHash"]], "bot_buys": buys, "pull": [pulls[0]["transactionHash"]]}
    hashes = [h for v in want.values() for h in v]
    txs = chunked([("eth_getTransactionByHash", [h]) for h in hashes])
    recs = chunked([("eth_getTransactionReceipt", [h]) for h in hashes])
    tok_code, launcher_code, hook_code = batch([("eth_getCode", [a, hex(L + 3)]) for a in (TOKEN, LAUNCHER, HOOK)])
    kh = lambda c: "0x" + keccak(bytes.fromhex(c[2:])).hex()
    for t in txs:
        assert t["blockNumber"] and t["to"], t["hash"]
    fx = {
        "_about": ("The 2.433 operator's 09:42 UTC test pool on Base (launch block L, research/session_oct14/base2433 b02/b08), read from "
                   f"{RPC} on {time.strftime('%Y-%m-%d %H:%M', time.gmtime())} UTC by research/session_oct14/base2433/b13_fixture.py. Keys: launch_block (L), "
                   "pool (the v4 pool id), key (currency0, currency1, fee, tickSpacing, hooks), init_log (the PoolManager's Initialize, as eth_getLogs "
                   "returns it), pool_logs (every ModifyLiquidity and Swap of the pool in L..L+31, in block/logIndex order: the add at +3 is two "
                   "ModifyLiquidity events, the bot's buys from +8, the pull at +30), headers (L-1..L+32: number, hash, parentHash, timestamp, "
                   "baseFeePerGas, hex as the node gives them), txs (hash -> eth_getTransactionByHash: the launch, the add, the bot's first three buys, "
                   "the pull), receipts (hash -> eth_getTransactionReceipt, l1Fee included), roles (launch, add, bot_buys, pull -> their hashes), "
                   "token_code (the token's runtime code at L+3), code_hashes (keccak of the runtime code of the token, the launcher and the hook; the "
                   "launcher's and the hook's code are left out for size)"),
        "source": RPC, "launch_block": L, "pool": pid,
        "key": {"currency0": "0x" + init["topics"][2][-40:], "currency1": "0x" + init["topics"][3][-40:], "fee": W(init["data"], 0),
                "tickSpacing": sgn(W(init["data"], 1)), "hooks": "0x" + init["data"][2 + 64 * 2 + 24: 2 + 64 * 3]},
        "init_log": init, "pool_logs": pool_logs, "headers": headers,
        "txs": {t["hash"]: t for t in txs}, "receipts": {r["transactionHash"]: r for r in recs}, "roles": want,
        "token_code": tok_code,
        "code_hashes": {"token": kh(tok_code), "launcher": kh(launcher_code), "hook": kh(hook_code)},
        "code_sizes": {"token": (len(tok_code) - 2) // 2, "launcher": (len(launcher_code) - 2) // 2, "hook": (len(hook_code) - 2) // 2},
    }
    with open(out, "w") as f:
        json.dump(fx, f, indent=0, separators=(",", ":"))
    print(f"pool {pid} key {fx['key']}")
    print(f"pool logs {len(pool_logs)}: " + ", ".join(f"+{int(l['blockNumber'], 16) - L}:{'ML' if l['topics'][0] == T_ML else 'S'}" for l in pool_logs))
    print(f"roles {json.dumps({k: [h[:10] for h in v] for k, v in want.items()})}")
    print(f"code hashes {fx['code_hashes']} sizes {fx['code_sizes']}")
    print(f"wrote {out}: {os.path.getsize(out)} B; requests {REQS[0]}")


if __name__ == "__main__":
    main()
