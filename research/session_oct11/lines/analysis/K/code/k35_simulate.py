"""read-only eth_call simulations at the head on live curves: (1) a holder's sell(tokens, 0, holder) on the curve without any approval;
(2) the holder's token transfer to a fresh address (are transfers locked before graduation?); (3) a buy(eth, 0, x) from a fresh address with
an overridden balance, compared with the curve math incl. the surcharge window. Nothing is sent."""
import json, pickle, collections
from kreplay import *
P = pickle.load(open(os.path.join(DATA, "packed.pkl"), "rb")); CE = P["creates"]; TR = P["trades"]
head = int(rpc("eth_blockNumber", []), 16)
FRESH = "0x00000000000000000000000000000000000c0ffe"
def enc_addr(a): return a[2:].rjust(64, "0")
def enc_u(x): return hex(int(x))[2:].rjust(64, "0")
res = []
cands = sorted([c for c in TR if CE[c]["bn"] > head - 300000], key=lambda c: -CE[c]["bn"])
done = 0
for c in cands:
    ev = TR[c]; hold = collections.Counter()
    for r in ev:
        if r[3] == "B" and r[4][0] == r[4][1]: hold[r[4][1]] += r[5][1]
        if r[3] == "S" and r[4][0] == r[4][1]: hold[r[4][0]] -= r[5][0]
    hs = [(w, t) for w, t in hold.items() if t > 10**18]
    if not hs: continue
    w, t = hs[0]; tok = CE[c]["token"]
    bal = int(rpc("eth_call", [{"to": tok, "data": "0x70a08231" + enc_addr(w)}, "latest"]), 16)
    if bal == 0: continue
    grad = int(rpc("eth_call", [{"to": c, "data": "0xe7c2b772"}, "latest"]), 16)
    if grad: continue
    amt = bal // 2
    o = {"curve": c, "holder": w, "age_blocks": head - CE[c]["bn"], "balance": bal}
    for name, to, data in [("sell_no_approval", c, "0xd04c6983" + enc_u(amt) + enc_u(0) + enc_addr(w)),
                           ("transfer_to_fresh", tok, "0xa9059cbb" + enc_addr(FRESH) + enc_u(amt))]:
        try: o[name] = int(rpc("eth_call", [{"from": w, "to": to, "data": data}, "latest"]) or "0x0", 16)
        except Exception as e: o[name] = "REVERT " + str(e)[:120]
    # a buy of 0.0058 ETH from a fresh address with an overridden balance
    try:
        r_ = rpc("eth_call", [{"from": FRESH, "to": c, "value": hex(5800000000000000), "data": "0x59a87bc1" + enc_u(5800000000000000) + enc_u(0) + enc_addr(FRESH)}, "latest", {FRESH: {"balance": hex(10**18)}}])
        o["buy_0.0058_tokens_out"] = int(r_, 16) if r_ and r_ != "0x" else r_
    except Exception as e: o["buy_0.0058_tokens_out"] = "REVERT " + str(e)[:120]
    rv = rpc("eth_call", [{"to": c, "data": "0x0902f1ac"}, "latest"]); x, y = W(rv, 0), W(rv, 1)
    cf = cfee(ev) or 0
    net = int(5800000000000000 * (1 - 0.01 - cf)); o["model_tokens_out"] = y * net // (x + net); o["cf"] = cf
    gross = x * amt // (y + amt); o["model_sell_eth"] = int(gross * (1 - 0.01 - cf))
    res.append(o); print(json.dumps(o)); done += 1
    if done >= 4: break
json.dump(res, open(os.path.join(OUT, "k35_simulate.json"), "w"), indent=1)
