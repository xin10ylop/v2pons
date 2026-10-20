"""decode launch calldata: words, strings (name/symbol/uri); fingerprint per track"""
import sys
exec(open("who.py").read().split('if __name__')[0])
TX = json.load(open(S + "ops/launcher_txs.json"))
import re
def dec(inp):
    d = inp[10:]; w = [d[i:i+64] for i in range(0, len(d), 64)]
    def s_at(off):
        o = off // 32; n = int(w[o], 16); return bytes.fromhex("".join(w[o+1:o+1+(n+31)//32]))[:n].decode("utf8", "replace")
    try: name, sym, uri = s_at(int(w[1], 16)), s_at(int(w[2], 16)), s_at(int(w[3], 16))
    except Exception: name = sym = uri = "?"
    nums = [w[i] for i in range(4, 13)]
    return name, sym, uri, nums
out = {}
for x in X:
    t = TX[x["h"]]; name, sym, uri, nums = dec(t["input"])
    m = re.match(r"(https?://[^/]+)(/.*?)([0-9a-f]{6,})?(\.json)?$", uri)
    host = m.group(1) if m else uri[:40]; pat = (m.group(2) if m else "")
    out[x["h"]] = {"host": host, "pat": pat, "nums": [str(int(n, 16)) if int(n,16) < 2**200 else "neg" + str(2**256 - int(n,16)) for n in nums], "tip": int(t["tip"] or "0x0", 16), "maxfee": int(t["maxfee"] or "0x0", 16), "gas": t["gas"], "sym": sym}
json.dump(out, open(D + "fp.json", "w"))
day = collections.defaultdict(collections.Counter)
for x in X:
    o = out[x["h"]]; day[T(x["bn"])[:5]][(o["host"], o["pat"])] += 1
for d in sorted(day): print(d, dict(day[d]))
