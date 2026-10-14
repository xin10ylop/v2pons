"""Every token minted to the bot router (s03) mapped to its ETH-pair launch price: VB 3.0 / 5.0 / 2.433 per hour. Output: s03c_botmint_lines.out."""
from common import *
import collections
bm = [r for r in jl_load("s03_botmints_cache.jsonl") if "tok" in r]; bt = BT()
sq = {}
for l in jl_load("s01_v4init_cache.jsonl"):
    if l["t"][2][-40:] == "0" * 40: sq.setdefault("0x" + l["t"][3][-40:], (W(l["d"], 3), W(l["d"], 0), sgn(W(l["d"], 1))))
lab = {679394651928963067279918579724198: "3.0", 526364174002223567019744861584709: "5.0", SQRTP_2433: "2.433"}
tot = collections.Counter(); hr = collections.defaultdict(collections.Counter)
for r in bm:
    s = sq.get(r["tok"]); k = lab.get(s[0], "other %s" % (s,)) if s else "no ETH init"
    tot[k] += 1; hr[time.strftime("%d %H", time.gmtime(bt(r["b"])))][k] += 1
print("tokens minted to 0x1cbaf24d from Oct 12 00:00 to the head:", sum(tot.values()), dict(tot))
for h in sorted(hr): print(h, dict(hr[h]))
