"""Pre-fire rule with no 60-block limit: any non-fingerprint, non-us, non-dust buy of >= 0.0001 ETH (or value 0, size unknown to the feed)
from launch to the trigger. How many of the 88 triggers would it skip, and what happened on them?"""
import sys, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
from load_all import *
pools, head = load_all(); cw = annotate(pools)
n = 0
for p in pools:
    if p["kind"] != "orig": continue
    rb = [x for x in p["sw"] if x["a0"] <= -REAL and before_pull(p, x) and x["cls"] != "us"]
    if any(x["bn"] - p["b0"] < 6 for x in rb): continue
    t = next((x for x in rb if 6 <= x["bn"] - p["b0"] <= 150), None)
    if not t: continue
    n += 1
    pre = [x for x in p["sw"] if x["a0"] < 0 and x["cls"] in ("outsider", "?") and (x["bn"], x["li"]) < (t["bn"], t["li"]) and ((x["value"] or 0) >= 1e14 or not x["value"])]
    if pre:
        pb = p["pull"]["bn"] if p["pull"] else None
        print(utc(p["ts"]), p["pid"][:10], "T +%d" % (t["bn"] - p["b0"]), [(x["bn"] - t["bn"], x["from"][:10], round(-x["a0"]/1e18, 6), round((x["value"] or 0)/1e18, 6)) for x in pre], "pull T+", (pb - t["bn"]) if pb else None)
print("triggers", n)
