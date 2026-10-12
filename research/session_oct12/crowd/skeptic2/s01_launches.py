"""own re-find of the v3crowd launches: the V3 factory's PoolCreated with fee 100 and WETH on one side, kept when the creating tx is a
value-0 multicall (ac9650d8) of exactly 836 bytes to the PositionManager whose inner calls are createAndInitializePoolIfNecessary
(13ead562), mint (88316456) and refundETH (12210e8a), with the pool's token the minted one. Own decoder (not W/v3dec.py).
-> s01_launches.json, s01_meta.json"""
from common import *
import rpc, collections
START = int(sys.argv[1]) if len(sys.argv) > 1 else 78_700_000
head = int(rpc.call("eth_blockNumber", []), 16); th = int(rpc.call("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
pc = []; a = START
while a <= head:
    b = min(a + 400_000 - 1, head); pc += rpc.logs({"address": FACT, "topics": [T_PC]}, a, b); a = b + 1
cand = [l for l in pc if int(l["topics"][3], 16) == 100 and WETH[2:] in (l["topics"][1][-40:], l["topics"][2][-40:])]
print(f"head {head} {utc(th)}; PoolCreated {len(pc)}; fee 100 + WETH {len(cand)}", flush=True)
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in cand])
def inner_calls(inp):
    """multicall(bytes[]) -> list of inner call hex strings"""
    d = inp[10:]; off = int(d[0:64], 16) * 2; n = int(d[off:off + 64], 16); out = []
    base = off + 64
    for i in range(n):
        o = int(d[base + 64 * i: base + 64 * (i + 1)], 16) * 2; ln = int(d[base + o: base + o + 64], 16)
        out.append(d[base + o + 64: base + o + 64 + 2 * ln])
    return out
out = []; other = collections.Counter()
for l, t in zip(cand, txs):
    if not t: other["missing"] += 1; continue
    to = (t.get("to") or "").lower(); inp = t["input"]; n = (len(inp) - 2) // 2; v = int(t["value"], 16)
    key = (to[:10], inp[:10], n, v > 0)
    if not (to == NPM and inp[:10] == "0xac9650d8" and n == 836 and v == 0): other[key] += 1; continue
    try: ic = inner_calls(inp)
    except Exception: other[("undecodable",) + key] += 1; continue
    sels = [c[:8] for c in ic]
    if sels != ["13ead562", "88316456", "12210e8a"]: other[("inner",) + tuple(sels)] += 1; continue
    t0 = "0x" + l["topics"][1][-40:]; t1 = "0x" + l["topics"][2][-40:]; pool = "0x" + l["data"][-40:]
    token = t1 if t0 == WETH else t0; qs = 0 if t0 == WETH else 1          # qs: WETH's side (0 = token0)
    c0 = ic[0]; ci0 = "0x" + c0[8 + 24: 8 + 64]; ci1 = "0x" + c0[8 + 64 + 24: 8 + 128]; fee = int(c0[8 + 128: 8 + 192], 16); sqrtp = int(c0[8 + 192: 8 + 256], 16)
    m = ic[1][8:]; mw = lambda i: m[64 * i: 64 * (i + 1)]
    mt0 = "0x" + mw(0)[24:]; mt1 = "0x" + mw(1)[24:]; tl = si("0x" + mw(3)); tu = si("0x" + mw(4)); a0 = int(mw(5), 16); a1 = int(mw(6), 16); rc = "0x" + mw(9)[24:]
    if {ci0, ci1} != {t0, t1} or fee != 100 or {mt0, mt1} != {t0, t1}: other[("mismatch",) + key] += 1; continue
    out.append({"pool": pool, "token": token, "qs": qs, "lb": int(l["blockNumber"], 16), "ti": int(l["transactionIndex"], 16), "tx": l["transactionHash"],
                "lw": t["from"].lower(), "nonce": int(t["nonce"], 16), "sqrtp": sqrtp, "tl": tl, "tu": tu, "a0": a0, "a1": a1, "rcpt": rc})
bl = sorted(set(x["lb"] for x in out)); ts = {}
for b, r in zip(bl, rpc.batch("eth_getBlockByNumber", [[hex(b), False] for b in bl])): ts[b] = int(r["timestamp"], 16)
for x in out: x["ts"] = ts[x["lb"]]
out.sort(key=lambda x: (x["lb"], x["ti"]))
print(f"line launches {len(out)} (WETH token1: {sum(x['qs'] for x in out)}); first {utc(out[0]['ts'])} last {utc(out[-1]['ts'])}")
print("per day", sorted(collections.Counter(time.strftime('%m-%d', time.gmtime(x['ts'])) for x in out).items()))
print("distinct launch wallets", len({x['lw'] for x in out}), "launch wallet nonce", collections.Counter(x['nonce'] for x in out).most_common(4))
print("sqrtP levels", collections.Counter(x['sqrtp'] for x in out).most_common(8))
print("other fee-100 WETH shapes", other.most_common(10))
json.dump(out, open(J("s01_launches.json"), "w")); json.dump({"head": head, "head_ts": th, "start": START}, open(J("s01_meta.json"), "w"))
print("rpc", rpc.STATS)
