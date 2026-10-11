"""Funding of the operator's fresh wallets, measured live (the public node keeps state for only the last ~6,000 blocks, ~10 min).
For the 2.433 and 3.0 launches of the last WINDOW blocks: the launch wallet and every fresh (nonce 0/1) wallet buying ahead of the bot's buy.
For each: binary-search the block where its ETH balance went from 0 to > 0 within the state window, then read that block's transactions
and name the one that pays it (to = wallet, or the wallet's address in the calldata: a batch payout). Appends to x07_funding.jsonl."""
import sys, json, time
from rpc import call, batch, logs, STATS
from xcommon import *
WINDOW = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
head = int(call("eth_blockNumber", []), 16) - 15
def bal(w, b):
    try: return int(call("eth_getBalance", [w, hex(b)]), 16)
    except RuntimeError as e:
        if "historical state" in str(e): return None
        raise
# the oldest block with state: probe downward
lo_ok = head - 5500
while bal(OURS, lo_ok) is None: lo_ok += 500
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, head - WINDOW, head)
L = []
for l in inits:
    d = l["data"]
    if W(d, 2) == 0 and W(d, 3) in SP: L.append((l, SP[W(d, 3)]))
txs = batch("eth_getTransactionByHash", [[l["transactionHash"]] for l, _ in L], 20)
subjects = []
for (l, line), t in zip(L, txs):
    if not t or (t.get("to") or "").lower() != POSM: continue
    lb = int(l["blockNumber"], 16); pid = l["topics"][1]
    subjects.append({"kind": "launcher", "line": line, "w": t["from"].lower(), "first": lb, "pid": pid, "nonce": int(t["nonce"], 16)})
    sw = logs({"address": PM, "topics": [T_SWAP, pid]}, lb, min(head, lb + 80))
    stx = batch("eth_getTransactionByHash", [[s["transactionHash"]] for s in sw], 20)
    for s, st_ in zip(sw, stx):
        if not st_: continue
        a0 = sgn(W(s["data"], 0)); a0 = a0 - (1 << 128) if a0 >= (1 << 127) else a0
        if a0 < 0 and (st_.get("to") or "").lower() != BOT and int(st_["nonce"], 16) <= 1:
            subjects.append({"kind": "fresh_buyer", "line": line, "w": st_["from"].lower(), "first": int(s["blockNumber"], 16), "pid": pid, "nonce": int(st_["nonce"], 16),
                             "q": -a0 / 1e18, "off": int(s["blockNumber"], 16) - lb, "to": (st_.get("to") or "").lower()})
print(f"head {head}, state from {lo_ok}; {len(L)} line launches in the last {WINDOW} blocks; subjects {len(subjects)}", flush=True)
out = open("x07_funding.jsonl", "a")
for s in subjects:
    w = s["w"]; hi = s["first"]
    b_lo = bal(w, lo_ok)
    rec = dict(s, state_from=lo_ok, head=head)
    if b_lo is None: rec["result"] = "no state"; out.write(json.dumps(rec) + "\n"); continue
    if b_lo > 0:
        rec["result"] = f"funded before the state window (>= {hi - lo_ok} blocks before its first act)"; rec["bal_at_lo"] = b_lo / 1e18
    else:
        a, b = lo_ok, hi       # bal(a) == 0, bal(b) > 0 (it acted at b)
        while b - a > 1:
            m = (a + b) // 2; v = bal(w, m)
            if v is None: a = m; continue
            if v > 0: b = m
            else: a = m
        blk = call("eth_getBlockByNumber", [hex(b), True])
        cand = [t for t in blk["transactions"] if (t.get("to") or "").lower() == w or w[2:] in (t.get("input") or "").lower()]
        rec["funded_block"] = b; rec["blocks_before_first_act"] = hi - b; rec["bal_after"] = bal(w, b) / 1e18
        rec["funding_txs"] = [{"from": t["from"].lower(), "to": (t.get("to") or "").lower(), "value": int(t["value"], 16) / 1e18, "sel": t["input"][:10], "len": (len(t["input"]) - 2) // 2,
                               "nonce": int(t["nonce"], 16), "hash": t["hash"]} for t in cand]
        if not cand: rec["block_txs"] = [{"from": t["from"].lower(), "to": (t.get("to") or "").lower(), "value": int(t["value"], 16) / 1e18, "sel": t["input"][:10]} for t in blk["transactions"]]
        rec["result"] = "found"
    out.write(json.dumps(rec) + "\n"); out.flush()
    print(json.dumps({k: rec.get(k) for k in ("kind", "line", "w", "q", "off", "result", "blocks_before_first_act", "bal_after", "funding_txs")})[:400], flush=True)
print("posts", STATS)
