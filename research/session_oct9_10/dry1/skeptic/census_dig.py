import sys, os, pickle, json, collections, datetime
SCR = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"; sys.path.insert(0, SCR)
from chain import T_SWAP, T_ML, W, sgn
HERE = os.path.dirname(os.path.abspath(__file__))
C = pickle.load(open(os.path.join(HERE, "census_s.pkl"), "rb")); D = pickle.load(open(os.path.join(HERE, "data_s.pkl"), "rb"))
rows = json.load(open(os.path.join(HERE, "census_s.json")))
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
txs = dict(C["txs"]); txs.update(D["txs"])
by = collections.defaultdict(list)
for l in C["plogs"] + D["logs"]: by[l["topics"][1]].append(l)
def s128(v):
    v = sgn(v); return v - (1 << 128) if v >= (1 << 127) else v
# approximate time: window start block 84855917 = 08:24:24; 0.1035 s/block
t_of = lambda b: (datetime.datetime(2026, 10, 10, 8, 24, 24) + datetime.timedelta(seconds=(b - 84855917) * 0.1035)).strftime("%m-%d %H:%M")
def timeline(pid, b0, upto):
    out = []; seen = set()
    for l in sorted(by[pid], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
        k = (l["transactionHash"], l["logIndex"])
        if k in seen: continue
        seen.add(k); bn = int(l["blockNumber"], 16)
        if bn - b0 > upto: break
        t = txs.get(l["transactionHash"])
        who = (t["from"][:10] + " via " + (t["to"] or "")[:10] + " " + t["input"][:10]) if t else "?"
        if l["topics"][0] == T_ML: out.append((bn - b0, "ML", sgn(W(l["data"], 2)) / 1e18, who))
        else:
            a0 = s128(W(l["data"], 0)); out.append((bn - b0, "BUY" if a0 < 0 else "SELL", abs(a0) / 1e18, who))
    return out
early = [r for r in rows if r["pull"] is not None and r["bot"] is not None and r["pull"] - r["bot"] <= 15]
for r in early:
    print(r["pid"][:10], r["b0"], t_of(r["b0"]), "bot +", r["bot"], "pull +", r["pull"])
    for e in timeline(r["pid"], r["b0"], r["pull"]): print("     ", e)
# regimes by hour
print("\nby hour: n launches, median gap, median pull offset, n pull<=30, n pull-bot<=15")
H = collections.defaultdict(list)
for i, r in enumerate(rows): H[t_of(r["b0"])[:-3]].append((i, r))
for h, lst in sorted(H.items()):
    pls = sorted(r["pull"] for _, r in lst if r["pull"] is not None)
    gaps = sorted(rows[i + 1]["b0"] - r["b0"] for i, r in lst if i + 1 < len(rows))
    print(h, len(lst), "gap med", gaps[len(gaps) // 2] if gaps else None, "pull med", pls[len(pls) // 2] if pls else None, "pull<=30", sum(1 for v in pls if v <= 30), "pull-bot<=15", sum(1 for _, r in lst if r["pull"] is not None and r["bot"] is not None and r["pull"] - r["bot"] <= 15))
