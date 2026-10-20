"""Stage 4: every transaction in the whole blocks [L-3, T+3] of every 3.0 pool (T = the block of the bot's first buy), classified by sender,
target, selector, value and what it touches (the pool id, the token, the bot router, the PositionManager, Permit2, the buyer wallet of T,
the launcher, the sentinel, other bot wallets, the other line pools). Output: events.pkl (one row per tx per pool, with d = Tbn - bn, the
blocks before T; same-block rows ahead of the bot's tx have d = 0, rows behind it d = -0) and wallet facts per pool."""
import pickle, collections, json
from lib import *
D = pickle.load(open("parsed.pkl", "rb")); ALL = D["pools"]
P = sorted([p for p in ALL if p["line"] == "3.0" and p["T"] is not None], key=lambda p: p["L"])
kb = KV("blk"); kr = KV("rcp")
import sys
NORCP = "--norcp" in sys.argv   # first look before the receipts are in: touch flags from inputs only
# known parties from the line pools (both lines)
botw = collections.Counter(); pullers = collections.Counter(); launchers = set(); line_pid = {}; line_tok = {}
for p in ALL:
    launchers.add(p["launcher"]); line_pid[p["pid"]] = p; line_tok[p["token"].lower()] = p
    for w in set(s["eoa"] for s in p["sw"] if s["bot"]): botw[w] += 1
    for m in p["ml"]:
        if m["dL"] < 0: pullers[m["eoa"]] += 1
BOTW = set(botw)
print("bot buyer wallets (both lines):", len(BOTW), "pull senders:", pullers.most_common(5), "launchers:", len(launchers))
SYS = "0x00000000000000000000000000000000000a4b05"
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
            rcp = rc.get(t["hash"]) or {}
            lg = rcp.get("logs", [])
            touch = set()
            if pid[2:] in inp: touch.add("pid_in_input")
            if tok[2:] in inp: touch.add("token_in_input")
            if buyer[2:] in inp and frm != buyer: touch.add("buyer_in_input")
            for l in lg:
                if l["a"] == tok: touch.add("token_log:" + ("Transfer" if l["t"][0] == T_TRANSFER else "Approval" if l["t"][0] == T_APPROVAL else l["t"][0][:10]))
                if l["a"] == PM and len(l["t"]) > 1 and l["t"][1].lower() == pid: touch.add("pool_log:" + ("Swap" if l["t"][0] == T_SWAP else "ML" if l["t"][0] == T_ML else "Init" if l["t"][0] == T_INIT else "other"))
                if any(buyer[2:] in x.lower() for x in l["t"][1:]) and frm != buyer: touch.add("buyer_in_log:" + l["a"][:10])
                if l["a"] == PM and len(l["t"]) > 1 and l["t"][1].lower() in line_pid and l["t"][1].lower() != pid:
                    touch.add("otherline_" + line_pid[l["t"][1].lower()]["line"] + ":" + ("Swap" if l["t"][0] == T_SWAP else "ML" if l["t"][0] == T_ML else "Init" if l["t"][0] == T_INIT else "x"))
            d = p["Tbn"] - bn
            pos = "T" if t["hash"] == next(s["tx"] for s in p["sw"] if s["bot"]) else ("before" if (bn < p["Tbn"] or (bn == p["Tbn"] and ti < p["Tti"])) else "after")
            rows.append(dict(L=p["L"], pid=p["pid"], d=d, off=bn - p["L"], ti=ti, pos=pos, hash=t["hash"], frm=frm, to=to, fc=cls_addr(frm, p), tc=cls_addr(to, p), sel=inp[2:10],
                             val=int(t["value"], 16), nonce=int(t["nonce"], 16), status=rcp.get("status"), touch=sorted(touch), clen=(len(inp) - 2) // 2,
                             prio=int(t["maxPriorityFeePerGas"], 16) if t.get("maxPriorityFeePerGas") else None, gas=int(t["gas"], 16) if t.get("gas") else None))
    facts.append(dict(L=p["L"], pid=p["pid"], T=p["T"], Tbn=p["Tbn"], buyer=buyer, buyer_nonce=p["buyer_nonce"], Tq=p["Tq"], launcher=p["launcher"],
                      launcher_nonce=p["launcher_nonce"], have_blocks=sum(1 for bn in range(p["L"] - 3, p["Tbn"] + 4) if str(bn) in kb.d), need_blocks=p["Tbn"] + 7 - p["L"],
                      have_rcp=sum(1 for bn in range(p["L"] - 3, p["Tbn"] + 4) if str(bn) in kr.d),
                      near_ok=all(str(bn) in kb.d and (NORCP or str(bn) in kr.d) for bn in range(max(p["L"] - 3, p["Tbn"] - 12), p["Tbn"] + 4))))
pickle.dump({"rows": rows, "facts": facts, "botw": dict(botw), "pullers": dict(pullers)}, open("events.pkl", "wb"))
print("pools", len(P), "rows", len(rows), "complete pools", sum(1 for f in facts if f["have_blocks"] == f["need_blocks"] == f["have_rcp"]))
