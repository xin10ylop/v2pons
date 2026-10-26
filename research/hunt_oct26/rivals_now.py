#!/usr/bin/env python3
"""rivals_now.py: are the other front-runners of the 2.433 line still active, and where?

The wallets are the ones REPORT_X (research/session_oct11/lines/REPORT_X.md) found fronting the 2.433 and 3.0 lines on Robinhood on Oct 10-11
next to us: the "D65" group (twin 752-byte routers 0x65050a9b / 0xfd1b271f, their admins, the collectors their fresh wallets swept into, the
recurring buyers) and the other early buyers of the 3.0 line. For each address on Robinhood, Base, Ethereum, BNB and Arbitrum: the nonce, the
balance and whether it has code now. Read-only, public RPCs."""
import json, sys, time, urllib.request, concurrent.futures as cf

EP = {"rh": "https://rpc.mainnet.chain.robinhood.com", "base": "https://base-rpc.publicnode.com", "eth": "https://ethereum-rpc.publicnode.com",
      "bsc": "https://bsc-rpc.publicnode.com", "arb": "https://arbitrum-one-rpc.publicnode.com"}
W = {"router_65050a9b": "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc", "router_fd1b271f": "0xfd1b271f235e5230eaee9d914ccb1af495bfb758",
     "admin_0c628d65": "0x0c628d6535b781f6c703ad319af8b1bcec63fbb4", "admin_04a802fe": "0x04a802fe42476e9e9ed3cc3c28ce3a476a73d229",
     "coll_544ef435": "0x544ef4354283261fb9e258247a80d49c86b9f107", "coll_e322fc6d": "0xe322fc6ddb6b29d110b7f84c728d2d743e904616",
     "coll_488faf52": "0x488faf521a2d5f16ee55d1335841bb3ba9a0946e", "coll_c522af57": "0xc522af57dfc0006ff6f77d8d46f1fc7996431151",
     "buy_b4c345dc": "0xb4c345dcf30be7ef93abbacb5f67bd3cc3dfaa04", "buy_b8c879dc": "0xb8c879dcd96d5ce0719e6fb056738f09b33bc33c",
     "buy_8cf143dd": "0x8cf143ddc84dedcd7bedd2b362b63af154dfa4f7", "buy_7ae81404": "0x7ae81404e32aef363eb63bc4befba78fb5b636de",
     "buy_b002e8a0": "0xb002e8a04b2822d8f2890b022ddea3d25f9c3df8", "buy_f05d0e3f": "0xf05d0e3f4b7777223e132254a1dc12127d503384",
     "buy3_8c009ea5": "0x8c009ea554d530dde6ef42d4e105ceb1006749a6", "router3_7ebacc35": "0x7ebacc352509c454139003d5aef9f86151deb0ac",
     "buy3_9f3b9a44": "0x9f3b9a449dfaa2fdfb4dd5e1d8c47b9f12d051ea", "buy3_9a128676": "0x9a12867607c191a7191c08e3d8dea7018e277416"}


def rpc(url, m, p, tries=4):
    for i in range(tries):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                                                        {"Content-Type": "application/json", "User-Agent": "curl/8"}), timeout=20))
            if "result" in r:
                return r["result"]
        except Exception:
            pass
        time.sleep(0.5 * (i + 1))
    return None


def one(ch, name, a):
    n, b, c = rpc(EP[ch], "eth_getTransactionCount", [a, "latest"]), rpc(EP[ch], "eth_getBalance", [a, "latest"]), rpc(EP[ch], "eth_getCode", [a, "latest"])
    return ch, name, (int(n, 16) if n else None), (int(b, 16) / 1e18 if b else None), (len(c) // 2 - 1 if c else None)


if __name__ == "__main__":
    with cf.ThreadPoolExecutor(12) as ex:
        res = list(ex.map(lambda t: one(*t), [(ch, k, v) for k, v in W.items() for ch in EP]))
    by = {}
    for ch, name, n, b, c in res:
        by.setdefault(name, {})[ch] = (n, b, c)
    print(f"{'wallet':18}" + "".join(f"{ch:>26}" for ch in EP))
    for name in W:
        cells = []
        for ch in EP:
            n, b, c = by[name][ch]
            cells.append(f"{'?' if n is None else n:>8}n {0 if b is None else b:9.4f}{'' if not c else f' code{c}':>9}")
        print(f"{name:18}" + "".join(f"{x:>26}" for x in cells))
