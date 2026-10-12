"""S05: is the launcher's own buy timed in blocks or in seconds? Block timestamps of the launch, the mint and the own first buy of every line
launch of the 50 h (public RPC, read-only) -> s05_times.json and s05_times.out"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpc
from scommon import *
D, R = load()
from s04_shapes import line_shape
LR = [r for r in R if line_shape(r)]
need = sorted({r["lb"] for r in LR} | {r["lb"] + r["mints"][0]["off"] for r in LR} | {r["lb"] + r["own1"]["off"] for r in LR if r["own1"]})
fn = os.path.join(OUT, "s05_times.json")
if os.path.exists(fn): T = {int(k): v for k, v in json.load(open(fn)).items()}
else:
    bl = rpc.batch("eth_getBlockByNumber", [[hex(b), False] for b in need]); T = {b: int(x["timestamp"], 16) for b, x in zip(need, bl)}
    json.dump(T, open(fn, "w"))
out = ["launch time | wallet | mint +blocks (+s) | own first buy ETH +blocks (+s) | own - mint blocks (s)"]
for r in LR:
    m = r["lb"] + r["mints"][0]["off"]; o = r["own1"]
    s = f"{time.strftime('%m-%d %H:%M:%S', time.gmtime(r['ts']))} {r['lw'][:10]} mint +{r['mints'][0]['off']} (+{T[m] - T[r['lb']]} s)"
    if o:
        ob = r["lb"] + o["off"]; s += f" own {o['eth']:.3f} +{o['off']} (+{T[ob] - T[r['lb']]} s) own-mint {o['off'] - r['mints'][0]['off']} ({T[ob] - T[m]} s)"
    out.append(s)
open(os.path.join(OUT, "s05_times.out"), "w").write("\n".join(out) + "\n"); print("\n".join(out)); print(rpc.STATS)
