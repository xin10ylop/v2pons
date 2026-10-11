#!/usr/bin/env python3
"""line_adapt: the 2.4333 line's launches in the same 24 h (Initialize with its sqrtP), for the one position slot -> data/v2433.json"""
import sys, os, json
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import logs, PM, T_INIT, W
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
w = json.load(open(os.path.join(D, "window.json"))); out = []
a = w["from_block"]
while a <= w["head"]:
    b = min(a + 99_999, w["head"])
    out += [int(l["blockNumber"], 16) for l in logs({"address": PM, "topics": [T_INIT]}, a, b) if W(l["data"], 3) == 1604517591721945638372359205383840]
    a = b + 1
json.dump(sorted(out), open(os.path.join(D, "v2433.json"), "w")); print(len(out))
