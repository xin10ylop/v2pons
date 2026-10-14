"""Do the operator's reusable wallets (the 31 2.433 bot-buyer wallets, the BNB line's 34 bot wallets, hub 0x6c3bd8f6, next wallet 0x8b499c5a,
admins 0x5b2b20e1/0x0152c954) have any transactions on other EVM chains? eth_getTransactionCount('latest') on public endpoints."""
import sys, json, urllib.request, time; sys.path.insert(0, '.'); import rpcx
EPS = {"optimism": "https://optimism-rpc.publicnode.com", "polygon": "https://polygon-bor-rpc.publicnode.com", "avalanche": "https://avalanche-c-chain-rpc.publicnode.com",
       "linea": "https://linea-rpc.publicnode.com", "scroll": "https://scroll-rpc.publicnode.com", "blast": "https://blast-rpc.publicnode.com", "mantle": "https://mantle-rpc.publicnode.com",
       "sonic": "https://sonic-rpc.publicnode.com", "opbnb": "https://opbnb-rpc.publicnode.com", "gnosis": "https://gnosis-rpc.publicnode.com", "berachain": "https://berachain-rpc.publicnode.com",
       "soneium": "https://soneium-rpc.publicnode.com", "taiko": "https://taiko-rpc.publicnode.com", "celo": "https://celo-rpc.publicnode.com", "hyperevm": "https://rpc.hyperliquid.xyz/evm",
       "monad": "https://rpc.monad.xyz", "worldchain": "https://worldchain-mainnet.g.alchemy.com/public", "abstract": "https://api.mainnet.abs.xyz", "plasma": "https://rpc.plasma.to",
       "sei": "https://evm-rpc.sei-apis.com", "zksync": "https://mainnet.era.zksync.io", "ink": "https://rpc-gel.inkonchain.com", "unichain": "https://unichain-rpc.publicnode.com",
       "cronos": "https://evm.cronos.org", "kaia": "https://public-en.node.kaia.io", "mode": "https://mainnet.mode.network", "zora": "https://rpc.zora.energy", "apechain": "https://rpc.apechain.com",
       "megaeth": "https://mainnet.megaeth.com/rpc", "katana": "https://rpc.katana.network", "hemi": "https://rpc.hemi.network/rpc", "flare": "https://flare-api.flare.network/ext/C/rpc",
       "core": "https://rpc.coredao.org", "moonbeam": "https://moonbeam-rpc.publicnode.com", "metis": "https://metis-rpc.publicnode.com", "fraxtal": "https://fraxtal-rpc.publicnode.com",
       "polygon_zkevm": "https://zkevm-rpc.com", "manta": "https://pacific-rpc.manta.network/http", "bob": "https://rpc.gobob.xyz", "lisk": "https://rpc.api.lisk.com", "morph": "https://rpc.morphl2.io",
       "story": "https://mainnet.storyrpc.io", "rootstock": "https://public-node.rsk.co", "xlayer": "https://rpc.xlayer.tech", "base": "https://base-rpc.publicnode.com",
       "arbitrum_nova": "https://arbitrum-nova-rpc.publicnode.com", "robinhood": "https://rpc.mainnet.chain.robinhood.com", "ethereum": "https://ethereum-rpc.publicnode.com",
       "bsc": "https://bsc-rpc.publicnode.com", "arbitrum": "https://arbitrum-one-rpc.publicnode.com"}
x = json.load(open("c16_rh_wallets_xchain.json")); B31 = [a for a, _, _ in x["buyers_bsc"]]
TX = {}
for l in open("c18_swaptx_cache.jsonl"):
    r = json.loads(l); TX[r["h"]] = r
E = [json.loads(l) for l in open("c18_events_cache.jsonl")]
B34 = sorted(set(TX[e["tx"]]["from"] for e in E if e["k"] == "swap" and e["tx"] in TX and TX[e["tx"]]["to"] == "0x07cb61618b69234d954022ff738a015548715533" and TX[e["tx"]]["sel"] == "0xc1120e3d"))
KEY = ["0x6c3bd8f6fbca130f95305e9fa5a37d1dbf31622d", "0x8b499c5a56d5d0bed60527463bb1de389d6327e1", "0x5b2b20e15e96b015908a323ddbaee4aa25b04f4d", "0x0152c954397718abfe4716eb3aaf86903cff3796"]
A = sorted(set(B31 + B34 + KEY))
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
out = {}
for ch, url in EPS.items():
    try:
        res = []
        for i in range(0, len(A), 20):
            body = [{"jsonrpc": "2.0", "id": j, "method": "eth_getTransactionCount", "params": [a, "latest"]} for j, a in enumerate(A[i:i + 20])]
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), H), timeout=30, context=rpcx.CTX))
            if isinstance(d, dict): raise RuntimeError(str(d)[:120])
            d = sorted(d, key=lambda z: z["id"]); res += [int(z["result"], 16) if z.get("result") else -1 for z in d]
            time.sleep(0.3)
        nz = {a: n for a, n in zip(A, res) if n > 0}
        out[ch] = nz
        print(f"{ch:14s} wallets with nonce>0: {len(nz):3d} of {len(A)}", ("max %d" % max(nz.values())) if nz else "", "| key:", {k[:10]: nz.get(k, 0) for k in KEY if nz.get(k)}, flush=True)
    except Exception as e:
        out[ch] = "ERR " + str(e)[:100]; print(f"{ch:14s} ERR {str(e)[:100]}", flush=True)
json.dump(out, open("c21_xchain_probe.json", "w"), indent=1)
