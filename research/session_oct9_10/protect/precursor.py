#!/usr/bin/env python3
"""What precedes the pull: for every pull that came <= 60 blocks after a non-crowd real buy (the reactions), every transaction in the
blocks from the buy - 2 to the pull + 1, tagged: the pulling deployer (from / to / named in input), the pool's token (to / named),
the PositionManager, crowd wallets (A / B / fresh / speck, any pool), other operator deployers (launches, pulls), the launcher.
Also the pull transaction itself (type, gas, fees, index) against the launch transaction. Writes precursor.json."""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from classify import *
from chain import batch, rpc, OP
HERE = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect/"
M = json.load(open(HERE + "measure.json"))
pools = load(); cw = annotate(pools)
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; LAUNCHER = "0x" + OP
deployers = {p["deployer"]: p for p in pools}
by_pid = {p["pid"][:10]: p for p in pools}
# crowd wallets of every family (from measure's families: recompute quickly)
L = collections.defaultdict(set)
for p in pools:
    for x in p["sw"]:
        if x["from"] in cw: L[x["from"]].add(p["pid"])
cases = [r for r in M["noncrowd_buys"] if r["lag_blocks"] is not None and r["lag_blocks"] <= 60]
out = []
for r in cases:
    p = by_pid[r["pid"]]; b0 = p["b0"]; X = b0 + r["offset"]; P = p["pull"]["bn"]; dep = p["deployer"]; tok = p["m"]["token"]
    blks = batch([("eth_getBlockByNumber", [hex(b), True]) for b in range(X - 2, P + 2)])
    pull_tx = None; launch_tx = None; ev = []
    for blk in blks:
        bn = int(blk["number"], 16)
        for t in blk["transactions"]:
            fr = t["from"].lower(); to = (t.get("to") or "").lower(); inp = t["input"].lower()
            tags = []
            if fr == dep: tags.append("DEPLOYER_SENDS")
            if to == dep: tags.append("TO_DEPLOYER value %.6f" % (int(t["value"], 16) / 1e18))
            if dep[2:] in inp and fr != dep: tags.append("NAMES_DEPLOYER")
            if to == "0x" + tok: tags.append("TO_TOKEN " + inp[:10])
            if tok in inp and to != "0x" + tok and fr != dep: tags.append("NAMES_TOKEN")
            if to == POSM and fr != dep: tags.append("POSM " + inp[:10])
            if to == LAUNCHER or inp[:10] == "0x2fcb9108": tags.append("LAUNCH")
            if fr in deployers and fr != dep: tags.append("OTHER_DEPLOYER " + deployers[fr]["pid"][:10] + " n" + str(int(t["nonce"], 16)))
            if fr in cw: tags.append("CROWD" + ("_this_pool" if p["pid"] in L[fr] and tok in inp else ""))
            if fr == US: tags.append("US")
            if tags:
                ev.append({"bn": bn, "rel_pull": bn - P, "rel_buy": bn - X, "idx": int(t["transactionIndex"], 16), "from": fr[:10], "to": to[:10], "sel": inp[:10], "value": int(t["value"], 16) / 1e18, "tags": tags})
            if fr == dep and bn == P: pull_tx = t
    lt = rpc("eth_getTransactionByHash", [p["m"]["tx"]])
    def fees(t): return {"type": int(t["type"], 16), "gas": int(t["gas"], 16), "maxFee_gwei": int(t.get("maxFeePerGas", t.get("gasPrice", "0x0")), 16) / 1e9, "prio_gwei": int(t.get("maxPriorityFeePerGas", "0x0"), 16) / 1e9, "nonce": int(t["nonce"], 16), "idx": int(t["transactionIndex"], 16), "len": (len(t["input"]) - 2) // 2}
    o = {"case": f"{r['time_utc']} {r['who']} {r['wallet'][:10]} {r['size_eth']} +{r['offset']} lag {r['lag_blocks']}", "pid": r["pid"], "pull_tx": fees(pull_tx) if pull_tx else None, "launch_tx": fees(lt),
         "events": [e for e in ev if not (e["tags"] == ["DEPLOYER_SENDS"] and e["rel_pull"] == 0)]}
    out.append(o)
    print("\n==", o["case"], "| pull tx", o["pull_tx"], "| launch tx", o["launch_tx"])
    for e in o["events"]:
        if any(t.startswith(("CROWD",)) for t in e["tags"]) and len(e["tags"]) == 1: continue      # crowd trading in other pools: counted below
        print(f"   pull{e['rel_pull']:+4d} buy{e['rel_buy']:+4d} idx {e['idx']:3d} {e['from']} -> {e['to']} {e['sel']} {e['value']:.5f} {e['tags']}")
    cc = collections.Counter((e["rel_pull"] < 0) for e in o["events"] if any(t.startswith("CROWD") for t in e["tags"]))
    tp = [e for e in o["events"] if "CROWD_this_pool" in e["tags"]]
    print(f"   crowd txs in the window (any pool): {sum(cc.values())}; in this pool: {[(e['rel_pull'], e['sel'], round(e['value'], 4)) for e in tp]}")
json.dump(out, open(HERE + "precursor.json", "w"), indent=1)
