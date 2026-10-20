"""positive control for honeypot_sim.py: the same eth_call buy + sell through the relay on recent hookless pools that had sells in the census
(stops at the first pool whose buy returns tokens). Appends to honeypot_sim.json."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
src = open(os.path.join(HERE, "honeypot_sim.py")).read().split("P = load_pools()")[0]
exec(src)
P = load_pools()
cands = sorted([p for p in P.values() if p["hooks_zero"] and not p["n_pulls"] and p["n_sells"] >= 3 and p["n_buys"] >= 5 and p["fee"] <= 10000], key=lambda p: -p["launch_block"])[:6]
out = json.load(open("honeypot_sim.json"))
for p in cands:
    ov = {RELAY_AT: {"code": RELAY_CODE, "balance": hex(10**18)}}
    res, err = call(RELAY_AT, SEL_BUY + keyw(p) + w(int(0.0058e18)) + w(0) + w(0), ov)
    toks = int(res, 16) if res else 0
    row = {"control": True, "pid": p["pid"], "family": p["family"], "token": p["token"], "buy_out": toks, "buy_err": err}
    if toks:
        key = "0x" + keccak(bytes.fromhex(w(RELAY_AT) + w(0))).hex()
        r2, e2 = call(p["token"], "0x70a08231" + w(RELAY_AT), {p["token"]: {"stateDiff": {key: "0x" + w(toks)}}})
        if r2 and int(r2, 16) == toks:
            ov2 = {RELAY_AT: {"code": RELAY_CODE, "balance": hex(10**18)}, p["token"]: {"stateDiff": {key: "0x" + w(toks)}}}
            r3, e3 = call(RELAY_AT, SEL_SELL + keyw(p) + w(0) + w(0), ov2)
            row.update({"balance_slot": 0, "sell_out_wei": int(r3, 16) if r3 else None, "sell_err": e3, "round_trip": (int(r3, 16) / 0.0058e18 - 1) if r3 else None})
        else: row["balance_slot"] = None
    print(json.dumps(row)[:400]); out.append(row)
    if row.get("sell_out_wei"): break
json.dump(out, open("honeypot_sim.json", "w"), indent=1)
