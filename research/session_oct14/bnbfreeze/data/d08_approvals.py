"""d08: every non-Transfer log of the launcher's tokens (launch to head 127552369). The freeze of our wallet is a call approve(OUR_WALLET,
MAX) sent to the token by 0xbd418ce6 at L+70; its log is NOT the ERC-20 Approval (topic0 0x8c5be1e5...c925) but a look-alike with the same
first four bytes, 0x8c5be1e5ebec7d5bd14f714f4f5ec7c46ab3db174da78c3f62f10b71e9aeeaa0, topics (caller, target), data = the target.
-> cache/d08_tokenlogs_cache.jsonl [blk, txi, li, tx, token, topic0, topic1, topic2, data]; d08_approvals.out"""
import json, os, sys, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from common import *; import rpc
TT = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
APPROVAL = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0315f7c71b4e5d5ab7a9ac4b00c925"; FREEZE = "0x8c5be1e5ebec7d5bd14f714f4f5ec7c46ab3db174da78c3f62f10b71e9aeeaa0"
LS = launches(); head = 127552369; FROM = min(o["L"] for o in LS); STEP = 10000; G = 150
fn = os.path.join(CACHE, "d08_tokenlogs_cache.jsonl")
if not os.path.exists(fn):
    f = open(fn, "w"); x = FROM; n = 0
    while x <= head:
        e = min(head, x + STEP - 1); toks = sorted(o["token"] for o in LS if o["L"] <= e)
        for i in range(0, len(toks), G):
            for lg in rpc.logs({"address": toks[i:i + G]}, x, e, step=STEP):
                if lg["topics"] and lg["topics"][0] == TT: continue
                tp = lg["topics"] + [None] * 3
                f.write(json.dumps([int(lg["blockNumber"], 16), int(lg["transactionIndex"], 16), int(lg["logIndex"], 16), lg["transactionHash"], lg["address"].lower(),
                                    tp[0], tp[1] and "0x" + tp[1][-40:], tp[2] and "0x" + tp[2][-40:], lg["data"]]) + "\n"); n += 1
        x = e + 1
    f.close(); print("non-Transfer token logs", n)
A = [json.loads(l) for l in open(fn)]
print("non-Transfer token logs", len(A), "topic0:", C.Counter(a[5] for a in A).most_common(6))
F = [a for a in A if a[5] == FREEZE]
print("freeze-shaped logs", len(F), "callers", C.Counter(a[6] for a in F).most_common(5), "data == target", sum(1 for a in F if a[8][-40:] == a[7][2:]))
