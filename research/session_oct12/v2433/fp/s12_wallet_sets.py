"""Do the 2.4333 line's wallets show up in the 3.0 / 5.0 lines after it stopped? Wallet sets per line, before and after 02:06 UTC Oct 12:
the launch senders (s03), the supply fan-out recipients of the token deployments (s11), and the bot router's buy recipients (s06: router -> wallet)."""
import json, collections, time
from clusters import load
from common import load_jsonl, BOT
rows = load(); vb = {r["c1"]: r for r in rows if r["fam"].startswith("VB ")}
STOP = max(r["t"] for r in rows if r["fam"].startswith("VB 2.4333"))
fam = lambda r: r["fam"].split(" (")[0]
dep = load_jsonl("s11_deploy_cache.jsonl")
sets = collections.defaultdict(set)
for r in rows:
    if r["fam"].startswith("VB "): sets[(fam(r), "launcher", r["t"] > STOP)].add(r["from"])
for d in dep:
    r = vb.get(d["token"])
    if r: sets[(fam(r), "fan-out", r["t"] > STOP)].update(d["recipients"])
for x in load_jsonl("s06_bot_transfers_cache.jsonl"):
    if x["side"] != "from": continue
    r = vb.get(x["token"])
    if r: sets[(fam(r), "buyer", r["t"] > STOP)].add("0x" + x["t2"][-40:])
print("cutoff (last 2.4333 launch):", time.strftime("%m-%d %H:%M:%S", time.gmtime(STOP)))
for k in sorted(sets): print("%-10s %-9s %-6s %6d wallets" % (k[0], k[1], "after" if k[2] else "before", len(sets[k])))
A = set().union(*[sets[k] for k in sets if k[0] == "VB 2.4333"])
for k in sorted(sets):
    if k[0] != "VB 2.4333": print("2.4333 wallets (all kinds) in %-8s %-9s %-6s: %5d of %5d" % (k[0], k[1], "after" if k[2] else "before", len(A & sets[k]), len(sets[k])))
for kind in ("launcher", "fan-out", "buyer"):
    a = sets[("VB 2.4333", kind, False)]
    print("2.4333 %-9s (%5d): in 3.0 before %5d, 3.0 after %5d, 5.0 before %5d, 5.0 after %5d" % (kind, len(a), len(a & set().union(*[sets[k] for k in sets if k[0] == "VB 3.0" and not k[2]])),
          len(a & set().union(*[sets[k] for k in sets if k[0] == "VB 3.0" and k[2]])), len(a & set().union(*[sets[k] for k in sets if k[0] == "VB 5.0" and not k[2]])), len(a & set().union(*[sets[k] for k in sets if k[0] == "VB 5.0" and k[2]]))))
