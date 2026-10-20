"""Stage 4: THE CANDIDATE RULE, re-measured. For every transaction in the fetched whole blocks of each pool (cur: L-3..T+3; old: T-12..T+3),
what it touches, from its sender, target, calldata AND its receipt logs (topics and data, every block, not only T-4..T):
  pool  - the pool id in calldata; a PoolManager log of the pool (Initialize / ModifyLiquidity / Swap / Donate, any event with topic1 = pid)
  token - the token as tx target; the token in calldata; any log emitted by the token; the token in any log's topics or data
  buyer - T's buyer wallet (the sender of the bot's first buy) as sender, as target (incl. a plain ETH send), in calldata, in any log topic/data
  launcher - the pool's launcher as sender or target or in calldata/logs (extra, outside the candidate)
d = Tbn - bn (blocks before T; d = 0 is T's own block ahead of the bot's tx, 'T' the bot's tx, 'after' everything behind it).
-> touch.pkl (rows), s4_touch.out"""
import pickle, collections, sys
from lib import *
CUR0 = 85553521
SYS = "0x00000000000000000000000000000000000a4b05"
mid = pickle.load(open("parsed_mid.pkl", "rb"))["pools"]; old = pickle.load(open("parsed_old.pkl", "rb"))["pools"]
SETS = {"cur": [p for p in mid if p["L"] >= CUR0 and p["T"] is not None], "old": [p for p in old if p["T"] is not None]}
kb = KV("blk"); kr = KV("rcp")
rows = []; facts = []
for sname, P in SETS.items():
    for p in P:
        pid = p["pid"].lower()[2:]; tok = p["token"].lower()[2:]; buyer = p["buyer"][2:]; lau = p["launcher"][2:]
        lo = p["L"] - 3 if sname == "cur" else p["Tbn"] - 12
        have = [bn for bn in range(lo, p["Tbn"] + 4) if str(bn) in kb.d and str(bn) in kr.d]
        facts.append(dict(set=sname, pid=p["pid"], L=p["L"], T=p["T"], Tbn=p["Tbn"], lo=lo, need=p["Tbn"] + 4 - lo, have=len(have),
                          ts_T=kb.d[str(p["Tbn"])]["ts"] if str(p["Tbn"]) in kb.d else None, ts_L=kb.d[str(p["L"])]["ts"] if str(p["L"]) in kb.d else None))
        for bn in have:
            b = kb.d[str(bn)]; rc = {x["tx"]: x for x in kr.d[str(bn)]}
            for t in b["txs"]:
                frm = (t.get("from") or "").lower(); to = (t.get("to") or "").lower()
                if t.get("type") == "0x6a" or frm == SYS: continue
                inp = (t.get("input") or "0x").lower(); r = rc.get(t["hash"]) or {}
                ti = int(t["transactionIndex"], 16)
                tc = set()
                if pid in inp: tc.add("pool:pid_in_calldata")
                if to[2:] == tok: tc.add("token:target")
                if tok in inp: tc.add("token:in_calldata")
                if frm[2:] == buyer: tc.add("buyer:sender")
                if to[2:] == buyer: tc.add("buyer:target" + ("+eth" if int(t["value"], 16) > 0 else ""))
                if buyer in inp and frm[2:] != buyer: tc.add("buyer:in_calldata")
                if frm[2:] == lau: tc.add("launcher:sender")
                if to[2:] == lau: tc.add("launcher:target")
                if lau in inp and frm[2:] != lau: tc.add("launcher:in_calldata")
                for l in r.get("logs", []):
                    tp = [x.lower() for x in l["t"]]; dat = (l["d"] or "").lower()
                    if l["a"] == PM and len(tp) > 1 and tp[1][2:] == pid:
                        tc.add("pool:log_" + {T_SWAP: "Swap", T_ML: "ML", T_INIT: "Init"}.get(tp[0], tp[0][:10]))
                    if l["a"][2:] == tok: tc.add("token:log_" + {T_TRANSFER: "Transfer", T_APPROVAL: "Approval"}.get(tp[0], tp[0][:10]))
                    elif any(tok in x for x in tp[1:]) or tok in dat: tc.add("token:in_log_of_" + l["a"][:10])
                    if frm[2:] != buyer and (any(buyer in x for x in tp[1:]) or buyer in dat): tc.add("buyer:in_log_of_" + l["a"][:10])
                    if frm[2:] != lau and (any(lau in x for x in tp[1:]) or lau in dat): tc.add("launcher:in_log")
                if t["hash"] == p["Ttx"]: pos = "T"
                elif bn < p["Tbn"] or (bn == p["Tbn"] and ti < p["Tti"]): pos = "before"
                else: pos = "after"
                rows.append(dict(set=sname, pid=p["pid"], L=p["L"], T=p["T"], d=p["Tbn"] - bn, off=bn - p["L"], ti=ti, pos=pos, hash=t["hash"], frm=frm, to=to,
                                 sel=inp[2:10], val=int(t["value"], 16), clen=(len(inp) - 2) // 2, status=r.get("status"), touch=sorted(tc),
                                 prio=int(t["maxPriorityFeePerGas"], 16) if t.get("maxPriorityFeePerGas") else None))
