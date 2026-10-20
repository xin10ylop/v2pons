"""Replay the real blocks around the eight live trades through the release 0.3 engine in DRY_RUN, without our own transactions:
what would it have done?"""
import os, sys, json, time, base64, tempfile
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "replay.jsonl")
if os.path.exists(LOG): os.remove(LOG)
os.environ.update({"DRY_RUN": "1", "LOG_PATH": LOG, "ROUTE": "router", "HALT_FILE": LOG + ".halt"})
sys.path.insert(0, "/home/user/v2pons/src")
import rlp
from eth_utils import keccak
import flip_engine as E
from chain import *
WAL = "ab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
D = json.load(open("oct8.json")); pools = D["pools"]; ev = D["ev"]
LAUNCHES = [83341600, 83342087, 83342440, 83342632, 83343251, 83343560, 83344131, 83386507]
def hb(x): x = int(x, 16); return b"" if x == 0 else x.to_bytes((x.bit_length() + 7) // 8, "big")
def raw_of(t):
    if t["type"] == "0x2":
        al = [[bytes.fromhex(a["address"][2:]), [bytes.fromhex(k[2:]) for k in a["storageKeys"]]] for a in t.get("accessList", [])]
        body = [hb(t["chainId"]), hb(t["nonce"]), hb(t["maxPriorityFeePerGas"]), hb(t["maxFeePerGas"]), hb(t["gas"]), bytes.fromhex(t["to"][2:]) if t["to"] else b"",
                hb(t["value"]), bytes.fromhex(t["input"][2:]), al, hb(t.get("yParity", t["v"])), hb(t["r"]), hb(t["s"])]
        raw = b"\x02" + rlp.encode(body)
    elif t["type"] == "0x0":
        raw = rlp.encode([hb(t["nonce"]), hb(t["gasPrice"]), hb(t["gas"]), bytes.fromhex(t["to"][2:]) if t["to"] else b"", hb(t["value"]), bytes.fromhex(t["input"][2:]), hb(t["v"]), hb(t["r"]), hb(t["s"])])
    else:
        return None
    assert "0x" + keccak(raw).hex() == t["hash"], (t["type"], t["hash"])
    return raw
def frame(seq, raws):
    body = b"\x03" + b"".join((len(r) + 1).to_bytes(8, "big") + b"\x04" + r for r in raws)
    return json.dumps({"messages": [{"sequenceNumber": seq, "message": {"message": {"header": {"kind": 3, "timestamp": int(time.time())}, "l2Msg": base64.b64encode(body).decode()}}}]})
E.state["base_fee"] = 20_100_000
for b0 in LAUNCHES:
    pid = [k for k, p in pools.items() if p["bn"] == b0][0] if any(p["bn"] == b0 for p in pools.values()) else None
    if pid is None:
        il = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, b0, b0); pid = il[0]["topics"][1]; tok = il[0]["topics"][3][-40:]
    else:
        tok = pools[pid]["token"]
    ls = logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, b0, b0 + 12000)
    pull = min(int(l["blockNumber"], 16) for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0)
    blks = batch([("eth_getBlockByNumber", [hex(b), True]) for b in range(b0, b0 + 175)])
    for b in blks:
        bn = int(b["number"], 16); raws = []
        for t in b["transactions"]:
            if t["from"][2:].lower() == WAL: continue                                   # the pool without us
            if (t.get("to") or "")[2:].lower() == OP or tok in t["input"].lower():
                r = raw_of(t)
                if r: raws.append(r)
        E.ingest(frame(bn, raws))
        if bn == b0:
            t0 = time.time()
            while pid not in E.state["armed"] and time.time() - t0 < 6: time.sleep(0.05)
        if bn > b0 and E.state["armed"].get(pid, {}).get("first_buy") and bn > E.state["armed"][pid]["first_buy"] + 12: break
    t0 = time.time()
    while E.state["position"] is not None and time.time() - t0 < 3: time.sleep(0.05)
    evs = [json.loads(l) for l in open(LOG)]
    wf = [e for e in evs if e["ev"] == "would_fire" and e["pid"] == pid]; ws = [e for e in evs if e["ev"] == "would_sell" and e["pid"] == pid]
    if not wf: print(b0, "no fire", [e for e in evs if e.get("pid") == pid][-2:]); continue
    w, s = wf[-1], ws[-1]
    print(f"launch {b0}: trigger +{w['trig_seq'] - b0}, planned buy trig+2; would_sell at buy+{s['after_buy']} ({s['why'][:40]}, tp_ret {s['tp_ret']}), "
          f"lands buy+{s['after_buy'] + 1}..+{s['after_buy'] + 2}; the real pull at trig+{pull - w['trig_seq']} = planned buy+{pull - w['plan_buy_seq']}")
