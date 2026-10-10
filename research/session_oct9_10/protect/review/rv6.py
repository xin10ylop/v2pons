"""If the feed treated ANY non-fingerprint, non-us swap tx naming the token (value 0 included, buys or sells, any size) as an outsider:
how often would the pre-fire (T-60..T-1) and in-window (T..T+4) rules fire on the 88 triggers? And the size-thresholded version
with value-0 buys counted (their size is unknown to the feed)."""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
from load_all import *
pools, head = load_all(); cw = annotate(pools)
TR = []
for p in pools:
    if p["kind"] != "orig": continue
    rb = [x for x in p["sw"] if x["a0"] <= -REAL and before_pull(p, x) and x["cls"] != "us"]
    if any(x["bn"] - p["b0"] < 6 for x in rb): continue
    t = next((x for x in rb if 6 <= x["bn"] - p["b0"] <= 150), None)
    if t: TR.append((p, t))
print("triggers", len(TR))
def nonfp(x): return not is_us(x) and x["from"] not in cw and x["from"] != DUST
res = collections.Counter(); ex = collections.defaultdict(list)
for p, t in TR:
    T = t["bn"]
    pre = [x for x in p["sw"] if nonfp(x) and T - 60 <= x["bn"] < T]
    win = [x for x in p["sw"] if nonfp(x) and T <= x["bn"] <= T + 4 and (x["bn"], x["li"]) > (t["bn"], t["li"])]
    # value-0 or value>=0.0001: what a feed rule would flag (size unknown for value 0)
    flag = lambda x: (not x["value"]) or x["value"] >= 1e14
    for name, xs in (("pre_any", pre), ("win_any", win), ("pre_flag", [x for x in pre if flag(x)]), ("win_flag", [x for x in win if flag(x)])):
        if xs:
            res[name] += 1; ex[name].append((utc(p["ts"]), p["pid"][:10], [(x["bn"] - T, x["from"][:10], round(-x["a0"] / 1e18, 6), round((x["value"] or 0) / 1e18, 6)) for x in xs][:4]))
print(dict(res))
for k in ("pre_flag", "win_flag"):
    print(k); [print("   ", e) for e in ex[k]]