pickle.dump({"rows": rows, "facts": facts}, open("touch.pkl", "wb"))
F = {f["pid"]: f for f in facts}
for sname in SETS:
    fs = [f for f in facts if f["set"] == sname]; ok = {f["pid"] for f in fs if f["have"] == f["need"]}
    print(f"\n===== set {sname}: pools {len(fs)}, with every block of the window fetched (blocks + receipts): {len(ok)}")
    R = [r for r in rows if r["set"] == sname and r["pid"] in ok]
    cand = lambda r: [x for x in r["touch"] if x.startswith(("pool:", "token:", "buyer:"))]
    # the candidate rule: first touch before T at d >= 1 (or d = 0 ahead of the bot's tx)
    for lab, dlo, dhi in (("d 1..4", 1, 4), ("d 0..4 (T's block ahead of the bot incl.)", 0, 4), ("d 0..12", 0, 12), ("d 5..12", 5, 12)):
        hit = {r["pid"] for r in R if r["pos"] == "before" and dlo <= r["d"] <= dhi and cand(r)}
        print(f"  pools with a pool/token/buyer touch before the bot's buy at {lab}: {len(hit)} of {len(ok)}")
    # by kind and d
    c = collections.Counter()
    for r in R:
        if r["pos"] == "before" and r["d"] <= 12:
            for x in cand(r): c[(x, r["d"])] += 1
    kinds = sorted(set(k for k, _ in c))
    print("  touches before the bot's buy, by kind and d (pools-rows) d=0..12:")
    for k in kinds: print(f"    {k:45s} " + " ".join(f"{c[(k, d)]:3d}" for d in range(13)))
    # background (cur only): blocks L+4..T-13
    if sname == "cur":
        bgc = collections.Counter(); bgb = 0
        for f in fs:
            if f["pid"] in ok: bgb += max(0, (f["Tbn"] - 13) - (f["L"] + 4) + 1)
        bgp = collections.defaultdict(set)
        for r in R:
            if r["pos"] == "before" and r["d"] >= 13 and r["off"] >= 4:
                for x in cand(r): bgp[x].add((r["pid"], r["off"]))
        print(f"  background L+4..T-13 ({bgb} blocks): blocks holding each kind:", {k: len(v) for k, v in bgp.items()} or "none")
        lt = collections.Counter()
        for r in R:
            if r["pos"] == "before" and r["off"] < 4:
                for x in cand(r): lt[(x, r["off"])] += 1
        print("  launch-time touches (offset < 4 from L), kind/offset -> rows:", sorted(lt.items(), key=lambda kv: (kv[0][1], kv[0][0]))[:30])
    # first touch after T (the buyer's first appearance after its buy)
    aft = collections.Counter()
    for r in R:
        if r["pos"] == "after":
            for x in cand(r):
                if not x.startswith("pool:log_Swap"): aft[(x, -r["d"])] += 1
    print("  touches behind the bot's buy to T+3 (kind, blocks after T) -> rows:", sorted(aft.items(), key=lambda kv: (kv[0][1], -kv[1]))[:25])
    st_ = collections.Counter(r["status"] for r in R if r["pos"] == "T"); print("  status of the bot's T tx:", dict(st_))
    ex = [r for r in R if r["pos"] == "before" and r["d"] <= 12 and cand(r)]
    for r in ex[:12]:
        print(f"    e.g. L {r['L']} T {r['T']} d {r['d']} off {r['off']} {r['hash'][:12]} {r['frm'][:10]} -> {r['to'][:10]} {r['sel']} val {r['val']/1e18:.6f} {cand(r)}")
