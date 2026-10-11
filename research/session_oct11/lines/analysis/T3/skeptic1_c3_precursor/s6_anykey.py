"""Stage 6: is there ANY transaction type at a stable 1-4 block lead to T on the current-regime pools of my slice (cur, 04:22..09:38 UTC,
none used by the precursor finder)? Every tx in the whole blocks L+4..T (ahead of the bot's tx) gets keys: exact target+selector, selector,
exact sender, sender class (bot buyer wallet / line launcher / sentinel / ours / other), target class, what it touches (stage 4 kinds),
an event in another 3.0 line pool, a 1,444-byte PositionManager launch, a bot-router call, a pull (a0f7978d), a bot sell (UR 24856bc3).
Two tests per key:
  (a) the finder's: pools holding the key at d = 1..4 vs at d = 5..8 and 9..12 (same width);
  (b) a usable trigger: arm at L+A (A = 4 / 15 / 18), fire on the key's FIRST occurrence at block b >= L+A, lead = T - b.
      hit = lead in 1..4; early = lead > 4 (a front bought there is pulled before T: -100%); miss = never before T.
Keys with the most hits are listed; the finder's top keys (s6/s6b) are listed by name."""
import pickle, collections
from lib import *
E = pickle.load(open("touch.pkl", "rb")); rows = [r for r in E["rows"] if r["set"] == "cur"]
facts = {f["pid"]: f for f in E["facts"] if f["set"] == "cur" and f["have"] == f["need"]}
allp = []
for s in ("older", "old", "mid", "recent"):
    try: allp += pickle.load(open(f"parsed_{s}.pkl", "rb"))["pools"]
    except FileNotFoundError: pass
BOTW = set(); LAUN = set(); LINE_PID = set()
for p in allp:
    LAUN.add(p["launcher"]); LINE_PID.add(p["pid"].lower())
    for s in p["sw"]:
        if s["bot"]: BOTW.add(s["eoa"])
print(f"cur pools with the whole window: {len(facts)}; known bot buyer wallets {len(BOTW)}, line launchers {len(LAUN)}, line pools {len(LINE_PID)}")
kr = KV("rcp")
def cls(a):
    if a in BOTW: return "botwallet"
    if a in LAUN: return "launcher"
    if a == SENTINEL: return "sentinel"
    if a in (OURS, RELAY): return "ours"
    if a == BOT: return "BOTROUTER"
    if a == POSM: return "POSM"
    if a == UR: return "UR"
    if a == PERMIT2: return "PERMIT2"
    return "other"
# other-line-pool events per tx (from receipts)
oth = {}
for r in rows:
    pass
rc_logs = {}
def other_line(r):
    bn = r["L"] + r["off"]; rr = kr.d.get(str(bn)) or []
    for x in rr:
        if x["tx"] == r["hash"]:
            for l in x["logs"]:
                if l["a"] == PM and len(l["t"]) > 1 and l["t"][1].lower() in LINE_PID and l["t"][1].lower() != r["pid"].lower():
                    return {T_SWAP: "Swap", T_ML: "ML", T_INIT: "Init"}.get(l["t"][0], "x")
    return None
def keys(r):
    fc = cls(r["frm"]); tc = cls(r["to"])
    ks = [f"to+sel {r['to'][:10]}:{r['sel']}", f"sel {r['sel']}", f"from {r['frm'][:10]}", f"cls {fc}->{tc}:{r['sel']}", f"fromcls {fc}", f"tocls {tc}"]
    ks += [f"touch {x.split('_of_')[0]}" for x in r["touch"]]
    if r["val"] > 0 and r["sel"] == "": ks.append(f"eth-send {fc}->{tc}")
    if r["to"] == POSM and r["clen"] == 1444: ks.append("1444-byte PositionManager launch")
    if r["to"] == BOT and r["sel"] == "a0f7978d": ks.append("a bot pull (a0f7978d)")
    if r["to"] == UR and r["sel"] == "24856bc3" and fc == "botwallet": ks.append("a bot sell (UR 24856bc3)")
    if r["to"] == BOT and r["sel"] == "c1120e3d": ks.append("a bot buy (any pool)")
    if r["status"] == "0x0": ks.append(f"failed tx {r['to'][:10]}:{r['sel']}")
    ol = other_line(r)
    if ol: ks.append(f"event in another 3.0/2.433 line pool: {ol}"); ks.append("event in another line pool (any)")
    return ks
