"""Which of the 349 launches the engine would arm as eligible (src/flip_engine.py front_mismatch for a V3 family: WETH token0, lower tick
-887272, amount0 0, the launch price exactly on the top tick, liquidity >= MIN_LIQUIDITY 1e21; pin: tick spacing 1 from fee 100), from the
calldata decode of s01 (v3dec, the engine's decode_launch_v3's source). Offline. Writes s15_eligible.out (stdout)."""
from common import *
import collections
from v3dec import sqrt_at_tick
L = json.load(open(J("s01_launches.json")))["launches"]
why = collections.Counter()
for x in L:
    if x["qs"] != 0: why["WETH is token1 (mirrored: not traded)"] += 1; continue
    if x["lo"] != -887272 or x["amount0"] or x["sqrt_p"] != sqrt_at_tick(x["hi"]): why["not the line's range"] += 1; continue
    if x["liq"] < 1e21: why["no liquidity"] += 1; continue
    why["eligible"] += 1
print(dict(why)); print("top ticks of the eligible:", collections.Counter(x["hi"] for x in L if x["qs"] == 0).most_common(8))
