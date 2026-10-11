"""Stage 4: the candidate's claim re-measured on the test slice (recent 2 h, pools the finder did not use) and, separately, on the 11 recent
pools it did use. For every transaction in the whole blocks [L-3, T+3] (ahead of / behind the bot's buy at T), flag any touch of
  the pool id (calldata), the token (calldata, a tx sent to it, any log it emits), the pool's PoolManager logs, T's buyer wallet
  (as sender, recipient incl. plain ETH sends, calldata argument, log topic or log data), Permit2 calls by it.
The candidate says: no touch in [T-12, T) (calldata) and none in [T-4, T) (logs). Here the logs are checked over the whole [L-3, T) too.
Also: the bot's T transaction itself (deadline word 6 minus the T block's timestamp = how long before landing it was signed, gas fields)."""
import pickle, collections, os, json
from lib import *
os.chdir(HERE)
D = pickle.load(open("u2_parsed.pkl", "rb"))
kb = KV("blk"); kr = KV("rcp")
SYS = "0x00000000000000000000000000000000000a4b05"
BOTW = {p["buyer"] for p in D["pools"] if p["buyer"]} | {s["eoa"] for p in D["pools"] for s in p["sw"] if s["who"] == "bot"}
def touches(t, rc, p):
    inp = (t.get("input") or "0x").lower(); frm = t["from"].lower(); to = (t.get("to") or "").lower()
    pid = p["pid"][2:]; tok = p["token"][2:]; buyer = p["buyer"][2:]; out = set()
    if pid in inp: out.add("pid_in_calldata")
    if tok in inp: out.add("token_in_calldata")
    if to == p["token"]: out.add("tx_to_token")
    if frm == p["buyer"]: out.add("buyer_is_sender" + (":permit2" if to == PERMIT2 else ""))
    if to == p["buyer"]: out.add("tx_to_buyer" + (":eth" if int(t["value"], 16) > 0 else ""))
    if buyer in inp and frm != p["buyer"]: out.add("buyer_in_calldata")
    for l in (rc or {}).get("logs", []):
        if l["a"] == p["token"]: out.add("token_log:" + ("Transfer" if l["t"][0] == T_TRANSFER else "Approval" if l["t"][0] == T_APPROVAL else l["t"][0][:10]))
        if l["a"] == PM and len(l["t"]) > 1 and l["t"][1].lower() == p["pid"]:
            out.add("pool_log:" + ("Swap" if l["t"][0] == T_SWAP else "ML" if l["t"][0] == T_ML else "Init" if l["t"][0] == T_INIT else "other"))
        if frm != p["buyer"] and (any(buyer in x.lower() for x in l["t"][1:]) or buyer in (l["d"] or "").lower()): out.add("buyer_in_log:" + l["a"][:10])
        if tok in (l["d"] or "").lower() or any(tok in x.lower() for x in l["t"][1:]): out.add("token_in_log:" + l["a"][:10])
        if pid in (l["d"] or "").lower() and not (l["a"] == PM): out.add("pid_in_log:" + l["a"][:10])
    return out
res = {}
for p in D["pools"]:
    if not (p["recent2h"] and p["T"] is not None): continue
    rows = []
    for bn in range(p["L"] - 3, p["Tbn"] + 4):
        b = kb.d[str(bn)]; rc = {x["tx"]: x for x in kr.d[str(bn)]}
        for t in b["txs"]:
            if t.get("type") == "0x6a" or (t.get("from") or "").lower() == SYS: continue
            ti = int(t["transactionIndex"], 16)
            pos = "T" if t["hash"] == p["Ttx"] else ("before" if (bn < p["Tbn"] or (bn == p["Tbn"] and ti < p["Tti"])) else "after")
            rows.append(dict(bn=bn, d=p["Tbn"] - bn, off=bn - p["L"], pos=pos, hash=t["hash"], frm=t["from"].lower(), to=(t.get("to") or "").lower(),
                             sel=(t.get("input") or "0x")[2:10], touch=sorted(touches(t, rc.get(t["hash"]), p)), status=(rc.get(t["hash"]) or {}).get("status")))
    res[p["pid"]] = rows
pickle.dump(res, open("u4_rows.pkl", "wb"))
def known(r, p):
    """touches explained by the launch (L) and the sentinel's dust buy (L+3)"""
    if r["hash"] == p["launch_tx"]: return "launch"
    if r["frm"] == SENTINEL: return "sentinel"
    if r["frm"] == p["launcher"] and r["bn"] <= p["L"]: return "launcher_prelaunch:" + r["to"][:10] + ":" + r["sel"]
    return None
