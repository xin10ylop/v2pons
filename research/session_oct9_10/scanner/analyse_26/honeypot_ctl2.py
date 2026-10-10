"""positive control, take 2: a hookless ETH pool initialized in the last 30k blocks whose liquidity is still in (Initialize + ModifyLiquidity logs),
same relay buy + sell eth_call as honeypot_sim.py. Appends to honeypot_sim.json."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
exec(open(os.path.join(HERE, "honeypot_sim.py")).read().split("P = load_pools()")[0])
from chain import rpc, T_INIT, T_ML, W, sgn
head = int(rpc("eth_blockNumber", []), 16)
inits = rpc("eth_getLogs", [{"fromBlock": hex(head - 30000), "toBlock": hex(head), "address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}])
cands = []
for l in inits:
    d = l["data"]; hooks = "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3]
    if hooks != "0x" + "0" * 40: continue
    cands.append({"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "fee": W(d, 0), "tick_spacing": sgn(W(d, 1)), "hooks": hooks, "bn": int(l["blockNumber"], 16)})
pids = [c["pid"] for c in cands][-40:]
ml = rpc("eth_getLogs", [{"fromBlock": hex(head - 30000), "toBlock": "latest", "address": PM, "topics": [T_ML, pids]}]) if pids else []
net = {}
for l in ml: net[l["topics"][1]] = net.get(l["topics"][1], 0) + sgn(W(l["data"], 2))
live = [c for c in cands if c["pid"] in pids and net.get(c["pid"], 0) > 0 and c["fee"] <= 10000]
print("hookless inits in 30k blocks:", len(cands), "checked", len(pids), "with liquidity in:", len(live))
out = json.load(open("honeypot_sim.json"))
for p in reversed(live[-5:]):
    ov = {RELAY_AT: {"code": RELAY_CODE, "balance": hex(10**18)}}
    res, err = call(RELAY_AT, SEL_BUY + keyw(p) + w(int(0.0058e18)) + w(0) + w(0), ov)
    toks = int(res, 16) if res else 0
    row = {"control": True, "pid": p["pid"], "token": p["token"], "fee": p["fee"], "bn": p["bn"], "buy_out": toks, "buy_err": err}
    if toks:
        for s in range(0, 12):
            key = "0x" + keccak(bytes.fromhex(w(RELAY_AT) + w(s))).hex()
            r2, e2 = call(p["token"], "0x70a08231" + w(RELAY_AT), {p["token"]: {"stateDiff": {key: "0x" + w(toks)}}})
            if r2 and int(r2, 16) == toks:
                ov2 = {RELAY_AT: {"code": RELAY_CODE, "balance": hex(10**18)}, p["token"]: {"stateDiff": {key: "0x" + w(toks)}}}
                r3, e3 = call(RELAY_AT, SEL_SELL + keyw(p) + w(0) + w(0), ov2)
                row.update({"balance_slot": s, "sell_out_wei": int(r3, 16) if r3 else None, "sell_err": e3, "round_trip": (int(r3, 16) / 0.0058e18 - 1) if r3 else None})
                break
    print(json.dumps(row)[:400]); out.append(row)
    if row.get("sell_out_wei"): break
json.dump(out, open("honeypot_sim.json", "w"), indent=1)
