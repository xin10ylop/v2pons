"""d05: for every (token, buyer) that is not the crowd's, and for a sample of crowd (token, buyer) pairs: the first buy (offset from the
launch block, method, gas price, the contract that called the pair, recipient == tx.from, the recipient's code), every later movement of
the token out of the buyer (a sell into the pair, any other transfer), and today's state: balanceOf and an eth_call of transfer(0x...dEaD,
1% of the balance) from the buyer at the latest block (ok / revert). The crowd = recipients whose every buy is the router's 7ff36ab5 with
tx.from == recipient, in >= 20 pools.  -> d05_status.json, d05_status.out"""
import json, os, sys, random, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from common import *; import rpc
d = json.load(open(os.path.join(CACHE, "d04_buyers_cache.json"))); B = d["buys"]; OUTS = d["outs"]; INS = d["ins"]
LS = launches(); byp = {o["pair"]: o for o in LS}
pools_by = C.defaultdict(set); shape = C.defaultdict(set)
for b in B:
    pools_by[b["buyer"]].add(b["pool"]); shape[b["buyer"]].add((b["tx_to"] == ROUTER, b["sel"], b["tx_from"] == b["buyer"]))
CROWD = sorted(a for a in pools_by if shape[a] == {(True, "7ff36ab5", True)} and len(pools_by[a]) >= 20)
print("crowd wallets", len(CROWD))
first = {}
for b in sorted(B, key=lambda b: (b["blk"], b["txi"])):
    k = (b["token"], b["buyer"])
    if k not in first: first[k] = dict(b, nbuys=0, bnb_total=0.0, last_buy_blk=b["blk"])
    first[k]["nbuys"] += 1; first[k]["bnb_total"] += b["bnb_in"]; first[k]["last_buy_blk"] = b["blk"]
crowd_set = set(CROWD)
non = [k for k in first if k[1] not in crowd_set]
random.seed(14); crowd_keys = [k for k in first if k[1] in crowd_set]
# the crowd sample: every crowd holder in our pool, plus 300 random crowd (token, buyer) pairs
ours_pool = "0x2de2620b04a0382390b18441cd033da7b798e57e"
cs = [k for k in crowd_keys if first[k]["pool"] == ours_pool] + random.sample(crowd_keys, 300)
keys = non + [k for k in dict.fromkeys(cs)]
addrs = sorted(set(k[1] for k in keys))
codes = rpc.batch([("eth_getCode", [a, "latest"]) for a in addrs]); code = {a: (c.get("result") or "0x") for a, c in zip(addrs, codes)}
bals = rpc.batch([("eth_call", [{"to": k[0], "data": "0x70a08231" + k[1][2:].rjust(64, "0")}, "latest"]) for k in keys])
bal = {k: int(r["result"], 16) if (r.get("result") not in (None, "0x") and "error" not in r) else None for k, r in zip(keys, bals)}
tests = [k for k in keys if bal[k]]
DEADA = "000000000000000000000000000000000000dead".rjust(64, "0")
res = rpc.batch([("eth_call", [{"from": k[1], "to": k[0], "gas": hex(300000), "data": "0xa9059cbb" + DEADA + hex(max(1, bal[k] // 100))[2:].rjust(64, "0")}, "latest"]) for k in tests])
tst = {k: ("ok" if (r.get("result") is not None and "error" not in r) else "revert:" + str((r.get("error") or {}).get("message", r.get("error")))[:60]) for k, r in zip(tests, res)}
rows = []
for k in keys:
    f = first[k]; outs = [o for o in OUTS.get(f"{k[0]}|{k[1]}", []) if o["blk"] >= f["blk"]]
    ins_other = [i for i in INS.get(f"{k[0]}|{k[1]}", []) if i["from"] != f["pool"]]
    c = code[k[1]]
    rt = "eoa" if c in ("0x", "") else ("eoa7702" if c.startswith("0xef0100") else "contract")
    o = byp[f["pool"]]
    rows.append({"token": k[0], "buyer": k[1], "crowd": k[1] in crowd_set, "pool": f["pool"], "L": f["L"], "size": f["size"], "code": f["code"], "off": f["off"],
                 "txi": f["txi"], "nbuys": f["nbuys"], "bnb": round(f["bnb_total"], 6), "sel": f["sel"], "tx_to": f["tx_to"], "tx_from": f["tx_from"], "gp": f["gp"],
                 "self": f["tx_from"] == k[1], "swap_sender": f["swap_sender"], "rtype": rt, "code_len": (len(c) - 2) // 2, "tx": f["tx"],
                 "first_buyer_rank": None, "outs": len(outs), "sells": sum(1 for x in outs if x["kind"] == "sell"), "xfers": sum(1 for x in outs if x["kind"] == "transfer"),
                 "first_out_off": (outs[0]["blk"] - f["L"]) if outs else None, "first_out_kind": outs[0]["kind"] if outs else None,
                 "first_out_sel": outs[0]["sel"] if outs else None, "ins_other": len(ins_other), "bal_now": bal[k], "test_now": tst.get(k, "no balance" if bal[k] == 0 else "unread")})
# rank of each buy in its pool (1 = the pool's first buyer)
rank = {}
for p in set(b["pool"] for b in B):
    seen = []
    for b in sorted((b for b in B if b["pool"] == p), key=lambda b: (b["blk"], b["txi"])):
        if b["buyer"] not in seen: seen.append(b["buyer"])
    for i, a in enumerate(seen): rank[(p, a)] = i + 1
for r in rows: r["first_buyer_rank"] = rank[(r["pool"], r["buyer"])]
json.dump({"crowd": CROWD, "rows": rows}, open(os.path.join(D, "d05_status.json"), "w"), indent=0)
print("rows", len(rows), "non-crowd", sum(not r["crowd"] for r in rows), "crowd sample", sum(r["crowd"] for r in rows))
print("tests now", C.Counter(r["test_now"][:12] for r in rows))
