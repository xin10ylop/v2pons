"""The live cap counts from our buy's own block (src/flip_engine.py _fire: send_after = launch + 78 - (fire + 2), applied from buy_seq), so a buy
landing at + k sends the sell at launch + 76 + k; the 3 s buy deadline bounds k. Pulls since Oct 10 12:00 (the replay's rows: the first Burn > 0)
in the stretch the cap could reach. Writes s14_cap_stretch.out (stdout)."""
import json, os
from common import *
R = json.load(open(os.path.join(HERE, "..", "replay", "r06_rows.json")))["rows"]
b = sorted(r["burn_off"] for r in R if r["burn_off"] is not None)
for hi in (80, 85, 90, 100, 110, 120):
    print(f"pulled at or before + {hi}: {sum(x <= hi for x in b)} of {len(R)}")
print("earliest pulls:", b[:10])
