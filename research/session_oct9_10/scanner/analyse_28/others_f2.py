"""F2: the swap senders that are not among the operator's known executors (all swaps to the head): their code (eth_getCode latest), cached."""
import sys, json, os, collections, hashlib
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from load import *
from chain import batch
HERE = os.path.dirname(os.path.abspath(__file__))
ids = json.load(open(os.path.join(HERE, "pids.json"))); P = load_pools(); T = load_txs(); E = load_events(set(ids["F2"]))
PW = json.load(open(os.path.join(HERE, "postwindow_logs.json")))
DEP = "0xdc7a139c58701faac4b1c0b209989f1230ae5489"
EXEC = set(P[x]["launch_to"] for x in ids["F2"])
for x in ids["F2"]:
    for s in E[x]["swaps"]:
        t = T.get(s["tx"])
        if t and t["from"] == DEP: EXEC.add(s["sender"])
senders = collections.Counter("0x" + l["topics"][2][-40:] for l in PW["swap_f2"])
others = [a for a in senders if a not in EXEC]
F = os.path.join(HERE, "others_f2.json")
C = json.load(open(F)) if os.path.exists(F) else {}
miss = [a for a in others if a not in C]
if miss: C.update(zip(miss, batch([("eth_getCode", [a, "latest"]) for a in miss]))); json.dump(C, open(F, "w"))
exec_code = None
for a in others:
    c = C[a]; print(a, senders[a], "code bytes", len(c) // 2 - 1, "same-as-executor" if "c798752b80049e7a67457af36822f85df37ddd74" in c else "", c[:60])
# within the 3000-block window: swaps by non-executor senders, and when
for x in ids["F2"]:
    for s in E[x]["swaps"]:
        if s["sender"] not in EXEC:
            print("in-window other:", x[:10], "+%d" % (s["bn"] - P[x]["launch_block"]), s["sender"][:10], "buy" if s["a0"] < 0 else "sell", -s["a0"] / 1e18)
