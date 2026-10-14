"""Control check of the replay: our relay's realized return in each of the last 24 VB 2.433 pools vs the simulated front (buy at the L+1 head,
sell at the head of T+1) at the relay's own size. Output: s08_control_check.out."""
from common import *
import s07_traits as S
from s08_front import Sim
for pid in [t["pid"] for t in jload("s05_targets.json") if t["fam"] == "CONTROL VB 2.433"]:
    r = S.rows[pid]; sw = S.swaps(S.EV[pid], r)
    rel = [s for s in sw if S.actor(s["h"]).startswith("0x2abb5653")]
    b = [s for s in rel if s["buy"]]; se = [s for s in rel if not s["buy"]]
    if not b or not se: print(pid[:10], "no relay round trip"); continue
    x = Sim(pid, "0x1cbaf24d:0xc1120e3d").front(b[0]["q"])
    print("%s %s relay buy +%d %.4f ETH sell +%d real %+.2f%% | sim L+1 buy, sell T+1 (T=+%s) %+.2f%% nrev %d" % (pid[:10], hm(r["t"]), b[0]["bn"] - r["b"], b[0]["q"] / 1e18, se[0]["bn"] - r["b"], 100 * (se[0]["q"] / b[0]["q"] - 1), x["T"], 100 * x["gross"], x["nrev"]))
