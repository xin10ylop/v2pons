"""Stage 6c: with the receipts of blocks [T-4, T]: every log-level touch of the pool, its token or T's buyer wallet ahead of the bot's buy,
and the bot's own tx (status) - which logs are in the precursor window at all."""
import pickle, collections
from lib import *
E = pickle.load(open("events.pkl", "rb")); rows = E["rows"]; facts = {f["pid"]: f for f in E["facts"]}
kr = KV("rcp")
have = [k for k, f in facts.items() if all(str(f["Tbn"] - d) in kr.d for d in range(0, 5))]
print("pools with receipts for every block T-4..T:", len(have), "of", len(facts))
c = collections.Counter(); ex = []
for r in rows:
    if r["pid"] not in have or r["pos"] != "before" or not (0 <= r["d"] <= 4): continue
    t = [x for x in r["touch"] if x.startswith(("token", "pid", "pool_log", "buyer"))]
    if t: c[(r["d"], r["fc"], r["tc"], r["sel"], tuple(t))] += 1; ex.append((r["pid"][:12], r["d"], r["hash"][:14], r["fc"], r["tc"], r["sel"], t))
print("touches of the pool / token / T's buyer in d 0..4 ahead of the bot's buy:", sum(c.values()))
for k, v in c.most_common(20): print(" ", v, k)
for e in ex[:10]: print("   e.g.", e)
st_ = collections.Counter(r["status"] for r in rows if r["pos"] == "T" and r["pid"] in have)
print("status of the bot's T tx:", dict(st_))
oth = collections.Counter(x for r in rows if r["pid"] in have and r["pos"] == "before" and 0 <= r["d"] <= 4 for x in r["touch"] if x.startswith("otherline"))
print("events in other line pools (3.0 / 2.433) in d 0..4:", dict(oth))
fails = collections.Counter((r["fc"], r["tc"], r["sel"]) for r in rows if r["pid"] in have and r["pos"] == "before" and 0 <= r["d"] <= 4 and r["status"] == "0x0")
print("failed txs in d 0..4 (all pools):", sum(fails.values()), fails.most_common(8))
