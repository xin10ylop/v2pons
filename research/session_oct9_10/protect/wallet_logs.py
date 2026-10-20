"""Every ERC-20 Transfer to / from a wallet and every Approval by it (all contracts), Oct 8 00:00 -> head; which of those tokens
are the operator's launch tokens. Usage: wallet_logs.py w1 w2 ... -> wallet_logs_<w1[:8]>.json"""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
from chain import *
from load import load
HERE = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect/"
T_TR = "0x" + keccak(text="Transfer(address,address,uint256)").hex(); T_AP = "0x" + keccak(text="Approval(address,address,uint256)").hex()
START = 82878144 - 2_000_000          # ~2.4 days before Oct 8
head = int(rpc("eth_blockNumber", []), 16)
op_tokens = {"0x" + p["m"]["token"] for p in load()}
# all ETH-pool launch tokens of Oct 8 / Oct 9 (any launcher)
allp = json.load(open(HERE + "../oct8_pools.json"))["pools"] + json.load(open(HERE + "oct9_pools.json"))["pools"]
out = {}
for w in sys.argv[1:]:
    w = w.lower(); tw = "0x" + "0" * 24 + w[2:]
    tin = logs({"topics": [T_TR, None, tw]}, START, head); tout = logs({"topics": [T_TR, tw]}, START, head); ap = logs({"topics": [T_AP, tw]}, START, head)
    toks_in = collections.Counter(l["address"].lower() for l in tin); toks_out = collections.Counter(l["address"].lower() for l in tout)
    first = min([int(l["blockNumber"], 16) for l in tin + tout + ap] or [None])
    r = {"transfers_in": len(tin), "transfers_out": len(tout), "approvals": len(ap), "tokens_in": len(toks_in), "tokens_in_operator": sum(1 for t in toks_in if t in op_tokens),
         "tokens_out": len(toks_out), "first_log_block": first, "non_operator_tokens": [t for t in toks_in if t not in op_tokens][:20],
         "approval_spenders": collections.Counter("0x" + l["topics"][2][-40:] for l in ap).most_common(5)}
    out[w] = r
    print(w, json.dumps(r), flush=True)
json.dump(out, open(HERE + "wallet_logs_" + sys.argv[1][2:10] + ".json", "w"), indent=1)
