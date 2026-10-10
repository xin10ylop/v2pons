"""Full-block scanner: for blocks [a, b) writes chunk files idx/<start>.json.gz (chunks of 5000 blocks) with
 P: every plain ETH transfer (value>0, input '0x'): [bn, idx, hash, from, to, value_wei(str), nonce]
 W: every tx from/to a watch address or whose input mentions one: [bn, idx, hash, from, to, value(str), sel, nonce, inputlen, mentioned]
Usage: scan.py a b threads"""
import sys, json, gzip, os, re, time, threading
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import post
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/"
os.makedirs(D + "idx", exist_ok=True)
WATCH = set(l.strip().lower() for l in open(D + "watch.txt") if l.strip().startswith("0x"))
RX = re.compile("|".join(w[2:] for w in WATCH))
CH = 5000
def getblocks(lo, hi):
    out = []
    for s in range(lo, hi, 50):
        e = min(hi, s + 50)
        for k in range(8):
            r = post([{"jsonrpc": "2.0", "id": j, "method": "eth_getBlockByNumber", "params": [hex(b), True]} for j, b in enumerate(range(s, e))])
            if isinstance(r, list) and all("result" in x and x["result"] for x in r): break
            time.sleep(2 + 2 * k)
        else: raise RuntimeError("blocks %d" % s)
        out += [x["result"] for x in sorted(r, key=lambda x: x["id"])]
    return out
def chunk(start):
    fn = D + "idx/%d.json.gz" % start
    if os.path.exists(fn): return 0
    P, Wl = [], []
    for blk in getblocks(start, start + CH):
        bn = int(blk["number"], 16)
        for t in blk["transactions"]:
            f = t["from"].lower(); to = (t.get("to") or "").lower(); inp = t["input"]; v = int(t["value"], 16)
            if v > 0 and inp == "0x": P.append([bn, int(t["transactionIndex"], 16), t["hash"], f, to, str(v), int(t["nonce"], 16)])
            m = RX.findall(inp.lower()) if len(inp) > 10 else []
            if f in WATCH or to in WATCH or m:
                Wl.append([bn, int(t["transactionIndex"], 16), t["hash"], f, to, str(v), inp[:10], int(t["nonce"], 16), len(inp), sorted(set("0x" + x for x in m))])
    with gzip.open(fn + ".tmp", "wt") as fh: json.dump({"P": P, "W": Wl, "ts": int(blk["timestamp"], 16)}, fh)
    os.rename(fn + ".tmp", fn); return 1
if __name__ == "__main__":
    a, b, th = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    starts = list(range(a - a % CH, b, CH)); starts.reverse()     # newest first
    t0 = time.time(); done = [0]
    def job(s):
        try: done[0] += chunk(s)
        except Exception as e: print("ERR", s, e, flush=True)
        if done[0] % 10 == 0: print(time.strftime("%H:%M:%S"), "done", done[0], "of", len(starts), "%.0fs" % (time.time() - t0), flush=True)
    with ThreadPoolExecutor(th) as ex: list(ex.map(job, starts))
    print("finished", time.time() - t0, flush=True)
