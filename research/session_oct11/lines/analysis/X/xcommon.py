"""Shared constants for study X (our sell timing, the operator's reaction Oct 10 vs Oct 11, is our address tracked)."""
import json, os, calendar
from eth_utils import keccak
HERE = os.path.dirname(os.path.abspath(__file__))
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
OURS = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"; RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
SENTINEL = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
DECOY_ROUTER = "0x65050a9b"          # prefix: the router the fresh decoy wallets call
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_TRANSFER = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
SP = {1604517591721945638372359205383840: "2.433", 679394651928963067279918579724198: "3.0"}
VAL = {2433328500000000000: "2.433", 3 * 10 ** 18: "3.0"}
USD = 2570.0
T_START = calendar.timegm((2026, 10, 10, 0, 0, 0))
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x, bits=256): return x - (1 << bits) if x >= (1 << (bits - 1)) else x
def pad(a): return "0x" + a.lower().replace("0x", "").zfill(64)
def word(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)
def utc(ts):
    import time; return time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))
def period(ts):
    """6-hour period label, e.g. 'Oct10 06-12'"""
    import time
    g = time.gmtime(ts); h = (g.tm_hour // 6) * 6
    return f"Oct{g.tm_mday} {h:02d}-{h+6:02d}"


class TxCache:
    def __init__(self, path):
        self.path = path; self.d = {}
        if os.path.exists(path):
            for l in open(path):
                try: x = json.loads(l); self.d[x["hash"]] = x
                except Exception: pass
        self.f = open(path, "a")

    def get(self, hashes, batch_fn, n=40, progress=None):
        need = [h for h in dict.fromkeys(hashes) if h not in self.d]
        for i in range(0, len(need), n * 25):
            ch = need[i:i + n * 25]
            res = batch_fn("eth_getTransactionByHash", [[h] for h in ch], n)
            for h, t in zip(ch, res):
                if t:
                    x = {k: t.get(k) for k in ("hash", "from", "to", "nonce", "value", "input", "blockNumber", "transactionIndex", "gasPrice", "maxPriorityFeePerGas", "gas")}
                    self.d[h] = x; self.f.write(json.dumps(x) + "\n")
            self.f.flush()
            if progress: progress(i + len(ch), len(need))
        return {h: self.d.get(h) for h in hashes}
