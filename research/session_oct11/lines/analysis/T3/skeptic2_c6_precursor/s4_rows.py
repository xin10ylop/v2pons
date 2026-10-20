"""Stage 4: every transaction in the whole blocks [L-3, T+3] of every slice pool, classified exactly as the finder's s4_classify.py does
(sender class, target class, selector, value, what it touches: the pool id, token, T's buyer wallet, other line pools' logs), so that the
finder's key strings can be re-measured on new pools. Line pools = Initialize at the 3.0 or 2.4333 launch price without a hook in this
window, plus the finder's 465 line pools (ids only). Touch flags from logs exist only where receipts were fetched ([T-12, T+3]);
'rcp' marks that. Extra fields: bot_buy (a tx to the bot router with c1120e3d), bot_any (any tx to the bot router). -> s4_rows.pkl"""
import pickle, collections, json, os
from lib import *
os.chdir(HERE)
D = pickle.load(open("s2_parsed.pkl", "rb")); ALL = D["pools"]
P = sorted([p for p in ALL if p["in_slice"] and p["T"] is not None], key=lambda p: p["L"])
S1 = json.load(open("s1_pools.json"))
kb = KV("blk"); kr = KV("rcp")
P2433 = 1604517591721945638372359205383840
line_pid = {}; line_tok = {}
for i in S1["inits"]:
    if i["hook"] == 0 and i["sp"] in (SQRT30, P2433): line_pid[i["pid"]] = "3.0" if i["sp"] == SQRT30 else "2.433"; line_tok[i["tok"].lower()] = 1
F = json.load(open(os.path.join(HERE, "..", "precursor", "pools.json")))
launchers = set(p["launcher"] for p in ALL)
for p in F["pools"]:
    line_pid.setdefault(p["pid"].lower(), p["line"]); line_tok[p["token"].lower()] = 1; launchers.add(p["launcher"].lower())
botw = collections.Counter(); pullers = collections.Counter()
for p in ALL:
    for s in p["sw"]:
        if s["bot"]: botw[s["eoa"]] += 1
    for m in p["ml"]:
        if m["dL"] < 0: pullers[m["eoa"]] += 1
SYS = "0x00000000000000000000000000000000000a4b05"
for bn, b in kb.d.items():
    for t in b["txs"]:
        to = (t.get("to") or "").lower(); inp = t.get("input") or "0x"
        if to == BOT and inp[2:10] == "c1120e3d": botw[t["from"].lower()] += 0
        if to == POSM and (len(inp) - 2) // 2 == 1444 and int(t["value"], 16) in (3 * 10 ** 18, 2433328500000000000): launchers.add(t["from"].lower())
BOTW = set(botw)
print("line pools", len(line_pid), "bot wallets", len(BOTW), "pull senders", len(pullers), "launchers", len(launchers))
def cls_addr(a, p):
    a = (a or "").lower()
    if not a: return "create"
    if a == p["buyer"]: return "BUYER"
    if a == p["launcher"]: return "LAUNCHER"
    if a == BOT: return "BOTROUTER"
    if a == UR: return "UR"
    if a == POSM: return "POSM"
    if a == PM: return "PM"
    if a == PERMIT2: return "PERMIT2"
    if a == SENTINEL: return "SENTINEL"
    if a == p["token"].lower(): return "TOKEN"
    if a in BOTW: return "botwallet"
    if a in pullers: return "puller"
    if a in launchers: return "otherlauncher"
    if a in line_tok: return "linetoken"
    if a == SYS: return "SYS"
    return "other"
rows = []; facts = []
for p in P:
    tok = p["token"].lower(); pid = p["pid"].lower(); buyer = p["buyer"]
    for bn in range(p["L"] - 3, p["Tbn"] + 4):
        b = kb.d.get(str(bn)); r = kr.d.get(str(bn))
        if b is None: continue
        rc = {x["tx"]: x for x in (r or [])}
        for t in b["txs"]:
            if t.get("type") in ("0x6a",) or (t.get("from") or "").lower() == SYS: continue
            ti = int(t["transactionIndex"], 16); inp = (t.get("input") or "0x").lower(); frm = t["from"].lower(); to = (t.get("to") or "").lower()
            rcp = rc.get(t["hash"]) or {}; lg = rcp.get("logs", []); touch = set(); other_pool_logs = []
            if pid[2:] in inp: touch.add("pid_in_input")
            if tok[2:] in inp: touch.add("token_in_input")
            if buyer[2:] in inp and frm != buyer: touch.add("buyer_in_input")
            for l in lg:
                if l["a"] == tok: touch.add("token_log:" + ("Transfer" if l["t"][0] == T_TRANSFER else "Approval" if l["t"][0] == T_APPROVAL else l["t"][0][:10]))
                if l["a"] == PM and len(l["t"]) > 1 and l["t"][1].lower() == pid: touch.add("pool_log:" + ("Swap" if l["t"][0] == T_SWAP else "ML" if l["t"][0] == T_ML else "Init" if l["t"][0] == T_INIT else "other"))
                if any(buyer[2:] in x.lower() for x in l["t"][1:]) and frm != buyer: touch.add("buyer_in_log:" + l["a"][:10])
                if l["a"] == PM and len(l["t"]) > 1 and l["t"][1].lower() != pid:
                    other_pool_logs.append((l["t"][1].lower(), l["t"][0][:10]))
                    if l["t"][1].lower() in line_pid:
                        touch.add("otherline_" + line_pid[l["t"][1].lower()] + ":" + ("Swap" if l["t"][0] == T_SWAP else "ML" if l["t"][0] == T_ML else "Init" if l["t"][0] == T_INIT else "x"))
            d = p["Tbn"] - bn
            pos = "T" if t["hash"] == p["Ttx"] else ("before" if (bn < p["Tbn"] or (bn == p["Tbn"] and ti < p["Tti"])) else "after")
            rows.append(dict(L=p["L"], pid=p["pid"], d=d, off=bn - p["L"], ti=ti, pos=pos, hash=t["hash"], frm=frm, to=to, fc=cls_addr(frm, p), tc=cls_addr(to, p),
                             sel=inp[2:10], val=int(t["value"], 16), status=rcp.get("status"), touch=sorted(touch), clen=(len(inp) - 2) // 2, rcp=r is not None,
                             other_pool_logs=other_pool_logs, bot_buy=(to == BOT and inp[2:10] == "c1120e3d"), bot_any=(to == BOT),
                             prio=int(t["maxPriorityFeePerGas"], 16) if t.get("maxPriorityFeePerGas") else None))
    facts.append(dict(L=p["L"], pid=p["pid"], T=p["T"], Tbn=p["Tbn"], Tti=p["Tti"], buyer=buyer, Tq=p["Tq"],
                      have_blocks=sum(1 for bn in range(p["L"] - 3, p["Tbn"] + 4) if str(bn) in kb.d), need_blocks=p["Tbn"] + 7 - p["L"],
                      near_ok=all(str(bn) in kb.d and str(bn) in kr.d for bn in range(p["Tbn"] - 12, p["Tbn"] + 4))))
pickle.dump({"rows": rows, "facts": facts}, open("s4_rows.pkl", "wb"))
print("pools", len(P), "rows", len(rows), "pools with every block", sum(1 for f in facts if f["have_blocks"] == f["need_blocks"]), "near_ok", sum(f["near_ok"] for f in facts))
