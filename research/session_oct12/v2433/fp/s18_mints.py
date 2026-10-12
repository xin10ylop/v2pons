"""Every token mint (ERC20/721 Transfer from 0x0) in the window, kept only for tokens launched in the window (s03); per mint recipient, the
code hash (a contract like the bot router 0x1cbaf24d receives each of its tokens' 1B supply) - to look for a new router with the bot router's code."""
import json, collections, time
from clusters import load
from common import R, T_TRANSFER, BOT, keccak, p, load_jsonl, append_jsonl
E = "0x" + "0" * 40
meta = json.load(open(p("s01_meta.json")))
rows = load(); launched = {}
for r in rows:
    for c in (r["c0"], r["c1"]):
        if c != E: launched.setdefault(c, r)
try: done = json.load(open(p("s18_meta.json")))
except Exception: done = {"to": meta["start"] - 1}
for a in range(done["to"] + 1, meta["head"] + 1, 20000):
    b = min(a + 19999, meta["head"])
    ls = R.logs({"topics": [T_TRANSFER, "0x" + "0" * 64]}, a, b)
    keep = [{"b": int(l["blockNumber"], 16), "h": l["transactionHash"], "token": l["address"].lower(), "to": "0x" + l["topics"][2][-40:], "d": l["data"]} for l in ls if len(l["topics"]) == 3 and l["address"].lower() in launched]
    append_jsonl("s18_mints_cache.jsonl", keep); done["to"] = b; json.dump(done, open(p("s18_meta.json"), "w"))
print("mints kept", len(load_jsonl("s18_mints_cache.jsonl")), R.STATS)
ms = load_jsonl("s18_mints_cache.jsonl")
by = collections.defaultdict(list)
for m in ms: by[m["to"]].append(m)
rec = sorted(by, key=lambda k: -len(by[k]))
codes = R.batch("eth_getCode", [[a, "latest"] for a in rec[:400]], n=20)
bot_hash = keccak(bytes.fromhex(R.call("eth_getCode", [BOT, "latest"])[2:])).hex()
print("bot router code hash", bot_hash)
print("mint recipients (top 40 by tokens) with code size/hash, the clusters of the tokens:")
same = []
for a, c in zip(rec[:400], codes):
    h = keccak(bytes.fromhex(c[2:])).hex() if c and c != "0x" else "EOA"
    if h == bot_hash: same.append(a)
    if rec.index(a) < 40:
        fams = collections.Counter(launched[m["token"]]["fam"].split(" (")[0][:40] for m in by[a])
        print("  %s %5d mints  code %s %s  %s" % (a, len(by[a]), (len(c) - 2) // 2 if c else 0, h[:12], dict(fams.most_common(3))))
print("recipients with the bot router's code hash:", same)
