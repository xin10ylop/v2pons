import sys; sys.path.insert(0, "."); from h import *
E.LAUNCH_SELECTORS = {"2fcb9108"}; FRESH = "0x" + "5e" * 20
OP_CODE = "0x" + "60806040" * 50; CODES[FRESH] = OP_CODE; E.LAUNCHER_CODE_HASHES = {keccak(bytes.fromhex(OP_CODE[2:])).hex()}; E.SEAT_CODE_HASHES = set(E.LAUNCHER_CODE_HASHES)
def seat_launch(seq, nonce):
    raw = signed(DEPLOYER, FRESH, 0, "0x2fcb9108" + w(1), nonce); h = "0x" + keccak(raw).hex(); RECEIPTS[h] = launch_receipt(h)
    E.ingest(frame(seq, [raw])); assert wait_for(lambda: PID in E.state["armed"]); return E.state["armed"][PID]
# --- S1: live front fires at L; a seat launch at L+1 never gets the slot
reset(); E.state["nonce"] = 300
p = front_launch(5000, 3); fpos = E.state["position"]; assert fpos and fpos["entry"] == "front" and not fpos["dry"]
q = seat_launch(5001, 4); assert q["entry"] == "seat" and q["eligible"]
E.ingest(frame(5002, [SENT[0][1]]))                      # our front buy lands
for s_ in range(5003, 5012):
    E.ingest(frame(s_, []))
print("S1 seat pool status:", q["status"], "| position still front:", E.state["position"] is fpos, "| skips:", [e["why"] for e in events("skip") if e.get("pid") == PID])