for label, sel in (("TEST SLICE (recent 2 h, not the finder's)", lambda p: not p["finder"]), ("finder's own recent pools (overlap)", lambda p: p["finder"])):
    G = [p for p in D["pools"] if p["pid"] in res and sel(p)]
    print(f"\n== {label}: {len(G)} pools, L {G[0]['L']}..{G[-1]['L']} ({utc(D['head_ts'] - (D['head'] - G[0]['L']) / D['bps'])} .. {utc(D['head_ts'] - (D['head'] - G[-1]['L']) / D['bps'])} UTC)")
    hit_12 = 0; hit_4log = 0; hit_any = 0; c = collections.Counter(); kinds_before = collections.Counter(); first_after = collections.Counter(); ex = []
    for p in G:
        rows = res[p["pid"]]
        bef = [r for r in rows if r["pos"] == "before" and r["touch"] and not known(r, p)]
        cd = [r for r in bef if r["d"] <= 12 and any(x.startswith(("pid_in_calldata", "token_in_calldata", "buyer_in_calldata", "tx_to", "buyer_is_sender")) for x in r["touch"])]
        lg = [r for r in bef if r["d"] <= 4 and any(x.startswith(("token_log", "pool_log", "buyer_in_log", "token_in_log", "pid_in_log")) for x in r["touch"])]
        hit_12 += bool(cd); hit_4log += bool(lg); hit_any += bool(bef)
        for r in bef:
            kinds_before[(r["off"] - 0, tuple(r["touch"]), r["frm"][:10], r["to"][:10], r["sel"])] += 1
            if len(ex) < 12: ex.append((p["pid"][:12], "L+%d" % r["off"], "T-%d" % r["d"], r["frm"][:10], r["to"][:10], r["sel"], r["touch"]))
        aft = [r for r in rows if r["pos"] == "after" and any("buyer" in x for x in r["touch"])]
        if aft: first_after[(aft[0]["bn"] - p["Tbn"], tuple(aft[0]["touch"]), aft[0]["to"][:10], aft[0]["sel"])] += 1
        else: first_after["none to T+3"] += 1
        kn = collections.Counter(known(r, p) for r in rows if r["pos"] == "before" and r["touch"] and known(r, p))
        c.update(kn)
    print(f"  pools with a calldata/sender/recipient touch of pool, token or buyer in [T-12, T): {hit_12} of {len(G)}")
    print(f"  pools with a log touch (token log, pool log, buyer/token/pid in a log) in [T-4, T): {hit_4log} of {len(G)}")
    print(f"  pools with ANY touch in the whole [L-3, T) besides the launch tx and the sentinel: {hit_any} of {len(G)}; explained touches: {dict(c)}")
    for k, v in kinds_before.most_common(10): print("    ", v, k)
    for e in ex: print("     e.g.", e)
    print("  buyer's first touch after T (block offset from T, flags, to, selector):", first_after.most_common(8))
    # the sentinel and outside swaps ahead of T (pool logs) - what was in the pool before the bot
    pre = collections.Counter()
    for p in G:
        for s in p["sw"]:
            if s["bn"] < p["Tbn"] or (s["bn"] == p["Tbn"] and s["ti"] < p["Tti"]): pre[(s["who"], "L+%d" % s["off"], "buy" if s["buy"] else "sell", round(s["q"] / 1e18, 6))] += 1
    print("  swaps in the pool ahead of T:", pre.most_common(6))
    # the bot's T tx
    lagsig = collections.Counter(); prio = collections.Counter(); nonce = []
    for p in G:
        s = next(s for s in p["sw"] if s["tx"] == p["Ttx"]); b = kb.d[str(p["Tbn"])]
        lagsig[s.get("deadline", 0) - b["ts"]] += 1
        t = next(x for x in b["txs"] if x["hash"] == p["Ttx"]); prio[(t.get("type"), int(t.get("maxPriorityFeePerGas") or "0x0", 16))] += 1
        nonce.append(p["buyer_nonce"])
    print(f"  bot's T tx: deadline - ts(T block) {sorted(lagsig.items())} (1200 = signed in T's own second); tx type/priority fee {prio.most_common(4)}; buyer nonce p10/50/90 {pct(nonce,.1)}/{pct(nonce,.5)}/{pct(nonce,.9)}")
    # status of the bot's T tx
    st_ = collections.Counter(next(r["status"] for r in res[p["pid"]] if r["pos"] == "T") for p in G)
    print("  status of the bot's T tx:", dict(st_))
