import sys, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout")
from rpc1 import rpc, post, LOG
U = "https://arb1.arbitrum.io/rpc"
def blk(n): return rpc(U, "eth_getBlockByNumber", [hex(n) if isinstance(n, int) else n, False])["result"]
h = blk("latest"); head = int(h["number"], 16); th = int(h["timestamp"], 16)
print("head", head, "ts", th, time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(th)), "baseFee_gwei", int(h["baseFeePerGas"], 16) / 1e9, "l1BlockNumber", int(h.get("l1BlockNumber", "0x0"), 16))
# block rate over the last ~1,000,000 blocks
b = blk(head - 1_000_000); tb = int(b["timestamp"], 16)
rate = 1_000_000 / (th - tb); print("blocks/s over last 1,000,000:", round(rate, 4), "s/block", round(1 / rate, 4))
# block at now - 7 days by bisection on timestamps
target = th - 7 * 86400
lo, hi = head - int(rate * 7 * 86400 * 1.3), head
while hi - lo > 1:
    m = (lo + hi) // 2; t = int(blk(m)["timestamp"], 16)
    if t < target: lo = m
    else: hi = m
tb7 = int(blk(hi)["timestamp"], 16)
print("block_7d_back", hi, "ts", tb7, time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(tb7)), "blocks in 7 d", head - hi, "rate_7d", round((head - hi) / (th - tb7), 4))
target = th - 86400; lo, hi = head - int(rate * 86400 * 1.3), head
while hi - lo > 1:
    m = (lo + hi) // 2; t = int(blk(m)["timestamp"], 16)
    if t < target: lo = m
    else: hi = m
print("block_24h_back", hi, "blocks in 24 h", head - hi)
json.dump({"head": head, "head_ts": th, "rate_1m": rate, "b7": None}, open("/dev/null", "w"))
print("requests", len(LOG), "non-ok", [x for x in LOG if x[1] != "ok"])
