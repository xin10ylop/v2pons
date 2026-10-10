"""detail one launch: creator funding, buyers' funding + nonces, post-pull flows. usage: one.py <launch block or sender prefix> [pre] [post]"""
from B import *
X = launches(); R = json.load(open(D + "p1.json"))
arg = sys.argv[1]
x = next(v for v in X if (arg.isdigit() and v["bn"] == int(arg)) or v["h"].startswith(arg) or v["from"].startswith(arg))
r = R[x["h"]]; pre = int(sys.argv[2]) if len(sys.argv) > 2 else 1500; post_ = int(sys.argv[3]) if len(sys.argv) > 3 else 800
bn, P = x["bn"], r["pull"] or x["bn"] + 3000
SK = {PM, "0x" + "0" * 40, "0x3194e32622c5d860a0572c74edda99dcfd8fc827", "0x8876789976decbfcbbbe364623c63652db8c0904"}
buyers = []
for n, t, h in r["buys"]:
    if t not in SK and t != x["from"] and t not in buyers: buyers.append(t)
print(f"launch {bn} {utc(rows(bn, bn)[0][1])} creator {x['from']} n{x['nonce']} value {x['value']} pull {P} (+{P-bn}) buys {len(r['buys'])} buyers {len(buyers)} sells {len(r['sells'])}")
W_ = set(buyers) | {x["from"]}
rr = touching(W_, bn - pre, P + post_)
print("-- creator txs")
for q in rr:
    if x["from"] in (q[3], q[4]): print("  ", fmt(q, bn))
print("-- plain transfers into buyers (value>0, sel 0x) and buyers' first tx")
fund = collections.Counter(); first = {}
for q in rr:
    if q[4] in buyers and q[3] != x["from"] and int(q[5]) > 0: fund[q[3]] += 1
    if q[3] in buyers and q[3] not in first: first[q[3]] = q
for f, c in fund.most_common(10): print("   funder", f, "-> buyers", c)
print("   buyer first-tx nonces:", collections.Counter(q[6] for q in first.values()).most_common(8))
print("-- funders' txs")
for f, c in fund.most_common(3):
    for q in rr:
        if q[3] == f: print("  ", fmt(q, bn))
print("-- buyers' outflows after pull (value>0)")
oc = collections.Counter()
for q in rr:
    if q[3] in buyers and q[0] >= P and int(q[5]) > 0: oc[q[4]] += 1
print("  ", oc.most_common(5))
