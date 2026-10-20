"""d10: the stranger table. Buyer = the address that ends a buy tx holding the tokens (net receiver in the tx, so an aggregator that passes
the tokens on is replaced by the final recipient). Crowd = buyers whose buys are all router 7ff36ab5, tx.from == buyer, gas price 0.051
gwei, in >= 20 pools (the operator's own gas price; launches and freezes are sent at 0.051 too). Everyone else is a stranger. Per stranger
(token, buyer): first buy offset, method, gas price, recipient type, the freeze (the operator's approve(buyer, ...), d09) and its delay,
every movement of the token out of the buyer (sell into the pair, transfer) and whether it came before the freeze; today's transfer test.
-> d10_table.json, d10_table.out"""
import json, os, sys, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from common import *; import rpc
LS = launches(); byt = {o["token"]: o for o in LS}; TX = txs(); T = transfers(); P = pairlogs()
DU = json.load(open(os.path.join(D, "d06_dumps.json"))); FZ = json.load(open(os.path.join(D, "d09_freezes.json")))
frz = {(r["token"], r["target"]): r for r in FZ["rows"]}; OPS = set(FZ["ops"])
launch_tx = set(o["tx"] for o in LS)
swaps = C.defaultdict(list); burns = set()
for r in P:
    if r[5] == "swap": swaps[(r[3], r[4])].append(r)
    if r[5] == "burn": burns.add((r[3], r[4]))
bytx = C.defaultdict(list)
for r in T:
    if r[3] not in launch_tx: bytx[(r[3], r[4])].append(r)
buys = []; moves = C.defaultdict(list)
for (h, tok), rs in bytx.items():
    o = byt[tok]; pair = o["pair"]; blk = rs[0][0]; txi = rs[0][1]
    net = C.Counter()
    for r in rs:
        net[r[5]] -= r[7]; net[r[6]] += r[7]
    sw = swaps.get((h, pair), [])
    q_in = sum((x[6] if o["side"] == 0 else x[7]) for x in sw); q_out = sum((x[8] if o["side"] == 0 else x[9]) for x in sw)
    t = TX.get(h) or [None] * 9
    if net[pair] < 0 and sw and q_in > q_out:            # a buy: the pair lost tokens, took WBNB
        for a, v in net.items():
            if a != pair and a not in DEAD and v > 0:
                buys.append({"token": tok, "pool": pair, "L": o["L"], "size": o["size"], "code": o["code"]["size"], "blk": blk, "off": blk - o["L"], "txi": txi, "tx": h,
                             "buyer": a, "amt": v, "bnb": (q_in - q_out) / 1e18, "tx_from": t[0], "tx_to": t[1], "sel": t[2], "gp": t[3], "self": t[0] == a})
    for a, v in net.items():                              # every address whose balance fell in a tx that is not its own buy
        if a != pair and a not in DEAD and v < 0:
            kind = "sell" if net[pair] > 0 else "transfer"
            moves[(tok, a)].append({"blk": blk, "off": blk - o["L"], "kind": kind, "v": -v, "tx": h, "sel": t[2], "tx_from": t[0]})
pb = C.defaultdict(set); shp = C.defaultdict(set)
for b in buys:
    pb[b["buyer"]].add(b["pool"]); shp[b["buyer"]].add((b["tx_to"] == ROUTER, b["sel"], b["self"], b["gp"]))
CROWD = sorted(a for a in pb if shp[a] == {(True, "7ff36ab5", True, 51000000)} and len(pb[a]) >= 20)
cs = set(CROWD)
print("buys", len(buys), "buyers", len(pb), "crowd wallets", len(CROWD), "crowd frozen ever:", sum(1 for k in frz if k[1] in cs))
first = {}
for b in sorted(buys, key=lambda b: (b["blk"], b["txi"])):
    k = (b["token"], b["buyer"])
    if k not in first: first[k] = dict(b, nbuys=0, bnb_total=0.0)
    first[k]["nbuys"] += 1; first[k]["bnb_total"] += b["bnb"]
S = [k for k in first if k[1] not in cs]
addrs = sorted(set(k[1] for k in S))
codes = rpc.batch([("eth_getCode", [a, "latest"]) for a in addrs]); code = {a: (c.get("result") or "0x") for a, c in zip(addrs, codes)}
bals = rpc.batch([("eth_call", [{"to": k[0], "data": "0x70a08231" + k[1][2:].rjust(64, "0")}, "latest"]) for k in S])
bal = {k: (int(r["result"], 16) if r.get("result") not in (None, "0x") and "error" not in r else None) for k, r in zip(S, bals)}
tk = [k for k in S if bal[k]]
DEADA = "000000000000000000000000000000000000dead".rjust(64, "0")
res = rpc.batch([("eth_call", [{"from": k[1], "to": k[0], "gas": hex(300000), "data": "0xa9059cbb" + DEADA + hex(max(1, bal[k] // 100))[2:].rjust(64, "0")}, "latest"]) for k in tk])
tst = {k: ("ok" if r.get("result") is not None and "error" not in r else "revert") for k, r in zip(tk, res)}
rows = []
for k in S:
    f = first[k]; z = frz.get(k); du = (DU[f["pool"]]["dump"] or {}).get("off")
    mv = [m for m in moves.get(k, []) if m["blk"] >= f["blk"] and m["tx"] != f["tx"]]
    pre = [m for m in mv if z is None or (m["blk"], 0) < (z["fblk"], 0) or (m["blk"] == z["fblk"])]
    c = code[k[1]]; rt = "eoa" if c in ("0x", "") else ("eoa7702" if c.startswith("0xef0100") else "contract")
    rows.append({"token": k[0], "buyer": k[1], "pool": f["pool"], "L": f["L"], "size": f["size"], "code": f["code"], "off": f["off"], "txi": f["txi"], "tx": f["tx"],
                 "nbuys": f["nbuys"], "bnb": round(f["bnb_total"], 6), "sel": f["sel"], "tx_to": f["tx_to"], "tx_from": f["tx_from"], "gp_gwei": (f["gp"] or 0) / 1e9,
                 "self": f["self"], "rtype": rt, "dump_off": du, "before_dump": du is None or f["off"] < du,
                 "frozen": z is not None, "freeze_off": z["foff"] if z else None, "delay": (z["fblk"] - f["blk"]) if z else None, "freeze_op": z["op"] if z else None,
                 "moves": len(mv), "sells": sum(m["kind"] == "sell" for m in mv), "xfers": sum(m["kind"] == "transfer" for m in mv),
                 "moved_before_freeze": len(pre), "first_move_off": mv[0]["off"] if mv else None, "first_move_kind": mv[0]["kind"] if mv else None,
                 "bal_now": bal[k], "test_now": tst.get(k, "no balance" if bal[k] == 0 else "unread")})
rows.sort(key=lambda r: (r["L"], r["off"]))
json.dump({"crowd": CROWD, "rows": rows}, open(os.path.join(D, "d10_table.json"), "w"), indent=0)
print("stranger (token,buyer) rows", len(rows), "before the dump", sum(r["before_dump"] for r in rows))
print("frozen x today's test:", sorted(C.Counter((r["frozen"], r["test_now"]) for r in rows).items()))
