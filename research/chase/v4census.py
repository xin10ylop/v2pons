#!/usr/bin/env python3
"""v4census.py HOURS OUT.json [CHAIN...]: every Uniswap v4 pool initialized in the last HOURS on each EVM chain (read-only, public RPCs),
to find the 2.433 operator's line wherever it runs now. The Initialize event is read by its topic alone (any PoolManager). Per chain: the
pools, those with the operator's shape (fee 5000, tick spacing 100, no hook, native/token), and, for every no-hook native pool, the
creating transaction's sender, target and value; a family is 5+ pools launched with the same value (to 4 decimals) from 3+ senders: the
operator launches each pool with one fixed amount (10.5333 BNB on BNB Oct 15-19, 7.5333 BNB Sep 24-26, 2.433 ETH on Robinhood)."""
import json, sys, time, collections, urllib.request, concurrent.futures as cf

T_INIT = "0xdd466e674ea557f56295e2d0218a125ea4b4f0f6f3307b95f85e6110838d6438"   # Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)
# chain: (rpc, seconds a block, blocks a getLogs call)
CH = {"base": ("https://mainnet.base.org", 2.0, 2000), "bsc": ("https://bsc-rpc.publicnode.com", 0.45, 5000),
      "eth": ("https://ethereum-rpc.publicnode.com", 12.0, 5000), "arbitrum": ("https://arb1.arbitrum.io/rpc", 0.25, 50000),
      "optimism": ("https://mainnet.optimism.io", 2.0, 10000), "unichain": ("https://mainnet.unichain.org", 1.0, 10000),
      "polygon": ("https://polygon-bor-rpc.publicnode.com", 2.0, 5000), "avalanche": ("https://avalanche-c-chain-rpc.publicnode.com", 1.7, 5000),
      "ink": ("https://rpc-gel.inkonchain.com", 1.0, 10000), "soneium": ("https://rpc.soneium.org", 2.0, 10000),
      "worldchain": ("https://worldchain-mainnet.g.alchemy.com/public", 2.0, 10000), "zora": ("https://rpc.zora.energy", 2.0, 10000),
      "blast": ("https://rpc.blast.io", 2.0, 10000), "celo": ("https://forno.celo.org", 1.0, 10000), "linea": ("https://rpc.linea.build", 2.0, 10000),
      "monad": ("https://rpc.monad.xyz", 0.4, 100), "sonic": ("https://rpc.soniclabs.com", 0.5, 10000), "plasma": ("https://rpc.plasma.to", 1.0, 10000),
      "katana": ("https://rpc.katana.network", 1.0, 10000), "abstract": ("https://api.mainnet.abs.xyz", 1.0, 10000),
      "berachain": ("https://rpc.berachain.com", 2.0, 10000), "sei": ("https://evm-rpc.sei-apis.com", 0.4, 2000),
      "mode": ("https://mainnet.mode.network", 2.0, 10000), "scroll": ("https://rpc.scroll.io", 3.0, 10000), "mantle": ("https://rpc.mantle.xyz", 2.0, 10000),
      "hyperevm": ("https://rpc.hyperliquid.xyz/evm", 1.0, 1000), "opbnb": ("https://opbnb-mainnet-rpc.bnbchain.org", 0.5, 10000),
      "rh": ("https://rpc.mainnet.chain.robinhood.com", 0.25, 50000)}
# PoolManagers for the RPCs that refuse a log query without an address (and Unichain's, which returned nothing by topic alone)
PM = {"eth": "0x000000000004444c5dc75cb358380d2e3de08a90", "base": "0x498581ff718922c3f8e6a244956af099b2652b2b",
      "bsc": "0x28e2ea090877bf75740558f6bfb36a5ffee9e9df", "polygon": "0x67366782805870060151383f4bbff9dab53e5cd6",
      "avalanche": "0x06380c0e0912312b5150364b9dc4542ba0dbbc85", "unichain": "0x1f98400000000000000000000000000000000004"}
LOGS = {"base": "https://gateway.tenderly.co/public/base", "bsc": "https://rpc-bsc.48.club", "eth": "https://gateway.tenderly.co/public/mainnet"}   # log-friendlier endpoints


def rpc(url, m, p, tries=6):
    err = None
    for k in range(tries):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                                                        {"Content-Type": "application/json", "User-Agent": "research"}), timeout=60))
            if "result" in r:
                return r["result"]
            err = r.get("error")
        except Exception as e:
            err = e
        time.sleep(1.5 * (k + 1))
    raise RuntimeError(f"{m}: {str(err)[:100]}")


