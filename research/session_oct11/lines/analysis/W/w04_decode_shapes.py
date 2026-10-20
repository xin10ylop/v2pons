"""print the full calldata, word by word, of one tx per shape, with the receipt's logs summary (Transfer/Deposit/Withdrawal/Swap)"""
import json
from eth_utils import keccak
D = json.load(open("w03_txs.json")); P = json.load(open("w02_pick.json"))
TOP = {keccak(text=s).hex(): s.split("(")[0] for s in ("Transfer(address,address,uint256)", "Deposit(address,uint256)", "Withdrawal(address,uint256)",
       "Swap(address,address,int256,int256,uint160,uint128,int24)", "Approval(address,address,uint256)")}
import sys
only = sys.argv[1:] or None
for k, v in P:
    if only and not any(o in json.dumps(k) for o in only): continue
    x = v[0]; t = D["txs"][x["hash"]]; rc = D["receipts"].get(x["hash"])
    inp = t["input"]; b = inp[10:]
    print(f"\n=== {k}  tx {x['hash']}  pool {x['pool']} token {x['token']} qs {x['qs']} dq {x['dq']} dt {x['dt']}  value {int(t['value'],16)} gas {int(t['gas'],16)} from {t['from']} nonce {int(t['nonce'],16)} type {t['type']}")
    print("   sel", inp[2:10], "len", (len(inp) - 2) // 2)
    for i in range(0, len(b), 64): print(f"    w{i//64:02d} {b[i:i+64]}")
    if rc:
        print("   receipt status", rc["status"], "gasUsed", int(rc["gasUsed"], 16), "eff gp", int(rc["effectiveGasPrice"], 16), "L1?", rc.get("gasUsedForL1"))
        for l in rc["logs"]:
            tp = l["topics"][0][2:] if l["topics"] else ""
            print("    log", l["address"], TOP.get(tp, tp[:8]), [x[-40:] for x in l["topics"][1:]], l["data"][:2+64*2])
