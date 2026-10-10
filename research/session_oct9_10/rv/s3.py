import sys; sys.path.insert(0, "."); from h import *
E.PULL_WATCH_S = 3.0; E.SELL_FALLBACK_S = 0.5; SYNC_BUY[0] = False
reset(); E.state["nonce"] = 300; NONCE_ON_CHAIN[0] = hex(302)
L = 5000
p = front_launch(L, 3); fpos = E.state["position"]; assert fpos and fpos["entry"] == "front"
assert wait_for(lambda: len(SENT) == 1); buy_raw = SENT[0][1]
t0 = time.time()
follow_raw = signed(DEPLOYER, LAUNCHER, 0, "0x2fcb9108" + w(1), 0); hf = "0x" + keccak(follow_raw).hex(); RECEIPTS[hf] = launch_receipt(hf)
for s_ in range(L + 1, L + 60):
    txs = []
    if s_ == L + 1: txs = [buy_raw]
    if s_ == L + 3: txs = [follow_raw]                                # a follow launch 3 blocks after the front fire
    if s_ == L + 9: txs = [signed(CROWD, BOT, int(0.12e18), FBUY, 70)]   # the volume bot's buy: take profit
    if s_ == L + 3 + 44: txs = [signed(CROWD, UR, TRIG, BUY_DATA, 91)] # follow's crowd first buy, 44 blocks after its launch
    E.ingest(frame(s_, txs))
    if s_ == L + 9:
        RECEIPTS["0x" + fpos["buy_hash"]] = swap_receipt(L + 1, -E.FRONT_STAKE_WEI, fpos["feed_tokens"], pid=FPID)
        RECEIPTS["0x" + fpos["sell_hash"]] = swap_receipt(L + 10, int(E.FRONT_STAKE_WEI * 1.09), -fpos["feed_tokens"], pid=FPID)
    if E.state["position"] is None and "freed" not in globals():
        freed = s_; print("slot freed at block offset", s_ - L, "after", round(time.time() - t0, 2), "s")
    time.sleep(0.1)
q = E.state["armed"].get(PID)
print("follow pool: status", q and q["status"], "first_buy", q and q["first_buy"], "| follow skip reasons:", [e["why"] for e in events("skip") if e.get("pid") == PID])
