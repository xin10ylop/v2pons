"""Cross-check: the engine's own code (flip_engine 0.8, DRY_RUN=1, ENTRY=auto, LAUNCH_SELECTORS=2fcb9108) fed the real transactions of
L..L+15 of every Oct 8 copy launch (rebuilt from the chain, the launch call and every tx carrying the token), one frame per block.
Checks arming (entry, eligible, launcher code), the seat's fire block, the first real buy. The dry run's virtual buy sits at the
HEAD of fire+2 (optimistic), so its would_sell is not the paper's convention; only the decisions are compared."""
import os, sys, json, time, base64, pickle, rlp
from eth_utils import keccak
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
LOG = os.path.join(HERE, "seat_engine_replay.jsonl")
if os.path.exists(LOG): os.remove(LOG)
os.environ.update({"DRY_RUN": "1", "LOG_PATH": LOG, "HALT_FILE": LOG + ".halt", "ENTRY": "auto", "LAUNCH_SELECTORS": "2fcb9108", "MAX_TRADES_PER_DAY": "1000", "STAKE_ETH": "0.0012"})
sys.path.insert(0, "/home/user/v2pons/src")
import flip_engine as E
from chain import T_INIT
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
d = pickle.load(open(os.path.join(HERE, "cache_seat.pkl"), "rb"))
E.state["base_fee"] = 22_000_000; skipped_types = 0
out = []
for i, p in enumerate(d["copies"]):
    pid = p["pid"]; L = p["block"]; rec = d["rec"][i]
    tok = [l for l in rec["logs"] if l["topics"] and l["topics"][0] == T_INIT][0]["topics"][3][-40:]
    for b in d["blocks"][pid][:16]:
        bn = int(b["number"], 16); raws = []
        for t in sorted(b["transactions"], key=lambda t: int(t["transactionIndex"], 16)):
            if t["input"][:10] == "0x2fcb9108" or tok in t["input"].lower():
                r = raw_of(t)
                if r is None: skipped_types += 1
                else: raws.append(r)
        E.ingest(frame(bn, raws))
        if bn == L:
            t0 = time.time()
            while pid not in E.state["armed"] and time.time() - t0 < 10: time.sleep(0.05)
    t0 = time.time()
    while E.state["position"] is not None and time.time() - t0 < 3: time.sleep(0.05)
    evs = [e for e in (json.loads(l) for l in open(LOG)) if e.get("pid") == pid]
    arm = next((e for e in evs if e["ev"] == "armed"), {}); wf = next((e for e in evs if e["ev"] == "would_fire"), None); fb = next((e for e in evs if e["ev"] == "first_buy"), None)
    ws = next((e for e in evs if e["ev"] == "would_sell"), None); sk = [e.get("why") for e in evs if e["ev"] == "skip"]
    row = {"L": L, "entry": arm.get("entry"), "eligible": arm.get("eligible"), "launcher_code": arm.get("launcher_code"), "fire_offset": (wf["trig_seq"] - L) if wf else None,
           "first_buy_offset": fb["offset"] if fb else None, "would_sell_after_buy": ws["after_buy"] if ws else None, "skips": sk}
    out.append(row); print(row)
json.dump({"rows": out, "skipped_tx_types": skipped_types}, open(os.path.join(HERE, "seat_engine_replay.json"), "w"), indent=1)
import collections
print("fire offsets", collections.Counter(r["fire_offset"] for r in out), "entries", collections.Counter(r["entry"] for r in out), "eligible", collections.Counter(r["eligible"] for r in out),
      "codes", collections.Counter(r["launcher_code"] for r in out), "skipped tx types", skipped_types)
