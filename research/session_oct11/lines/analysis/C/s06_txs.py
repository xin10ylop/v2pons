"""Trimmed transactions for the studied pools' events and launch txs -> C/tx.pkl {hash: {from,to,sel,clen,value,nonce,prio,bn,ti,input?}}"""
import sys, os, pickle, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census"
E = pickle.load(open(os.path.join(OUT, "ev.pkl"), "rb")); R = load_rows()
want = set()
for p, o in E.items():
    for e in o["ev"]: want.add(e[-1])
    want.add(R[p]["launch_tx"])
out = {}
for n in ("tx_launch.jsonl", "tx_swap.jsonl", "tx_swap_b.jsonl"):
    with open(os.path.join(CEN, "cache", n)) as f:
        for line in f:
            try: x = json.loads(line)
            except Exception: continue
            if x["hash"] in want:
                out[x["hash"]] = {k: x.get(k) for k in ("from", "to", "selector", "calldata_len", "value_wei", "nonce", "max_prio", "gas_price", "bn", "ti", "input", "input_head", "gas", "type")}
print("wanted", len(want), "found", len(out))
pickle.dump(out, open(os.path.join(OUT, "tx.pkl"), "wb"))
