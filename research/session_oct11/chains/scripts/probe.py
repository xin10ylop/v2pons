"""Probe public RPC endpoints: liveness, chain head, block time (over ~N blocks), base fee, getLogs range limit."""
import json, sys, time, os
sys.path.insert(0, os.path.dirname(__file__))
import rpc
OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CHAINS = {
 "base": ["https://mainnet.base.org", "https://base-rpc.publicnode.com"],
 "unichain": ["https://mainnet.unichain.org", "https://unichain-rpc.publicnode.com"],
 "optimism": ["https://mainnet.optimism.io", "https://optimism-rpc.publicnode.com"],
 "ink": ["https://rpc-gel.inkonchain.com", "https://rpc-qnd.inkonchain.com"],
 "soneium": ["https://rpc.soneium.org"],
 "worldchain": ["https://worldchain-mainnet.g.alchemy.com/public"],
 "mode": ["https://mainnet.mode.network"],
 "apechain": ["https://rpc.apechain.com/http", "https://apechain.calderachain.xyz/http"],
 "xai": ["https://xai-chain.net/rpc"],
 "degen": ["https://rpc.degen.tips"],
 "sanko": ["https://mainnet.sanko.xyz"],
 "pop_apex": ["https://rpc.apex.proofofplay.com"],
 "rari": ["https://mainnet.rpc.rarichain.org/http", "https://rari.calderachain.xyz/http"],
 "reya": ["https://rpc.reya.network"],
 "superposition": ["https://rpc.superposition.so"],
 "bnb": ["https://bsc-dataseed.bnbchain.org", "https://bsc-rpc.publicnode.com"],
 "polygon": ["https://polygon-rpc.com", "https://polygon-bor-rpc.publicnode.com"],
 "avalanche": ["https://api.avax.network/ext/bc/C/rpc"],
 "sonic": ["https://rpc.soniclabs.com"],
 "berachain": ["https://rpc.berachain.com"],
 "monad": ["https://rpc.monad.xyz", "https://rpc1.monad.xyz"],
 "hyperevm": ["https://rpc.hyperliquid.xyz/evm"],
 "megaeth": ["https://mainnet.megaeth.com/rpc"],
}
SPAN = 200
res = {}
only = sys.argv[1:] or list(CHAINS)
for name in only:
    for url in CHAINS[name]:
        r = {"url": url}
        try:
            head = rpc.block_number(url)
            b1 = rpc.get_block(url, head)
            b0 = rpc.get_block(url, head - SPAN)
            dt = int(b1["timestamp"], 16) - int(b0["timestamp"], 16)
            r.update(head=head, chainTimeLag_s=round(time.time() - int(b1["timestamp"], 16), 1),
                     block_time_s=round(dt / SPAN, 4), baseFeeGwei=(int(b1.get("baseFeePerGas", "0x0"), 16) / 1e9),
                     txs_in_head=len(b1["transactions"]), gasLimit=int(b1["gasLimit"], 16))
            # getLogs range probe (no address, rare topic) at decreasing spans
            for span in (100000, 10000, 2000, 500, 100):
                try:
                    rpc.call(url, "eth_getLogs", [{"fromBlock": hex(head - span), "toBlock": hex(head),
                              "topics": ["0x" + "11" * 32]}])
                    r["getLogs_ok_span"] = span; break
                except rpc.RPCError as e:
                    r.setdefault("getLogs_errs", []).append(f"{span}: {str(e)[:140]}")
        except Exception as e:
            r["error"] = str(e)[:300]
        r["stats"] = rpc.STATS.get(url)
        res.setdefault(name, []).append(r)
        print(name, json.dumps(r)[:600], flush=True)
fn = os.path.join(OUT, "probe.json")
old = json.load(open(fn)) if os.path.exists(fn) else {}
old.update(res)
json.dump(old, open(fn, "w"), indent=1)
