# Recount from f8_fresh.json rows: v3.0 launches from the fronter's first pool on, pools with/without it, pull minus bot.
import json, collections, sys
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
W = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/report/work"
d = json.load(open(W + "/f8_fresh.json"))["rows"]
dec = json.load(open(W + "/decoy3.json")); fpids = {r["pid"] for r in dec}
rows = d["v3.0"]; first = 85469936
since = [r for r in rows if r["b0"] >= first]
withF = [r for r in rows if r["pid"][:10] in fpids]
print("v3.0 rows", len(rows), "since fronter's first pool", len(since), "with fronter", len(withF), "with fronter since", sum(1 for r in since if r["pid"][:10] in fpids))
after = d["v3.0 after 19:28"]
noF = [r for r in after if r["pid"][:10] not in fpids and r["pull_off"] is not None and r["bot_off"] is not None]
print("after 19:28 without fronter, pulled:", len(noF), "min pull-bot", min(r["pull_off"] - r["bot_off"] for r in noF))
print("n after 19:28", len(after), "head b0 max", max(r["b0"] for r in rows))
v = [r["ret"] for r in withF if r.get("ret") is not None]; import statistics as st
print("fronter pools replay n", len(v), "mean %.4f median %.4f pos %d" % (st.mean(v), st.median(v), sum(1 for a in v if a > 0)))