def logs(url, a, b, step, pm=None):
    out, lo = [], a
    while lo <= b:
        hi = min(b, lo + step - 1)
        q = {"fromBlock": hex(lo), "toBlock": hex(hi), "topics": [T_INIT]}
        if pm:
            q["address"] = pm
        try:
            out += rpc(url, "eth_getLogs", [q], tries=3)
            lo = hi + 1
        except Exception:
            if step <= 50:
                raise
            step //= 2
    return out


def one(ch, hours):
    url, bt, step = CH[ch]
    try:
        head = int(rpc(url, "eth_blockNumber", []), 16)
        t_head = int(rpc(url, "eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
        a = head - int(hours * 3600 / bt)
        t_a = int(rpc(url, "eth_getBlockByNumber", [hex(max(a, 1)), False])["timestamp"], 16)
        a = max(1, head - int((head - a) * hours * 3600 / max(1, t_head - t_a)))      # correct the block time once
        L = logs(LOGS.get(ch, url), a, head, step, PM.get(ch))
    except Exception as e:
        return ch, {"error": str(e)[:120]}
    pools = []
    for x in L:
        d = x["data"][2:]
        fee, ts, hooks = int(d[0:64], 16), int(d[64:128], 16), "0x" + d[128 + 24:192]
        ts = ts - (1 << 256) if ts >= 1 << 255 else ts
        pools.append({"pm": x["address"].lower(), "bn": int(x["blockNumber"], 16), "tx": x["transactionHash"], "c0": "0x" + x["topics"][2][26:],
                      "c1": "0x" + x["topics"][3][26:], "fee": fee, "ts": ts, "hooks": hooks, "sqrtP": int(d[192:256], 16)})
    native = [p for p in pools if p["c0"] == "0x" + "0" * 40 and (p["hooks"] == "0x" + "0" * 40 or (p["fee"], p["ts"]) == (5000, 100))]

    def tx(p):
        try:
            t = rpc(url, "eth_getTransactionByHash", [p["tx"]], tries=4)
            p.update(frm=t["from"].lower(), to=(t.get("to") or "").lower(), value=round(int(t["value"], 16) / 1e18, 4))
        except Exception:
            p.update(frm=None, to=None, value=None)
        return p
    with cf.ThreadPoolExecutor(4) as ex:
        native = list(ex.map(tx, native[:3000]))
    fam = collections.defaultdict(list)
    for p in native:
        if p.get("value"):
            fam[p["value"]].append(p)
    fams = sorted(((v, len(ps), len({p["frm"] for p in ps}), collections.Counter((p["fee"], p["ts"]) for p in ps).most_common(1)[0][0],
                    ps[0]["to"]) for v, ps in fam.items() if len(ps) >= 5 and len({p["frm"] for p in ps}) >= 3), key=lambda f: -f[1])
    shape = [p for p in native if p["fee"] == 5000 and p["ts"] == 100]
    x33 = [p for p in native if p.get("value") and p["value"] >= 0.1 and str(p["value"]).endswith("33")]   # the operator's amounts: 2.433, 4.133, 1.533, 10.5333, 7.5333 ...
    return ch, {"from_block": a, "head": head, "pools": len(pools), "native_nohook": len(native), "op_shape": len(shape),
                "op_shape_values": collections.Counter(p["value"] for p in shape).most_common(6), "families": fams[:8], "native": native,
                "x33": collections.Counter((p["value"], p["fee"], p["ts"], p["hooks"] != "0x" + "0" * 40) for p in x33).most_common(10),
                "all": [{k: p[k] for k in ("bn", "tx", "fee", "ts", "hooks", "c0", "c1")} for p in pools]}


def main(hours, out, chains):
    chains = chains or list(CH)
    res = {}
    with cf.ThreadPoolExecutor(8) as ex:
        for ch, r in ex.map(lambda c: one(c, hours), chains):
            res[ch] = r
            if "error" in r:
                print(f"{ch:10s} ERROR {r['error']}", flush=True); continue
            print(f"{ch:10s} v4 pools {r['pools']:5d} | native no-hook {r['native_nohook']:4d} | fee5000/ts100 {r['op_shape']:4d} {r['op_shape_values'][:4]}", flush=True)
            if r["x33"]:
                print(f"           values ending in 33 (value, fee, ts, hooked): {r['x33']}", flush=True)
            for v, n, ns, (fee, ts), to in r["families"]:
                print(f"           family {v} x{n} from {ns} senders, fee {fee} ts {ts}, via {to[:10]}", flush=True)
    json.dump({"hours": hours, "t": int(time.time()), "chains": res}, open(out, "w"))
    print("done ->", out, flush=True)


if __name__ == "__main__":
    main(float(sys.argv[1]), sys.argv[2], sys.argv[3:])
