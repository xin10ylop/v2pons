"""d01: every launch through the launcher 0xc9b7cc61 (selector 50b6f139) in the last ~3 days (600,000 blocks, 0.45 s each).
A launch = a WBNB Deposit whose dst is the launcher (one per launch, REPORT_BNB e03). Each launch tx and receipt is read: creator (tx.from),
selector, calldata length, PairCreated (pair, token, WBNB side), the Mint's WBNB (pool size), the token's code hash.
-> out d01_launches.json"""
import json, sys, os, collections, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import rpc
D = os.path.dirname(os.path.abspath(__file__))
WBNB = "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"; LC = "0xc9b7cc619200418649f9e3fc718e45028dfe9c47"
DEP = "0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c"
T_PC = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"; T_MINT = "0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f"
head = int(rpc.call("eth_blockNumber", []), 16); FROM = head - 600000
dep = rpc.logs({"address": WBNB, "topics": [DEP, "0x" + LC[2:].rjust(64, "0")]}, FROM, head, step=10000)
print("head", head, "from", FROM, "launch deposits", len(dep))
txh = sorted(set(l["transactionHash"] for l in dep))
txs = rpc.batch([("eth_getTransactionByHash", [h]) for h in txh]); rcs = rpc.batch([("eth_getTransactionReceipt", [h]) for h in txh])
rows = []
for h, t, r in zip(txh, txs, rcs):
    t = t.get("result"); r = r.get("result")
    if not t or not r: print("MISSING", h); continue
    o = {"tx": h, "L": int(r["blockNumber"], 16), "creator": t["from"].lower(), "to": (t["to"] or "").lower(), "sel": t["input"][2:10], "cd_len": len(t["input"]) // 2 - 1,
         "value_bnb": int(t["value"], 16) / 1e18, "status": r["status"]}
    for lg in r["logs"]:
        if lg["topics"][0] == T_PC and lg["address"].lower() == "0xca143ce32fe78f1f7019d7d551a6402fc5350c73":
            t0 = "0x" + lg["topics"][1][-40:]; t1 = "0x" + lg["topics"][2][-40:]
            o["pair"] = "0x" + lg["data"][26:66]; o["side"] = 0 if t0 == WBNB else 1; o["token"] = t1 if t0 == WBNB else t0
    for lg in r["logs"]:
        if lg["topics"][0] == T_MINT and lg["address"].lower() == o.get("pair"):
            a0 = int(lg["data"][2:66], 16); a1 = int(lg["data"][66:130], 16); o["size"] = (a0 if o["side"] == 0 else a1) / 1e18; o["tok_minted"] = a1 if o["side"] == 0 else a0
    rows.append(o)
toks = sorted(set(o["token"] for o in rows if o.get("token")))
codes = rpc.batch([("eth_getCode", [t, "latest"]) for t in toks])
ch = {}
for t, c in zip(toks, codes):
    c = c.get("result") or "0x"; b = bytes.fromhex(c[2:])
    import hashlib as _h
    try:
        from Crypto.Hash import keccak; k = keccak.new(digest_bits=256); k.update(b); kh = "0x" + k.hexdigest()
    except Exception: kh = None
    ch[t] = {"size": len(b), "sha256": hashlib.sha256(b).hexdigest()[:16], "keccak": kh}
for o in rows:
    if o.get("token"): o["code"] = ch[o["token"]]
rows.sort(key=lambda o: o["L"])
json.dump({"head": head, "from": FROM, "launches": rows}, open(os.path.join(D, "d01_launches.json"), "w"), indent=0)
C = collections.Counter
print("launch txs", len(rows), "to launcher", sum(o["to"] == LC for o in rows), "selector", C(o["sel"] for o in rows), "cd_len", C(o["cd_len"] for o in rows), "status", C(o["status"] for o in rows))
print("sizes", sorted(C(round(o.get("size", -1), 3) for o in rows).items()))
print("code sizes", C((o.get("code") or {}).get("size") for o in rows), "code sha", C((o.get("code") or {}).get("sha256") for o in rows).most_common(6))
print("creators", len(set(o["creator"] for o in rows)), C(o["creator"] for o in rows).most_common(3))
print("first L", rows[0]["L"], "last L", rows[-1]["L"])
