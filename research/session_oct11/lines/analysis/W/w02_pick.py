"""pick tx hashes per shape for the V3 line (crowd contracts' two calls, SwapRouter02 buys and sells, UR) to fetch in full"""
import pickle, json
C = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/analysis/C"
R = pickle.load(open(C + "/v23.pkl", "rb")); E = pickle.load(open(C + "/ev.pkl", "rb")); T = pickle.load(open(C + "/tx.pkl", "rb"))
L = [r for r in R.values() if r["dex"] == "v3" and (r["fam"]["lc"] or "").startswith("0a493d1a") and r["launch"]["selector"] == "ac9650d8"
     and r["launch"]["calldata_len"] == 836 and r["fee"] == 100 and r["launch"]["value_eth"] == 0]
L.sort(key=lambda r: -r["launch_block"])
want = {}
for r in L:
    o = E[r["pool"]]; qs = r["quote_side"]
    for e in o["ev"]:
        if e[0] != "s": continue
        dq = e[7] if qs == 0 else e[8]; t = T.get(e[-1])
        if not t: continue
        kind = "buy" if dq > 0 else "sell"
        k = (kind, (t["to"] or "")[:10], t["selector"], t["calldata_len"], (t["value_wei"] or 0) > 0)
        want.setdefault(k, [])
        if len(want[k]) < 2: want[k].append({"hash": e[-1], "pool": r["pool"], "token": r["token"], "qs": qs, "dq": dq, "dt": e[8] if qs == 0 else e[7], "bn": e[1], "lb": o["lb"], "value": t["value_wei"], "from": t["from"], "to": t["to"]})
keep = {k: v for k, v in want.items() if k[1] in ("0x80114879", "0xd26c8cfc", "0xa28f468c", "0xaf9d6fa0", "0xcaf681a6", "0x84021dc2", "0xfc7241d4")}
json.dump([[list(k), v] for k, v in keep.items()], open("w02_pick.json", "w"), indent=0)
for k, v in keep.items(): print(k, len(v), v[0]["hash"])
