#!/bin/bash
# the analyses, from the caches (no RPC): r04 build, then r05-r09, r11, r12, r14, r15 -> their .out files
cd /home/user/v2pons/research/session_oct12/crowd/reaction
python3 r04_build.py > r04_build.out 2>&1
for s in r05_groups r06_hazard r07_sold r08_fronters r09_cost r11_bot1_events r12_entry r14_bot_strat r15_bot_wave r16_early_pulls r17_bot_perm r20_validate_w r23_extractors r24_early_pull_cases r25_data; do
  python3 $s.py > $s.out 2>&1 || echo "$s failed" >&2
done
