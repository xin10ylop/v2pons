import os, sys, json, time, base64, rlp
from eth_utils import keccak
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "replay_seat.jsonl")
if os.path.exists(LOG): os.remove(LOG)
os.environ.update({"DRY_RUN": "1", "LOG_PATH": LOG, "HALT_FILE": LOG + ".halt", "ENTRY": "seat", "LAUNCH_SELECTORS": "2fcb9108", "MAX_TRADES_PER_DAY": "100"})
sys.path.insert(0, "/home/user/v2pons/src")
import flip_engine as E
from chain import *
def hb(x): x = int(x, 16); return b"" if x == 0 else x.to_bytes((x.bit_length() + 7) // 8, "big")
def raw_of(t):
    if t["type"] == "0x2":
        al = [[bytes.fromhex(a["address"][2:]), [bytes.fromhex(k[2:]) for k in a["storageKeys"]]] for a in t.get("accessList", [])]
        raw = b"\x02" + rlp.encode([hb(t["chainId"]), hb(t["nonce"]), hb(t["maxPriorityFeePerGas"]), hb(t["maxFeePerGas"]), hb(t["gas"]), bytes.fromhex(t["to"][2:]) if t["to"] else b"",
                                    hb(t["value"]), bytes.fromhex(t["input"][2:]), al, hb(t.get("yParity", t["v"])), hb(t["r"]), hb(t["s"])])
    elif t["type"] == "0x0":
        raw = rlp.encode([hb(t["nonce"]), hb(t["gasPrice"]), hb(t["gas"]), bytes.fromhex(t["to"][2:]) if t["to"] else b"", hb(t["value"]), bytes.fromhex(t["input"][2:]), hb(t["v"]), hb(t["r"]), hb(t["s"])])
    else: return None
    assert "0x" + keccak(raw).hex() == t["hash"]; return raw
def frame(seq, raws):
    body = b"\x03" + b"".join((len(r) + 1).to_bytes(8, "big") + b"\x04" + r for r in raws)
    return json.dumps({"messages": [{"sequenceNumber": seq, "message": {"message": {"header": {"kind": 3, "timestamp": int(time.time())}, "l2Msg": base64.b64encode(body).decode()}}}]})
E.state["base_fee"] = 22_000_000
rows = json.load(open("newlaunch.json"))[1:]
for pid, b0 in rows[-10:]:
    blks = batch([("eth_getBlockByNumber", [hex(b), True]) for b in range(b0, b0 + 16)])
    tok = logs({"address": PM, "topics": [T_INIT, pid]}, b0, b0)[0]["topics"][3][-40:]
    for b in blks:
        bn = int(b["number"], 16)
        raws = [r for t in b["transactions"] if (t["input"][:10] == "0x2fcb9108" or tok in t["input"].lower()) for r in [raw_of(t)] if r]
        E.ingest(frame(bn, raws))
        if bn == b0:
            t0 = time.time()
            while pid not in E.state["armed"] and time.time() - t0 < 6: time.sleep(0.05)
    t0 = time.time()
    while E.state["position"] is not None and time.time() - t0 < 3: time.sleep(0.05)
    evs = [e for e in (json.loads(l) for l in open(LOG)) if e.get("pid") == pid]
    wf = [e for e in evs if e["ev"] == "would_fire"]; ws = [e for e in evs if e["ev"] == "would_sell"]; fb = [e for e in evs if e["ev"] == "first_buy"]
    print(f"launch {b0}: fire at +{wf[0]['trig_seq'] - b0 if wf else '-'}, planned landing +{wf[0]['plan_buy_seq'] - b0 if wf else '-'}, burst at +{fb[0]['offset'] if fb else '-'}; "
          + (f"would_sell {ws[0]['after_buy']} block(s) after our buy: {ws[0]['why'][:11]}, priced {ws[0]['tp_ret']}" if ws else str([e['ev'] + ':' + str(e.get('why', '')) for e in evs][-2:])))
