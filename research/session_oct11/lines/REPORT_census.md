# Census 2 (the builder's hand-back, Oct 11 15:29 UTC)

All 64,416 in-scope pools from the last 7 days (blocks 79,984,897-85,881,750, 2026-10-04 13:52:42 to 2026-10-11 13:52:41 UTC). Every pool's
3,000-block event window complete, all 46,065 launch transactions fetched. Only the public RPC was used. Files kept here: README.md (method,
definitions, schemas, tables, problems), summary.json, top40.json, report_tables.md, shared_fps.json, bonding.json, load.py, code/.
Not kept (size): pools.jsonl (216 MB), families_*.json, overlap.json, cache/ (3.1 GB).

Counts per DEX: v4 32,416 pools (31,831 with liquidity, 22,283 with swaps, 12,249 with a real buy, 7,203 pulled in 3,000 blocks, 2,862 with an
outsider buy); V2 0x8bceaa40 15,947 (2,037 with liquidity); V2 0x0d1ebb17 13,951 (95 with a real buy); V3 2,102 (1,574 with a real buy,
1,331 pulled). Bonding-curve factory: 20,737 creates, 918 of its tokens later appear as census pools.

Families with >= 5 launches: token skeleton (tok) 184 of 1,050 (63,132 pools); launcher code|selector (lc) 245 of 1,152; strict 607 of 8,665;
funding root (sample) 6 of 166. 65 of 184 token families sit >= 90% in one launcher family, 91 split across >= 3.

Top 40 (merged tok/lc): 1 tok:fa4982d5 V2 launchpad template 28,547 (inert); 2 lc:c873e135|ac9650d8 PositionManager multicall 21,018
(the volume bot's v3.0 3,355, v2.433 3,182, v5.0 1,543 and 7,990 wallets' others); 3-4 V2 launchpads 13,780 and 11,970 (0 pulls); 5 tok:16afd61e
shared v4 template 8,102 (222 real buys); 6 tok:037449b1 vbot v3.0/v5.0 5,061; 7 tok:aff2095f vbot v2.433 3,207 (reaction 254/407: its own
decoys); 8 tok:58d59320 v4 WETH/USDG dynamic fee via ERC-4337 2,772; 9 V2 launchpad 2,003; 10 tok:d4e7eae4 mixed V3/v4 1,991; 11 V2 router
addLiquidityETH 1,834; 12 EntryPoint launches 1,482; 13-14 C-2 1,433/1,230; 15 tok:70adce63 V2 40-50 ETH launches 1,217; 16 V3 position
manager multicall 1,155; 17 tok:cb79985d C-1 960 (frb +116 via router 0xd6d35b56); 18 operator A 686 (frb +44); 19 PositionManager f7020405
627; 20 tok:0f34e3b5 V2 fleet of 5,072 single-use wallets 609 (frb +3); 21-40 smaller (see top40.json).

Problems: outsider coverage partial (buying wallet known for 19% of pre-pull buys; use outsider12); the "< 3 pools" rule catches single-use
crowds; funding is a sample; lc and tok over-merge shared entry points and templates; 1,496 launches via ERC-4337; V2/V3 "launch" = pair
creation; USDG at a fixed 2,570 per ETH; our own trades in 1,091 pools flagged `ours`.
