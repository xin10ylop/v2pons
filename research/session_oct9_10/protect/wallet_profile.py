"""A wallet's on-chain profile from logs (no archive state on this RPC): every ERC-20 Transfer to/from it and every Approval by it
since START; the transactions behind them (the ones it sent give their nonces); nonce coverage; what each tx was (operator-pool buy /
sell / Permit2 approval / other); the earliest tx found. Usage: wallet_profile.py w ... -> profile_<w[:10]>.json"""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
from chain import *
HERE = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect/"
T_TR = "0x" + keccak(text="Transfer(address,address,uint256)").hex(); T_AP = "0x" + keccak(text="Approval(address,address,uint256)").hex()
START = int(sys.argv[1]) if sys.argv[1].isdigit() else 80_500_000
ws = [a for a in sys.argv[1:] if a.startswith("0x")]
head = int(rpc("eth_blockNumber", []), 16)
P9 = json.load(open(HERE + "oct9_pools.json"))["pools"]; P8 = json.load(open(HERE + "../oct8_pools.json"))["pools"]
for w in ws:
    w = w.lower(); tw = "0x" + "0" * 24 + w[2:]
    L = logs({"topics": [T_TR, None, tw]}, START, head) + logs({"topics": [T_TR, tw]}, START, head) + logs({"topics": [T_AP, tw]}, START, head) + \
        logs({"address": PM, "topics": [T_SWAP]}, head - 1, head)[:0]
    hs = sorted({l["transactionHash"] for l in L})
    txs = {h: t for h, t in zip(hs, batch([("eth_getTransactionByHash", [h]) for h in hs])) if t}
    mine = {int(t["nonce"], 16): t for t in txs.values() if t["from"].lower() == w}
    kinds = collections.Counter()
    for t in mine.values():
        sel = t["input"][:10]
        kinds[(t["to"].lower()[:10], sel, "value>0" if int(t["value"], 16) else "value0")] += 1
    ns = sorted(mine)
    first = mine[ns[0]] if ns else None
    others = [t for t in txs.values() if t["from"].lower() != w]
    prof = {"wallet": w, "logs": len(L), "txs_sent_seen": len(mine), "nonce_min": ns[0] if ns else None, "nonce_max": ns[-1] if ns else None,
            "coverage": round(len(ns) / (ns[-1] - ns[0] + 1), 3) if ns else None,
            "first_seen_block": int(first["blockNumber"], 16) if first else None, "first_seen_nonce": ns[0] if ns else None,
            "sent_kinds": [(list(k), n) for k, n in kinds.most_common(12)],
            "txs_by_others_touching_it": [(t["from"], t["to"], t["input"][:10], int(t["blockNumber"], 16)) for t in others][:15]}
    json.dump({"profile": prof, "nonces": {n: [int(t["blockNumber"], 16), t["to"], t["input"][:10], int(t["value"], 16)] for n, t in mine.items()}}, open(HERE + "profile_" + w[:10] + ".json", "w"))
    print(json.dumps(prof), flush=True)
