"""For every token first launched in the window (s03), its first mint in the window (s18) and that mint's recipient; the recipient's code hash
(EOA or contract) compared with the bot router's. Answers: does any other contract with the bot router's code mint launch tokens?"""
import json, collections, time
from clusters import load
from common import R, BOT, keccak, load_jsonl
E = "0x" + "0" * 40
rows = load(); first = {}
for r in rows:
    t = r["c1"] if r["c0"] == E else None
    if t and t not in first: first[t] = r
mints = load_jsonl("s18_mints_cache.jsonl"); fm = {}
for m in sorted(mints, key=lambda m: m["b"]):
    if m["token"] in first and m["token"] not in fm and m["b"] <= first[m["token"]]["b"]: fm[m["token"]] = m
recs = sorted({m["to"] for m in fm.values()})
print("ETH-pair tokens launched", len(first), "with a mint in the window before the launch", len(fm), "distinct first-mint recipients", len(recs))
codes = R.batch("eth_getCode", [[a, "latest"] for a in recs], n=20)
bot_hash = keccak(bytes.fromhex(R.call("eth_getCode", [BOT, "latest"])[2:])).hex()
ch = {a: ("EOA" if not c or c == "0x" else keccak(bytes.fromhex(c[2:])).hex()) for a, c in zip(recs, codes)}
same = [a for a in recs if ch[a] == bot_hash]
print("first-mint recipients with the bot router's code hash:", same)
g = collections.defaultdict(collections.Counter)
for t, m in fm.items(): g["EOA" if ch[m["to"]] == "EOA" else ("BOT ROUTER" if m["to"] == BOT else "contract " + m["to"][:10] + " " + ch[m["to"]][:8])][first[t]["fam"].split(" (")[0][:44]] += 1
for k in sorted(g, key=lambda k: -sum(g[k].values()))[:25]: print("  %-40s %5d  %s" % (k, sum(g[k].values()), dict(g[k].most_common(4))))
