"""Stage 4: every transaction in the whole blocks [L+1, T+3] of every 3.0 pool with a bot buy, classified exactly as the precursor angle's
s4_classify.py does (sender class, target class, selector, value, what it touches), with d = Tbn - bn (rows in T's block ahead of the bot's
tx: d = 0, pos 'before'). Differences, all in the direction of MORE coverage: the touch flags from logs come from (a) every log of the pool's
token in [L, L+120] (eth_getLogs on the token, uniform over every d, where the finder had receipts only for d 0..4) and (b) the Swap /
ModifyLiquidity logs of every 1,444-byte launch pool in the slice ('another line pool'); no receipts, so 'buyer_in_log' only from token
logs. -> events.pkl"""
import pickle, collections, json
from lib import *
D = pickle.load(open("parsed.pkl", "rb")); ALL = D["pools"]; J = json.load(open("pools.json"))
P = sorted([p for p in ALL if p["T"] is not None], key=lambda p: p["L"])
kb = KV("blk")
botw = collections.Counter(); pullers = collections.Counter()
for p in ALL:
    for w in set(s["eoa"] for s in p["sw"] if s["bot"]): botw[w] += 1
    for m in p["ml"]:
        if m["dL"] < 0: pullers[m["eoa"]] += 1
BOTW = set(botw)
line_pid = {l["pid"]: l for l in J["launches"]}; line_tok = {l["token"]: l for l in J["launches"]}; launchers = set(l["launcher"] for l in J["launches"])
evtx = collections.defaultdict(list)            # tx -> [(pid, line, kind)] for every Swap/ML of every 1444-byte pool
for l in J["launches"]:
    for e in l["ev"]: evtx[e["tx"]].append((l["pid"], l["line"], "Swap" if e["kind"] == "swap" else "ML"))
print("bot buyer wallets:", len(BOTW), "pull senders:", pullers.most_common(3), "line launchers:", len(launchers), "line pools:", len(line_pid))
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
    tlog = collections.defaultdict(list)
    for x in p["tlogs"]: tlog[x["tx"]].append(x)
    for bn in range(p["L"] + 1, p["Tbn"] + 4):
        b = kb.d.get(str(bn))
        if b is None: continue
        for t in b["txs"]:
            if t.get("type") in ("0x6a",) or (t.get("from") or "").lower() == SYS: continue
            ti = int(t["transactionIndex"], 16); inp = (t.get("input") or "0x").lower(); frm = t["from"].lower(); to = (t.get("to") or "").lower()
            touch = set()
            if pid[2:] in inp: touch.add("pid_in_input")
            if tok[2:] in inp: touch.add("token_in_input")
            if buyer[2:] in inp and frm != buyer: touch.add("buyer_in_input")
            for l in tlog.get(t["hash"], []):
                touch.add("token_log:" + ("Transfer" if l["t"][0] == T_TRANSFER else "Approval" if l["t"][0] == T_APPROVAL else l["t"][0][:10]))
                if any(buyer[2:] in x.lower() for x in l["t"][1:]) and frm != buyer: touch.add("buyer_in_log:" + tok[:10])
            for (q, line, kind) in evtx.get(t["hash"], []):
                if q == pid: touch.add("pool_log:" + kind)
                else: touch.add("otherline_" + line + ":" + kind)
            d = p["Tbn"] - bn
            pos = "T" if t["hash"] == p["Ttx"] else ("before" if (bn < p["Tbn"] or (bn == p["Tbn"] and ti < p["Tti"])) else "after")
            rows.append(dict(L=p["L"], pid=p["pid"], d=d, off=bn - p["L"], bn=bn, ti=ti, pos=pos, hash=t["hash"], frm=frm, to=to, fc=cls_addr(frm, p), tc=cls_addr(to, p),
                             sel=inp[2:10], val=int(t["value"], 16), nonce=int(t["nonce"], 16), touch=sorted(touch), clen=(len(inp) - 2) // 2,
                             prio=int(t["maxPriorityFeePerGas"], 16) if t.get("maxPriorityFeePerGas") else None))
    have = sum(1 for bn in range(p["L"] + 1, p["Tbn"] + 4) if str(bn) in kb.d)
    facts.append(dict(L=p["L"], pid=p["pid"], regime=p["regime"], T=p["T"], Tbn=p["Tbn"], buyer=buyer, Tq=p["Tq"], launcher=p["launcher"],
                      have_blocks=have, need_blocks=p["Tbn"] + 3 - p["L"], near_ok=all(str(bn) in kb.d for bn in range(max(p["L"] + 1, p["Tbn"] - 12), p["Tbn"] + 4))))
pickle.dump({"rows": rows, "facts": facts, "botw": dict(botw), "pullers": dict(pullers)}, open("events.pkl", "wb"))
print("pools", len(P), "rows", len(rows), "complete pools", sum(1 for f in facts if f["have_blocks"] == f["need_blocks"]),
      "near_ok", sum(1 for f in facts if f["near_ok"]), "by regime", collections.Counter(f["regime"] for f in facts if f["near_ok"]))
