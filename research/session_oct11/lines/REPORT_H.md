# The hooked pump line (tok a98b3b9e): can our relay sell? (Oct 11 17:30-17:50 UTC)

Partial. The analyst confirmed the 117 pools of the line (ETH pair, fee 3000 / ts 60, a hook per pool, PositionManager multicall of 2,020
bytes, value 0); all 8 sampled hooks are byte-identical (16,724 bytes) and all 8 tokens too (1,939 bytes); every hook address ends in 0x..cc
= beforeSwap, afterSwap, beforeSwapReturnsDelta, afterSwapReturnsDelta, so a hook can revert a swap, change the amount or take a cut of the
output on either side, invisible in the Swap event; 11,989 of 11,991 sells went through the Universal Router. The analyst's run stopped
before the simulation (its bytecode step was cut off by a safety classifier).

The simulation itself (h03_sim.py, the C-1 verifier's harness: our relay's buy and sell by eth_call with the hook in the PoolKey) found no
pool to run on: the 12 newest census pools (Oct 10 09:31 to Oct 11 03:06) all have liquidity 0 now (pulled after their pump, beyond the
census's 3,000-block window: the census's "3% pulled" undercounts), and in the 6 hours to 17:50 UTC the line launched one pool (block
85986543, ~16:50), already pulled by 17:50. Verdict: UNKNOWN whether sells pass; the line is slow (1 launch in 6 h) and every pool is
pulled within hours. Parked. If it picks up, run h03_sim.py within an hour of a launch to get the answer.
