| class | families | pools in 48 h | why not | source |
|---|---|---|---|---|
| the 7fde822e launchpad (27 launch contracts; deployer `0x06cb3a68` made 454 of its 490 pools; here its families with 5 or more launches) | 43 | 375 | token-only pools with no ETH in them; a real buy in at most 1 pool per family; nobody pulls; a front sells into the untouched pool at -2.06% (two 1% fees) | `analyse_25/results.json` (WIDE-7fde822e: front -2.06%, n 490), `analyse_10/results.json` |
| fee-farm pools (fee 10% to 88% a swap) | 17 | 297 | two fees exceed any move; front -24% to -98% | `analyse_23/results.json` (fee >= 10% class: -75.3%, n 167), `analyse_21/results.json` |
| no ETH at the launch price (`0xfcd18241` at three fee tiers, `0x16cf6788`, a PM 0.3% family) | 5 | 276 | a front cannot buy at launch; no real buy | `analyse_1/results.json`, `analyse_4/results.json`, `report/work/a23_missing.txt` |
| the public launchpad `0x0000ffff` | 5 | 42 | no pull, organic first buys at random times; front -0.6% to -9.2% | `analyse_19/results.json` notes |
| buyers exist but both rules lose | 27 | 432 | a real buyer but no schedule or crowd behind it; front and follow negative after fees | Appendix A |
