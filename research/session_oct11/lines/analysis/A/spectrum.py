"""Step 4 + overview: msg.value spectrum of the whole lc family (vbot included, flagged) and of the non-vbot remainder; calldata lengths,
quotes, fee/ts; the exact-shape groups (value, clen, fee, ts, sqrt_p0, mint L, quote) ranked."""
from common import *
rows = [r for r in all_rows() if not r["quote_pair"]]
E = load_ev()
print("lc family pools (quote pairs excluded):", len(rows))
vb = [r for r in rows if is_vbot(r)]; nv = [r for r in rows if not is_vbot(r)]
print("vbot (known_fp or value 2.4333285/3/5):", len(vb), " remaining:", len(nv), " wallets:", len({r["launch"]["from"] for r in nv}))
print("known_fp of remaining:", C.Counter(r["known_fp"] for r in nv))
# value spectrum
def vb_(v):
    return "0" if v == 0 else f"{v/1e18:.10g}"
spec_all = C.Counter(vb_(r["launch"]["value_wei"]) for r in rows)
spec_nv = C.Counter(vb_(r["launch"]["value_wei"]) for r in nv)
print("\n== msg.value spectrum, whole lc family (top 40 exact values) ==")
for v, n in spec_all.most_common(40):
    print(f"  {v:>16} ETH  {n:6d}  (non-vbot {spec_nv.get(v,0)})")
print("distinct exact values:", len(spec_all), " non-vbot:", len(spec_nv))
# log-bucket histogram for non-vbot
import math
bk = C.Counter()
for r in nv:
    v = r["launch"]["value_wei"] / 1e18
    b = "0" if v == 0 else ("<1e-6" if v < 1e-6 else f"1e{math.floor(math.log10(v))}")
    bk[b] += 1
print("\n== non-vbot value buckets (decade) ==", sorted(bk.items(), key=lambda x: (x[0] != '0', x[0])))
print("\n== non-vbot calldata_len ==", C.Counter(r["launch"]["calldata_len"] for r in nv).most_common(12))
print("== non-vbot quote ==", C.Counter(r["quote"] for r in nv))
print("== non-vbot fee/ts ==", C.Counter((r["fee"], r["tick_spacing"]) for r in nv).most_common(12))
print("== non-vbot hooks zero ==", C.Counter(r["hooks"] == "0x" + "0" * 40 for r in nv))
print("== non-vbot n_pools_in_tx>1 ==", C.Counter(r["launch"]["n_pools_in_tx"] > 1 for r in nv))
# 1444-byte ETH no-hook with value>0 (engine-keyable shape)
ok = [r for r in nv if r["launch"]["calldata_len"] == 1444 and r["quote"] == "ETH" and r["hooks"] == "0x" + "0" * 40]
print("\nnon-vbot 1444-byte ETH no-hook:", len(ok), " with value>0:", sum(r["launch"]["value_wei"] > 0 for r in ok))
print(" their value spectrum (top 30):", C.Counter(vb_(r["launch"]["value_wei"]) for r in ok).most_common(30))
json.dump({"spec_all": spec_all.most_common(), "spec_nonvbot": spec_nv.most_common(), "decades_nonvbot": bk,
           "spec_1444_eth_nohook": C.Counter(vb_(r["launch"]["value_wei"]) for r in ok).most_common()}, open(os.path.join(OUT, "spectrum.json"), "w"))
