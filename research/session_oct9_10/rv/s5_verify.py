"""Independent check of the 'front holds the slot through hold + settle' finding, with RPC/sequencer latency.
usage: python3 s5_verify.py CASE   (A..E)"""
import sys; sys.path.insert(0, "."); from h import *
case = sys.argv[1]
RPC_MS = float(sys.argv[2]) if len(sys.argv) > 2 else 80; SEND_MS = 150
_rpc0 = E.rpc
def slow_rpc(m, p, tries=4, timeout=10):
    time.sleep(RPC_MS / 1000); return _rpc0(m, p, tries, timeout)
E.rpc = slow_rpc
class SlowSender(FakeSender):
    def post(self, i, body, retry=True):
        time.sleep(SEND_MS / 1000); return FakeSender.post(self, i, body, retry)
E.SENDER = SlowSender()
E.PULL_WATCH_S = 3.0; E.SELL_FALLBACK_S = 0.5; SYNC_BUY[0] = False
E.LAUNCH_SELECTORS = {"2fcb9108"}; FRESH = "0x" + "5e" * 20
OP_CODE = "0x" + "60806040" * 50; CODES[FRESH] = OP_CODE; E.LAUNCHER_CODE_HASHES = {keccak(bytes.fromhex(OP_CODE[2:])).hex()}; E.SEAT_CODE_HASHES = set(E.LAUNCHER_CODE_HASHES)
if case == "E":
    E.FRONT_DRY_RUN = True
reset(); E.state["nonce"] = 300; NONCE_ON_CHAIN[0] = hex(302)
L = 5000
cfg = {"A": dict(bot=9, other="follow", at=1, crowd=43),
       "B": dict(bot=None, other="follow", at=1, crowd=43),
       "C": dict(bot=13, other="follow", at=3, crowd=43),
       "D": dict(bot=9, other="follow", at=8, crowd=40),
       "E": dict(bot=9, other="seat", at=1, crowd=None),
       "F": dict(bot=9, other="seat", at=1, crowd=None)}[case]
p = front_launch(L, 3); fpos = E.state["position"]; assert fpos and fpos["entry"] == "front", fpos
print("front position dry:", fpos["dry"])
if not fpos["dry"]:
    assert wait_for(lambda: len(SENT) >= 1); buy_raw = SENT[0][1]
else:
    buy_raw = None
dest = LAUNCHER if cfg["other"] == "follow" else FRESH
other_raw = signed(DEPLOYER, dest, 0, "0x2fcb9108" + w(1), 0); ho = "0x" + keccak(other_raw).hex(); RECEIPTS[ho] = launch_receipt(ho)
t0 = time.time(); freed = None; receipts_set = False
for s_ in range(L + 1, L + 80):
    txs = []
    if s_ == L + 1 and buy_raw: txs.append(buy_raw)
    if s_ == L + cfg["at"]: txs.append(other_raw)
    if cfg["bot"] and s_ == L + cfg["bot"]: txs.append(signed(CROWD, BOT, int(0.12e18), FBUY, 70))
    if cfg["crowd"] and s_ == L + cfg["at"] + cfg["crowd"]: txs.append(signed(CROWD, UR, TRIG, BUY_DATA, 91))
    E.ingest(frame(s_, txs))
    if not fpos["dry"] and not receipts_set and fpos["sell_sent"]:
        RECEIPTS["0x" + fpos["buy_hash"]] = swap_receipt(L + 1, -E.FRONT_STAKE_WEI, fpos["feed_tokens"] or 10**18, pid=FPID)
        RECEIPTS["0x" + fpos["sell_hash"]] = swap_receipt(s_ + 1, int(E.FRONT_STAKE_WEI * 1.09), -(fpos["feed_tokens"] or 10**18), pid=FPID)
        receipts_set = True; print("front sell sent at offset", s_ - L, "why:", fpos.get("sell_why"))
    if freed is None and E.state["position"] is not fpos:
        freed = s_; print("slot freed from the front position at offset", s_ - L, "after", round(time.time() - t0, 2), "s")
    time.sleep(0.1)
q = E.state["armed"].get(PID)
print(f"case {case}: other={cfg['other']} launched at L+{cfg['at']}" + (f", crowd at L+{cfg['at'] + cfg['crowd']}" if cfg["crowd"] else ""),
      "| status:", q and q["status"], "| skips:", [e["why"] for e in events("skip") if e.get("pid") == PID],
      "| fired:", [e["ev"] for e in events() if e.get("pid") == PID and e["ev"] in ("fire", "would_fire")])
