"""follow each Relay cash-out recipient on Base: find each outgoing tx by binary search on historical nonce, record to/value; up to 2 hops."""
import json, sys
from base import rpc
START = {  # recipient: (side, relay fill tx)
 "0xd2fc9f256161509e1fd08c9656adeb0a85af060c": ("A via 0x3ee51814 0.8", "0x6ceb71808b0b96fbc4c9d89c2dcccb8946db989184f7493fd7fb8363780fa41f"),
 "0x7e9e0e2bc1ed575ce87845bea46853a1bf69b7bd": ("A via 0x3ee51814 1.0", "0x57602e75bd118d4a935a6b945288ba239391b01f33cc55db3a64a168adb5ead2"),
 "0xf6a6f8fabc6d9f0633cdee3be6fde742c2f60a29": ("A via 0x3ee51814 0.25", "0x9431d56f1d260662d5645c8656be28bda741cd5144d724a6b86157ebb6a1b95a"),
 "0x72fadaccb431bdb02e72423a14c946ae3d1e7f13": ("D sweep 1.25", "0x464812c22a1494b3da03f9d52cacdc3acf7796b5e79240add7a5732f6d75181a"),
 "0xac8c5826c0084798653c6d8686e50bf09addc519": ("B via 0xe7a1c2fb 0.1", "0xa0024d20e81fbc1d786c9b858c61317154d89a86bbcc59cdf681928f97a78921"),
 "0x761be1b5b9ea2a0074e2a94778c957f8a3656a31": ("B via 0xe7a1c2fb 0.3", "0x315b4030c9153745575632542dffa176e9bbc88210076035b195982009e84acc"),
 "0x64880aafc44e6f12e1dc8015eb1d20358c33b547": ("B via 0xe7a1c2fb 0.4", "0x6db00c18dd981d3458ca4b1c969358032cfc44891bb03db9952d8ba1a5ca5d74"),
 "0xe845b142741480097cf4d66df8b730d4eb408515": ("B via 0xe7a1c2fb 0.5", "0xef70b07d5691c7e77f5515b690172835bdd6c1340f043b875ede186d064cbbcc"),
}
HEAD = int(rpc("eth_blockNumber", []), 16)
nonce = lambda a, b: int(rpc("eth_getTransactionCount", [a, hex(b)]), 16)
def out_txs(a, lo, maxn=6):
    """outgoing txs of a after block lo (nonce binary search per nonce)"""
    res = []; n_lo = nonce(a, lo); n_hi = nonce(a, HEAD)
    for k in range(n_lo, min(n_hi, n_lo + maxn)):
        L, R = lo, HEAD   # first block where nonce > k
        while L < R:
            m = (L + R) // 2
            if nonce(a, m) > k: R = m
            else: L = m + 1
        blk = rpc("eth_getBlockByNumber", [hex(L), True])
        for t in blk["transactions"]:
            if t["from"].lower() == a and int(t["nonce"], 16) == k:
                res.append({"block": L, "hash": t["hash"], "to": (t.get("to") or "").lower(), "eth": int(t["value"], 16) / 1e18, "nonce": k, "sel": t["input"][:10], "inlen": (len(t["input"]) - 2) // 2})
        lo = L
    return res, n_hi
out = {}
for a, (side, fill) in START.items():
    fb = int(rpc("eth_getTransactionByHash", [fill])["blockNumber"], 16)
    txs, n = out_txs(a, fb)
    bal = int(rpc("eth_getBalance", [a, "latest"]), 16) / 1e18
    print(f"{side}: {a} fill blk {fb} latest nonce {n} bal {bal:.6f}", flush=True)
    hop2 = []
    for t in txs:
        print(f"    n{t['nonce']} blk {t['block']} -> {t['to']} {t['eth']:.6f} ETH sel {t['sel']} len {t['inlen']} {t['hash']}", flush=True)
        code = rpc("eth_getCode", [t["to"], "latest"]) if t["to"] else "0x"
        n2 = nonce(t["to"], HEAD) if t["to"] else None
        print(f"        to-code {len(code)//2-1} bytes, to-nonce {n2}", flush=True)
        t["to_code"] = len(code) // 2 - 1; t["to_nonce"] = n2
    out[a] = {"side": side, "fill_block": fb, "nonce": n, "bal": bal, "txs": txs}
json.dump(out, open("/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2/verify3/basefollow.json", "w"), indent=1)
