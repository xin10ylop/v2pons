"""p02: the receipts of every launch by a launcher whose code keccak is 89885b75... (p01), and a chain-wide search for the 356-B line's
position fingerprint (any V3 Mint with tickLower -887272 and tickUpper 207243, any pool) over the same 48 hours, so that a move of the line to
another launcher would show. -> p02_receipts.jsonl, p02_fpmints.jsonl"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rpc
J = lambda n: os.path.join(HERE, n)
CODE89 = "89885b75fd29af130416accacb0351226a4259b3090dc0a2bb56189489efe08a"
T_MINT = "0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde"
meta = json.load(open(J("p01_meta.json")))
rows = [json.loads(x) for x in open(J("p01_pools.jsonl"))]
tx = {}
for x in open(J("p01_txs.jsonl")):
    t = json.loads(x); tx[t["hash"]] = t
code = json.load(open(J("p01_code.json")))
L89 = sorted(set(r["tx"] for r in rows if code.get((tx[r["tx"]]["to"] or "").lower(), {}).get("hash") == CODE89))
print("launch txs (code 89885b75...)", len(L89))
have = set()
if os.path.exists(J("p02_receipts.jsonl")):
    have = set(json.loads(x)["transactionHash"] for x in open(J("p02_receipts.jsonl")))
need = [h for h in L89 if h not in have]
for i in range(0, len(need), 20):
    res = rpc.batch("eth_getTransactionReceipt", [[h] for h in need[i:i + 20]], n=10)
    with open(J("p02_receipts.jsonl"), "a") as f:
        for r in res:
            if r: f.write(json.dumps({k: r.get(k) for k in ("transactionHash", "status", "blockNumber", "gasUsed", "effectiveGasPrice", "from", "to", "logs")}) + "\n")
print("receipts", len(have) + len(need))

if not os.path.exists(J("p02_fpmints.jsonl")):
    tl = "0x" + ((1 << 256) - 887272).to_bytes(32, "big").hex(); tu = "0x" + (207243).to_bytes(32, "big").hex()
    out = []
    for a in range(meta["from"], meta["head"] + 1, 100_000):
        b = min(meta["head"], a + 99_999)
        out += rpc.logs({"topics": [T_MINT, None, tl, tu]}, a, b)
        print("fp mints to", b, len(out), flush=True)
    with open(J("p02_fpmints.jsonl"), "w") as f:
        for l in out: f.write(json.dumps(l) + "\n")
print("rpc", rpc.STATS)
