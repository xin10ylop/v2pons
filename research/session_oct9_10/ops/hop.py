"""Funding of a wallet: scan back from block B for a value tx to it (or input naming it). Usage: hop.py w B [maxback]"""
import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops")
from lib import *
w = sys.argv[1].lower(); B = int(sys.argv[2]); mb = int(sys.argv[3]) if len(sys.argv) > 3 else 40000
h = scan(B - mb, B, lambda x, t: (x["to"] == w and x["value"] > 0) or (w[2:] in t["input"].lower() and x["from"] != w) or x["from"] == w, backwards=True,
         stop=lambda h: any(y["to"] == w and y["value"] > 0 for y in h))
for y in h: print(w[:10], "|", y["bn"], utc(y["ts"]), y["from"], "->", y["to"], round(y["value"], 6), y["sel"], "nonce", y["nonce"], y["hash"], flush=True)
if not h: print(w[:10], "| nothing in", B - mb, B)
