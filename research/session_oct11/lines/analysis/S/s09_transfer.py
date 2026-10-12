"""S09: the launch wallet's third tx (token transfer a9059cbb between the mint and the own buy): recipient, amount, and its timing in blocks
and seconds relative to the launch and the own buy (offsets from s08_between.out; public RPC, read-only) -> s09_transfer.out"""
import sys, os, re, time, ast
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpc
from scommon import *
D, R = load(); byl = {r["lb"]: r for r in R}
T5 = {int(k): v for k, v in json.load(open(os.path.join(OUT, "s05_times.json"))).items()}
out = []
for line in open(os.path.join(OUT, "s08_between.out")):
    if not line[0].isdigit(): continue
    lb = int(line.split()[0]); r = byl[lb]
    txs = ast.literal_eval(line.split("value) ", 1)[1].strip())
    tr = [t for t in txs if t[3] == "0xa9059cbb"]
    if not tr: out.append(f"{lb}: no transfer"); continue
    off = tr[0][0]
    b = rpc.call("eth_getBlockByNumber", [hex(lb + off), True]); ts = int(b["timestamp"], 16)
    t = next(t for t in b["transactions"] if t["from"].lower() == r["lw"] and t["input"][:10] == "0xa9059cbb")
    to = "0x" + t["input"][10 + 24:10 + 64]; amt = int(t["input"][74:138], 16)
    own = r["own1"]; ts_own = T5[lb + own["off"]]
    out.append(f"{lb} {time.strftime('%m-%d %H:%M', time.gmtime(r['ts']))}: transfer +{off} (+{ts - r['ts']} s) to {to} amount {amt / 1e18:.4g} tokens; own buy +{own['off']} "
               f"(+{ts_own - r['ts']} s): own - transfer {own['off'] - off} blocks, {ts_own - ts} s")
    print(out[-1])
open(os.path.join(OUT, "s09_transfer.out"), "w").write("\n".join(out) + "\n"); print(rpc.STATS)
