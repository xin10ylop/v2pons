"""BNB: token code of the router-copy tokens vs the 2.433 token; router-copy mints in 5,000-block samples at earlier dates (when did this BNB line run)."""
import sys, json, time; sys.path.insert(0, '.'); import rpcx
from eth_utils import keccak
T = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"; pad = lambda a: "0x" + "0" * 24 + a[2:].lower()
RC = "0x07cb61618b69234d954022ff738a015548715533"
ref = json.load(open("c01_refcode.json"))
R = [json.loads(l) for l in open("c14_bsc_watch_cache.jsonl")]
mints = sorted(set(r["a"] for r in R if r["t"][0] == T and r["t"][1] == pad("0x" + "0" * 40) and r["t"][2] == pad(RC)))
for a in mints[:5]:
    c = rpcx.call("bsc", "eth_getCode", [a, "latest"]); print("token", a, "len", (len(c) - 2) // 2, "hash", "0x" + keccak(hexstr=c).hex(), "== RH 2.433 token" if "0x" + keccak(hexstr=c).hex() == ref["token2433"]["hash"] else "")
h, th = rpcx.head("bsc_h"); out = []
for hrs in [6, 12, 18, 24, 30, 36, 39, 42, 44, 46, 48, 54, 60, 72, 96, 120, 168, 240, 336, 480, 720]:
    b = h - int((th - (1791810000 - (hrs - 43) * 0)) / 0.45) if False else None
    t_target = th - hrs * 3600; b = h - int(hrs * 3600 / 0.45)
    try:
        ls = rpcx.logs("bsc_h", {"topics": [T, pad("0x" + "0" * 40), pad(RC)]}, b, b + 4999)
        ts = rpcx.ts_of("bsc_h", b)
        out.append({"hrs_ago": hrs, "b": b, "ts": ts, "mints_in_5000": len(ls)})
        print(f"{hrs:4d} h ago  block {b}  {time.strftime('%m-%d %H:%M', time.gmtime(ts))}  mints in next 5000 blocks (~37.5 min): {len(ls)}", flush=True)
    except Exception as e: print(hrs, "ERR", str(e)[:120])
json.dump(out, open("c17_bsc_era.json", "w"))
