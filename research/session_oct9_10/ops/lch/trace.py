"""Money graph around launches: deployer funding back 3 hops, pull proceeds forward 2 hops. Block scans via bc.py cache.
Usage: trace.py <pid-prefix> [...]   -> writes tr/<pid10>.json"""
import sys, json, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bc
D = os.path.dirname(os.path.abspath(__file__)) + "/tr/"; os.makedirs(D, exist_ok=True)
LA = json.load(open(os.path.dirname(os.path.abspath(__file__)) + "/launches.json"))
FAM = LA["fam"]
HEAD = None
def head():
    global HEAD
    if HEAD is None: HEAD = int(bc.rpc("eth_blockNumber", []), 16)
    return HEAD
def T(bn, ts, t): return {"bn": bn, "ts": ts, "utc": time.strftime("%m-%d %H:%M:%S", time.gmtime(ts)), "hash": t[0], "from": t[1], "to": t[2], "eth": int(t[3]) / 1e18, "nonce": t[4], "sel": t[5], "len": t[6]}
def incoming(addr, before, maxback=30000, want=1, extra=300):
    """value>0 txs to addr before block `before`, scanning backwards; after the first hit look only `extra` blocks further back"""
    out = []; lo = max(0, before - maxback)
    for bn, ts, t in bc.txs_desc(lo, before - 1):
        if out and bn < out[0]["bn"] - extra: break
        if t[2] == addr and int(t[3]) > 0:
            out.append(T(bn, ts, t))
    return out, lo
def outgoing(addr, after, maxfwd=20000, want=3, min_eth=0.0, extra=300):
    out = []; hi = min(head() - 5, after + maxfwd)
    for bn, ts, t in bc.txs(after, hi):
        if out and bn > out[0]["bn"] + extra: break
        if t[1] == addr and int(t[3]) / 1e18 >= min_eth:
            out.append(T(bn, ts, t))
            if len(out) >= want: break
    return out, hi
def tag(a):
    if a in FAM: return "crowd_" + FAM[a]
    return ""
def trace(L):
    d = L["deployer"]; b0 = L["b0"]; res = {"launch": L, "back": [], "fwd": []}
    # backwards: who funded the deployer, then who funded the funder, then one more
    cur, before = d, b0
    for hop in range(3):
        inc, lo = incoming(cur, before, maxback=20000 if hop < 2 else 12000)
        res["back"].append({"hop": hop + 1, "addr": cur, "scanned_from": lo, "scanned_to": before - 1, "incoming": inc})
        if not inc: break
        f = max(inc, key=lambda x: x['eth'])
        if f["nonce"] > 50: res["back"][-1]["stop"] = "funder nonce %d (not fresh)" % f["nonce"]; break
        cur, before = f["from"], f["bn"]
    # the deployer's funder: everything it sent around then (who else it funded)
    if res["back"] and res["back"][0]["incoming"]:
        f0 = max(res["back"][0]["incoming"], key=lambda x: x["eth"])
        o, _ = outgoing(f0["from"], f0["bn"] - 100, maxfwd=600, want=200, extra=150)
        res["funder_sends"] = [{"to": x["to"], "eth": x["eth"], "nonce": x["nonce"], "bn": x["bn"], "tag": tag(x["to"])} for x in o]
    # forwards: deployer's txs after the pull, then where the ETH went
    pb = L["pull_bn"]
    if pb:
        o, hi = outgoing(d, pb + 1, maxfwd=20000, want=3)
        res["fwd"].append({"hop": 1, "addr": d, "scanned": [pb + 1, hi], "out": o})
        big = [x for x in o if x["eth"] > 0.05]
        if big:
            r = big[0]["to"]
            o2, hi2 = outgoing(r, big[0]["bn"], maxfwd=20000, want=3)
            res["fwd"].append({"hop": 2, "addr": r, "scanned": [big[0]["bn"], hi2], "out": o2})
            ins = [T(bn, ts, t) for bn, ts, t in bc.txs(big[0]["bn"] - 100, big[0]["bn"] + 100) if t[2] == r and int(t[3]) > 0]
            res["collector_in"] = [{"from": x["from"], "eth": x["eth"], "nonce": x["nonce"], "bn": x["bn"], "tag": tag(x["from"])} for x in ins]
    json.dump(res, open(D + L["pid"][:10] + ".json", "w"), indent=1)
    return res
if __name__ == "__main__":
    want = sys.argv[1:]
    for L in LA["launches"]:
        if any(L["pid"].startswith(w) for w in want):
            if os.path.exists(D + L["pid"][:10] + ".json"): continue
            t0 = time.time(); r = trace(L)
            print(L["utc"], L["family"], L["pid"][:10], "done %.0fs" % (time.time() - t0), flush=True)
