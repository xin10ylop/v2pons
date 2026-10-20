import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import T_SWAP, T_ML, W, sgn
D = json.load(open("react_data.json"))
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"; WALLET = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
cnt_first = collections.Counter(); cnt_any = collections.Counter(); per = collections.defaultdict(set); senders = collections.Counter(); tos = collections.Counter()
for pid, P in D["pools"].items():
    m = P["meta"]; b0 = m["block"]
    sw = [e for e in P["ev"] if e["t0"] == T_SWAP]
    pull = min([e["bn"] for e in P["ev"] if e["t0"] == T_ML and sgn(W(e["data"], 2)) < 0] or [10**12])
    for e in sw:
        a0 = s128(W(e["data"], 0)); t = P["txs"].get(e["tx"])
        if t is None: continue
        senders[e["sender"]] += 1; tos[t["to"]] += 1
        if a0 < 0 and e["bn"] < pull:
            per[t["from"]].add(pid)
    real = [e for e in sw if s128(W(e["data"], 0)) <= -2e14 and e["bn"] < pull]
    for e in real[:3]: cnt_first[P["txs"][e["tx"]]["from"]] += 1
print("swap senders", senders.most_common(8)); print("tx to", tos.most_common(8))
print("first-3 real buyers:", cnt_first.most_common(30))
print("buyers by launches:", sorted(((len(v), k) for k, v in per.items()), reverse=True)[:40])
print("deployers", collections.Counter(P["meta"]["from"] for P in D["pools"].values()))
