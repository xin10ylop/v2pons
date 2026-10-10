import sys, json, datetime, time
sys.path.insert(0, '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad')
sys.path.insert(0, '/home/user/v2pons/src')
from chain import *
import flip_engine
OUT = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/fp/"
SP = 1604517591721945638372359205383840
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
VAL = 2433328500000000000
A = 84540924
END = int(rpc("eth_blockNumber", []), 16)
flt = {"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}
allinit = []; chunks = []
b = A
while b <= END:
    e = min(b + 99999, END)
    L = logs(flt, b, e)
    chunks.append((b, e, len(L)))
    allinit += L
    print("chunk", b, e, len(L), flush=True)
    b = e + 1
# dedupe
seen = set(); u = []
for l in allinit:
    k = (l["transactionHash"], l["logIndex"])
    if k in seen: continue
    seen.add(k); u.append(l)
allinit = u
def rbatch(calls):
    res = [None] * len(calls)
    todo = list(range(len(calls)))
    for attempt in range(8):
        if not todo: break
        sub = [calls[i] for i in todo]
        try:
            r = batch(sub)
        except Exception as ex:
            print("batch err", ex, flush=True); time.sleep(3 * (attempt + 1)); continue
        nt = []
        for i, x in zip(todo, r):
            if x is None: nt.append(i)
            else: res[i] = x
        todo = nt
        if todo: time.sleep(2 * (attempt + 1))
    return res, todo
kept = []
for l in allinit:
    d = l["data"]; fee = W(d, 0); ts = sgn(W(d, 1)); hooks = W(d, 2); sp = W(d, 3)
    if (fee == 2500 and ts == 50) or sp == SP:
        kept.append(dict(block=int(l["blockNumber"], 16), tx=l["transactionHash"], logIndex=int(l["logIndex"], 16), pid=l["topics"][1],
                         currency1="0x" + l["topics"][3][-40:], ev_fee=fee, ev_ts=ts, ev_hooks=hex(hooks), ev_sqrt=str(sp)))
print("all ETH inits", len(allinit), "kept", len(kept), flush=True)
txs, miss_tx = rbatch([("eth_getTransactionByHash", [k["tx"]]) for k in kept])
blks = sorted(set(k["block"] for k in kept))
bh, miss_b = rbatch([("eth_getBlockByNumber", [hex(x), False]) for x in blks])
bts = {x: int(h["timestamp"], 16) for x, h in zip(blks, bh) if h}
print("missing tx", len(miss_tx), "missing blocks", len(miss_b), flush=True)
rows = []
for k, t in zip(kept, txs):
    k["ts"] = bts.get(k["block"])
    k["day"] = datetime.datetime.fromtimestamp(k["ts"], datetime.timezone.utc).strftime("%Y-%m-%d") if k["ts"] else None
    if t is None:
        k["tx_missing"] = True; k["family"] = None; rows.append(k); continue
    inp = bytes.fromhex(t["input"][2:])
    k.update(to=t["to"], frm=t["from"], value=str(int(t["value"], 16)), input_len=len(inp), selector=inp[:4].hex())
    dec = None
    if (t["to"] or "").lower() == POSM and len(inp) == 1444 and inp[:4].hex() == "ac9650d8":
        dec = flip_engine.decode_launch(inp)
        if dec: dec = {kk: (str(v) if isinstance(v, int) and abs(v) > 2**53 else v) for kk, v in dec.items()}
    k["dec"] = dec
    k["family"] = (t["to"] or "").lower() == POSM and int(t["value"], 16) == VAL and len(inp) == 1444 and inp[:4].hex() == "ac9650d8"
    rows.append(k)
with open(OUT + "oct10.jsonl", "w") as f:
    for r in rows: f.write(json.dumps(r) + "\n")
json.dump({"from": A, "to": END, "chunks": chunks, "n_all": len(allinit), "n_kept": len(kept), "miss_tx": len(miss_tx), "miss_blocks": len(miss_b)}, open(OUT + "oct10_meta.json", "w"))
print("done", END, flush=True)
