#!/bin/sh
# re-run the whole skeptic pipeline from the public RPC (caches in cache/ are reused); the test slice = pools launched at or after block
# 86133015 with T, not in the finder's 200 (u2_parse.py). u_mon.py (live state monitor) runs separately: python3 u_mon.py MINUTES
set -e
cd "$(dirname "$0")"
python3 u1_pools.py 7 > u1_pools.out 2>&1
python3 u2_parse.py > u2_parse.out 2>&1
python3 u3_blocks.py > u3_blocks.out 2>&1
python3 u4_touch.py > u4_touch.out 2>&1
python3 u5_generic.py > u5_generic.out 2>&1
python3 u6a_pools_long.py 12.5 > u6a_pools_long.out 2>&1
python3 u6b_reaction.py > u6b_reaction.out 2>&1
python3 u7_front.py > u7_front.out 2>&1
python3 u8_clock.py > u8_clock.out 2>&1
python3 u10_deploy.py > u10_deploy.out 2>&1
python3 u9_mon_summary.py > u9_mon_summary.out 2>&1
