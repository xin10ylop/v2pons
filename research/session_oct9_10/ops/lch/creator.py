"""Launcher 0x3194e326 = CREATE(0x3b11cafa..., nonce 0). Find that deploy tx and the creator's funding (scan backwards from the first launch)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bc
from trace import T
C = "0x3b11cafa6b570e3bc75bb6529b16dd35fe4b64b5"
found = []; fund = None
for bn, ts, t in bc.txs_desc(19367696 - 200000, 19367696):
    if t[1] == C or t[2] == C:
        found.append(T(bn, ts, t)); print(found[-1], flush=True)
        if t[2] == C and int(t[3]) > 0: fund = found[-1]; break
json.dump(found, open("creator_hist.json", "w"), indent=1)
if fund:
    f = fund["from"]; print("funder", f)
    for bn, ts, t in bc.txs_desc(fund["bn"] - 100000, fund["bn"] - 1):
        if t[2] == f and int(t[3]) > 0: print("funder funded by", T(bn, ts, t), flush=True); break
