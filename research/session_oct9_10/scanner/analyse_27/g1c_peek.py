import sys, os, collections, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common27 import *  # noqa
P = load_pools(); T = load_txs(); M = load_blocks_meta()
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
G = [p for p in P.values() if p["launch_to"] == POSM and p["selector"] == "ac9650d8" and p["calldata_len"] == 2020 and not p["hooks_zero"]]
E = load_events(set(p["pid"] for p in G))
for p in G:
    e = E[p["pid"]]; b0 = p["launch_block"]; pl = Pool(p, e, T, M)
    errs = []
    for y in pl.seq:
        if y["buy"] and not y["relay"] and y["a1"]:
            s_, L_ = pl.state_through(None, upto_li=(y["bn"], y["li"]))
            errs.append((v4math.buy_out_int(int(s_), L_, y["eth"], y["fee"]) - y["a1"]) / y["a1"])
    sw = e["swaps"]
    s = " ".join("%s+%d:%.4f:%s" % ("B" if x["a0"] < 0 else "S", x["bn"] - b0, abs(x["a0"]) / 1e18, ((T.get(x["tx"]) or {}).get("from") or "?")[2:8]) for x in sw[:9])
    print(datetime.datetime.fromtimestamp(p["launch_ts"], datetime.UTC).strftime("%m-%d %H:%M"), p["fee"], p["tick_spacing"], p["hooks"][-6:], p["launch_from"][2:8], "n%d" % p["launch_nonce"], "v%.5f" % p["launch_value_eth"], "liq %.3g" % p["liq_launch"], "adds", len(e["adds"]), "nsw", len(sw), "pull", (e["pulls"][0]["bn"] - b0) if e["pulls"] else None, "maxerr %.2g" % max((abs(z) for z in errs), default=0), "|", s)
