#!/usr/bin/env python3
"""v2scan.py RPC FACTORY WETH FROM_BLOCK OUT [HORIZON=900 SWAPWIN=300]: every WETH pair created on a Uniswap-V2 factory since FROM_BLOCK,
its creator, its first Mint (ETH side), Burns (pulls) inside HORIZON blocks, swaps inside SWAPWIN blocks with the wallet behind each
(the first 25 swaps' transactions looked up: [from, to, nonce, value, selector, type, priority fee wei]).
As a module (deploy/base_v2_roster.py): Scan(rpc, factory, weth).run(from_block, out) returns what the file holds; its steps, pairs(),
fill_txs() and fill_events(), can be run apart (the roster looks the creations up first and reads the events of the line's pairs only)."""
import json, sys, time, urllib.request, urllib.error, concurrent.futures as cf
from eth_utils import keccak
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
T_PC = "0x"+keccak(text="PairCreated(address,address,address,uint256)").hex(); T_MINT = "0x"+keccak(text="Mint(address,uint256,uint256)").hex()
T_BURN = "0x"+keccak(text="Burn(address,uint256,uint256,address)").hex(); T_SW = "0x"+keccak(text="Swap(address,uint256,uint256,uint256,uint256,address)").hex()
W = lambda d, i: int(d[2+64*i:2+64*(i+1)], 16)


class Scan:
    def __init__(self, rpc, factory, weth, horizon=900, swapwin=300, threads=4, swap_cap=25, log=print):
        self.url = rpc; self.factory = factory.lower(); self.weth = weth.lower(); self.horizon = horizon; self.swapwin = swapwin
        self.threads = threads; self.swap_cap = swap_cap; self.log = log; self.w32 = "0x" + "0"*24 + self.weth[2:]

    def rpc(self, m, p):
        for i in range(8):
            try:
                r = json.load(urllib.request.urlopen(urllib.request.Request(self.url, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), H), timeout=90))
                if "result" in r: return r["result"]
                time.sleep(2)
            except urllib.error.HTTPError as e: time.sleep(6 if e.code == 429 else 2)
            except Exception: time.sleep(2)
        return None

    def head(self): return int(self.rpc("eth_blockNumber", []), 16)

    def pairs(self, b0, head):
        """{pair: {bn, tx, token, weth_is0}}: every WETH pair created on the factory in b0..head"""
        pairs = {}
        for pos in (1, 2):
            for a in range(b0, head+1, 5000):
                ls = self.rpc("eth_getLogs", [{"address": self.factory, "topics": [T_PC, self.w32, None] if pos == 1 else [T_PC, None, self.w32], "fromBlock": hex(a), "toBlock": hex(min(a+4999, head))}]) or []
                for l in ls:
                    pair = "0x" + l["data"][2:66][-40:]; pairs[pair] = {"bn": int(l["blockNumber"], 16), "tx": l["transactionHash"], "token": l["topics"][2 if pos == 1 else 1][-40:], "weth_is0": pos == 1}
        return pairs

    def events(self, pair, p):
        """(pair, mints, burns, swaps) inside the horizon; a swap is (block, logIndex, a0in, a1in, a0out, a1out, tx)"""
        ls = self.rpc("eth_getLogs", [{"address": pair, "topics": [[T_MINT, T_BURN, T_SW]], "fromBlock": hex(p["bn"]), "toBlock": hex(p["bn"]+self.horizon)}]) or []
        mints, burns, swaps = [], [], []
        for l in ls:
            bn = int(l["blockNumber"], 16); d = l["data"]; t0 = l["topics"][0]
            if t0 == T_MINT: mints.append((bn, W(d, 0), W(d, 1), l["transactionHash"]))
            elif t0 == T_BURN: burns.append((bn, W(d, 0), W(d, 1), l["transactionHash"]))
            elif bn <= p["bn"] + self.swapwin: swaps.append((bn, int(l["logIndex"], 16), W(d, 0), W(d, 1), W(d, 2), W(d, 3), l["transactionHash"]))
        return pair, mints, burns, swaps

    def tx(self, h):
        t = self.rpc("eth_getTransactionByHash", [h])
        return h, ([t["from"][2:].lower(), (t.get("to") or "")[2:].lower(), int(t["nonce"], 16), int(t["value"], 16), t["input"][:10],
                    int(t.get("type") or "0x0", 16), int(t.get("maxPriorityFeePerGas") or t.get("gasPrice") or "0x0", 16)] if t else None)

    def fill_events(self, pairs):
        """mints, burns, swaps and eth_in (the first Mint's ETH side) on every pair record"""
        with cf.ThreadPoolExecutor(self.threads) as ex:
            for n, (pair, mints, burns, swaps) in enumerate(ex.map(lambda kv: self.events(*kv), list(pairs.items()))):
                p = pairs[pair]; p["mints"], p["burns"], p["swaps"] = mints, burns, swaps
                if mints: p["eth_in"] = (mints[0][1] if p["weth_is0"] else mints[0][2]) / 1e18
                if n % 100 == 0: self.log(f"  events {n}/{len(pairs)}")
        return pairs

    def fill_txs(self, hashes, txs=None):
        """{hash: [from, to, nonce, value, selector, type, priority fee]} for the hashes (those already in txs are not asked again)"""
        txs = {} if txs is None else txs; todo = [h for h in dict.fromkeys(hashes) if h not in txs]
        with cf.ThreadPoolExecutor(self.threads) as ex:
            for n, (h, t) in enumerate(ex.map(self.tx, todo)):
                if t: txs[h] = t
                if n % 500 == 0: self.log(f"  txs {n}/{len(todo)}")
        return txs

    def run(self, b0, out=None):
        head = self.head(); self.log(f"blocks {b0}-{head}")
        pairs = self.pairs(b0, head); self.log(f"WETH pairs created: {len(pairs)}")
        self.fill_events(pairs)
        hashes = [p["tx"] for p in pairs.values()] + [s[6] for p in pairs.values() for s in p["swaps"][:self.swap_cap]]
        self.log(f"tx lookups: {len(dict.fromkeys(hashes))}")
        txs = self.fill_txs(hashes)
        for p in pairs.values():
            t = txs.get(p["tx"]); p["from"], p["to"], p["nonce"], p["sel"] = (t[0], t[1], t[2], t[4]) if t else (None, None, None, None)
        d = {"factory": self.factory, "weth": self.weth, "blocks": [b0, head], "pairs": pairs, "txs": txs}
        if out:
            json.dump(d, open(out, "w")); self.log("done -> " + out)
        return d


def main(argv):
    if len(argv) < 5: sys.exit(__doc__.split("\n")[0])
    horizon = int(argv[5]) if len(argv) > 5 else 900; swapwin = int(argv[6]) if len(argv) > 6 else 300
    Scan(argv[0], argv[1], argv[2], horizon, swapwin, log=lambda s: print(s, flush=True)).run(int(argv[3]), argv[4])


if __name__ == "__main__":
    main(sys.argv[1:])