occ = collections.defaultdict(lambda: collections.defaultdict(set))   # key -> pid -> set of offsets
for r in rows:
    if r["pid"] not in facts or r["pos"] != "before" or r["off"] < 4: continue
    for k in keys(r): occ[k][r["pid"]].add(r["off"])
n = len(facts)
res = []
for k, pp in occ.items():
    w14 = sum(1 for pid, offs in pp.items() if any(1 <= facts[pid]["T"] - o <= 4 for o in offs))
    w58 = sum(1 for pid, offs in pp.items() if any(5 <= facts[pid]["T"] - o <= 8 for o in offs))
    w912 = sum(1 for pid, offs in pp.items() if any(9 <= facts[pid]["T"] - o <= 12 for o in offs))
    trig = {}
    for A in (4, 15, 18):
        hit = early = miss = 0; leads = []
        for pid, f in facts.items():
            offs = sorted(o for o in pp.get(pid, ()) if o >= A and o <= f["T"])
            offs = [o for o in offs if f["T"] - o >= 1]
            if not offs: miss += 1; continue
            lead = f["T"] - offs[0]; leads.append(lead)
            if lead <= 4: hit += 1
            else: early += 1
        trig[A] = (hit, early, miss, leads)
    res.append(dict(k=k, w14=w14, w58=w58, w912=w912, trig=trig))
print(f"\n(a) d 1..4 vs d 5..8 / 9..12, top 25 by the excess of d1-4 over the mean of the other two windows (n {n} pools)")
for c in sorted(res, key=lambda c: -(c["w14"] - (c["w58"] + c["w912"]) / 2))[:25]:
    print(f"  {c['k'][:62]:62s} d1-4 {c['w14']:3d}  d5-8 {c['w58']:3d}  d9-12 {c['w912']:3d}  excess {c['w14'] - (c['w58'] + c['w912']) / 2:+5.1f}")
for A in (4, 15, 18):
    print(f"\n(b) first occurrence at or after L+{A} as the trigger: top 15 keys by hits (lead 1..4); 'early' = fired > 4 blocks before T")
    for c in sorted(res, key=lambda c: (-c["trig"][A][0], c["trig"][A][1]))[:15]:
        h, e, m, leads = c["trig"][A]
        print(f"  {c['k'][:62]:62s} hit {h:3d} ({100*h/n:4.1f}%) early {e:3d} miss {m:3d} | lead p10/50/90 {pct(leads,.1)}/{pct(leads,.5)}/{pct(leads,.9)}")
print("\nbest precision (hit / (hit + early)) among keys firing in >= 10 pools, arm L+18:")
for c in sorted([c for c in res if c["trig"][18][0] + c["trig"][18][1] >= 10], key=lambda c: -c["trig"][18][0] / (c["trig"][18][0] + c["trig"][18][1]))[:12]:
    h, e, m, leads = c["trig"][18]
    print(f"  {c['k'][:62]:62s} hit {h:3d} early {e:3d} miss {m:3d} precision {h/(h+e):.2f} coverage {h/n:.2f}")
print("\nnamed keys (the finder's top keys and the candidate's own) - arm L+4 / L+18:")
NAMED = ["touch pool:pid_in_calldata", "touch token:in_calldata", "touch token:target", "touch token:log_Transfer", "touch token:log_Approval",
         "touch buyer:sender", "touch buyer:target", "touch buyer:target+eth", "touch buyer:in_calldata", "touch buyer:in_log", "touch token:in_log",
         "touch pool:log_Swap", "touch pool:log_ML", "event in another line pool (any)", "1444-byte PositionManager launch", "a bot buy (any pool)",
         "a bot pull (a0f7978d)", "a bot sell (UR 24856bc3)", "fromcls botwallet", "fromcls launcher", "fromcls sentinel", "tocls BOTROUTER", "tocls POSM",
         "tocls PERMIT2", "to+sel 0x00000000:fd9f1e10", "sel 095ea7b3", "sel a9059cbb", "eth-send other->other", "to+sel 0xccc88a9d:0a2b8f36"]
byk = {c["k"]: c for c in res}
for k in NAMED:
    c = byk.get(k)
    if not c: print(f"  {k:62s} never occurs in L+4..T"); continue
    print(f"  {k:62s} d1-4 {c['w14']:3d} d5-8 {c['w58']:3d} d9-12 {c['w912']:3d} | L+4: hit {c['trig'][4][0]:3d} early {c['trig'][4][1]:3d} miss {c['trig'][4][2]:3d} | "
          f"L+18: hit {c['trig'][18][0]:3d} early {c['trig'][18][1]:3d} miss {c['trig'][18][2]:3d}")
