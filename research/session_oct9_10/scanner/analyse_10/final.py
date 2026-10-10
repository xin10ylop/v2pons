"""compile results.json: the per-family entries returned to the orchestrator, plus the machine numbers they rest on"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common10 import fmt_rule  # noqa
S = json.load(open(os.path.join(HERE, "stats.json"))); C = json.load(open(os.path.join(HERE, "calib.json")))
PW = json.load(open(os.path.join(HERE, "postwindow.json"))); D = json.load(open(os.path.join(HERE, "depth.json")))
X2 = json.load(open(os.path.join(HERE, "fam2_extra.json"))); TC = json.load(open(os.path.join(HERE, "trap_controls.json")))
K1, K2, K3, K4 = json.load(open(os.path.join(HERE, "keys.json")))
f = lambda k, r: fmt_rule(S[k][r])
fams = []
for k, contract, size, chash, nonces, blocks, span, gaps, fb in (
        (K1, "0x258dd351af960bc487532c0108d3f90e8d115369", 19028, "93eda754", "1879-1896", "83,639,379-83,688,847", 1.41, "2910/2937/11659", "+2/+3/+3"),
        (K4, "0x78ba8b21e8adbbc84f2e11f0e92c6f2299b78281", 19036, "a5f8b1cd", "1944-1959", "83,820,922-83,864,620", 1.25, "2882/5821/8789", "+3/+3/+4")):
    fams.append({
        "key": k, "known": "none", "count": 9, "launches_per_day": 4.5,
        "launcher": (f"one EOA 0x06cb3a6841c92525e7a1998328e7c9d37e98d937 (nonces {nonces}) calling its own launch contract {contract} ({size} bytes, code hash {chash}...) "
                     "with 7fde822e, 804-byte calldata, value 0, tip 0, gas ~1.70-1.74M. The calldata is token metadata from the imortal.buzz launchpad (name, symbol, "
                     "an imortal.buzz/i/<ipfs cid> image, x.com links), creator/fee address 0x94dddbb54535ee3515b3b9e10be5a6569c586324, constants 2500 and 1.7 ETH. "
                     "Pool: fee 1%, ts 200, hooks 0, one token-only range [132800, 201800] at tick0 201800, L 32156000099526845215062: no ETH in the pool, virtual ETH "
                     f"depth L/sqrtP = 1.335 ETH. This contract served these 9 launches in {span} h (blocks {blocks}, gap p10/50/90 {gaps} blocks), then the wallet "
                     "moved to another contract: 0x06cb3a68 made 454 pools in the 48 h window (227/day) on 91 strict families; the 7fde822e selector has 490 pools, 27 contracts, 5 deployers."),
        "first_buy": (f"first non-launch buy in 9/9 pools: the chain-wide dust bot 0xe71a69f434a719cd5afa411568b69716aab3b84a via Universal Router execute (1,156 bytes), "
                      f"offset p10/50/90 {fb} blocks, size 2e-6/2e-6/2e-6 ETH; one wallet, not fresh; first buy >= 0.0002 ETH: 0/9 pools (fraction 0). After the 3,000-block "
                      "window: eth_getLogs of every Swap of the 9 pools to head 85,255,938 shows no later swap at all. Deployer-wide: 5 of 454 pools ever saw > 0.001 ETH of buys."),
        "pull": ("0/9 pulled within 3,000 blocks and 0/9 ever (every ModifyLiquidity of the 9 pools to head 85,255,938, 1.39-1.57M blocks after launch: only the launch mint); "
                 "offsets from launch / first buy n/a; nobody pulls (0/454 of the deployer's pools within 3,000 blocks)."),
        "outsiders": ("the only buyer is the dust bot (9/9 pools, 2e-6 ETH at +2..+4); no scheduled buy and no real-size outsider; trap test not computable: 0 pulls with "
                      "or without outsiders (0/9 ever, 0/454 across the deployer)."),
        "front_rule": f(k, "front") + ". No buy ever comes: every trade sells at launch+20 into the untouched pool and pays two 1% fees + 0.07% gas.",
        "follow_rule": "n 0: no buy >= 0.0002 ETH in any pool (0 trades, $0 a day).",
        "capacity": ("n/a: no scheduled buy to decode. Reference under the assumption minOut = 0.99 x launch-state quote: 0.0068 ETH ahead cuts a 0.0058 ETH buy's output 1% "
                     "(0.0069 for a 0.05 ETH buy; virtual depth 1.335 ETH). Assumption, not measured."),
        "engine_config": ("none: nothing to trade. Recognizer if ever needed: from 0x06cb3a6841c92525e7a1998328e7c9d37e98d937, selector 7fde822e, value 0, calldata 644-964 bytes "
                          "(to = its current launch contract, rotating every 9-16 launches); pool fee 10000, ts 200, hooks 0, token-only range at tick0 201800; no exit trigger exists."),
        "verdict": "no-schedule", "candidate_score": 0,
        "notes": ("A user-facing token launchpad (imortal.buzz) deploying single-sided token pools; no operator buys, no crowd, no pull: the structure (scheduled buy + pull) is absent. "
                  "Pricer calibrated on the controls first (v2.433 front +13.98% on the live window, 409 pools; 10,160 real buys re-predicted with 0 errors > 1e-4).")})
fams.insert(1, {
    "key": K2, "known": "none", "count": 9, "launches_per_day": 4.5,
    "launcher": ("a graduation sniper, not a token operator: EOA 0x2c2572da570646b402b9b9e625aa102803904a49 (nonces 155,495-158,000, a busy bot) calls its contract "
                 "0x2a53386daf0bf3eedd9e715d162649764358c7b5 (7,089 bytes) with 3d9ab7c9 and exactly 0.15 ETH (gas 2.2M, tip 0): it buys the last of a token's bonding curve "
                 "(launchpad factory 0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e; calldata = curve, token, factory, 1100, 0.15 ETH, Universal Router, 0.125 ETH cap, deadline), "
                 "the curve graduates into a v4 pool (fee 0, ts 200, hook 0xe5e702641ea86f4ae6cc3cdaed2b886f976be044 with flags BEFORE_INITIALIZE|AFTER_SWAP|AFTER_SWAP_RETURNS_DELTA, "
                 "a full-range ~204M-token position minted through the POSM by migrator 0xc7819b64, virtual ETH depth 4.20-4.26 ETH), and the rest of the 0.15 ETH buys on v4 in "
                 "the same tx (0-0.108 ETH, median 0.0196). 9 of the 31 hook-0xe5e70264 graduations in the window (other snipers 0x387a453d, 0xe0703eaa, ... graduate the rest); "
                 "launch gaps 55k/121k/400k blocks (p10/50/90), spread over 46.7 h. The hook taxes every swap 4% of its output (1% + 3%, measured from receipts: hookfee.py)."),
    "first_buy": ("first non-launch buy in 9/9 pools at +1/+1/+1 blocks, 0.00025/0.002646/0.06 ETH (p10/50/90), through the Universal Router execute (5), 0xe0703eaa a67aeb8b (3), "
                  "0x7eea5f60 991f1cef (1); from 5 distinct recurring sniper wallets (nonces 919-5038, not fresh): 0xf52b9a54 (3), 0x7503caf1 (2), 0x4992e7ad (2), 0xf08ad284, 0x46bab0a8. "
                  "In the first 5 blocks the same sniper set appears across pools (0xf08ad284 in 7/9, 0xf52b9a54 7/9, 0x4992e7ad 5/9, 0x20916bba 5/9). Fraction with a buy >= 0.0002: 9/9 "
                  "(all at +1). Then a real market: 71-267 buys and 46-209 sells per pool in 3,000 blocks, 1.3-8.9 ETH of buys. No buy comes from the launcher after its launch tx."),
    "pull": ("0/9 pulled within 3,000 blocks; the launch liquidity is never removed (every ModifyLiquidity to head 85,255,938: the 9 launch mints plus one third party's "
             "concentrated add/remove pair at +121,579..+135,360 in pool 0x7020b110); offsets n/a; nobody pulls (the launchpad position is locked: 0/31 hook pools pulled in the window)."),
    "outsiders": ("everyone after the launch tx is an outsider: 9/9 pools have 1-4 sniper buys at +1 (0.00025-0.08 ETH) before any later buy; with no pull at all there is "
                  "no reaction to measure (trap test: 0 pulls with outsiders in 9/9, no pools without them)."),
    "front_rule": (f(K2, "front") + ". Sell trigger = the first buy >= 0.0002 ETH behind ours at +2/+3/+4, sell at +3..+5. The 4% hook tax each way is the killer: "
                   f"without it the same trades price {100*X2['front_no_tax']['mean']:+.2f}% mean, {100*X2['front_no_tax']['median']:+.2f}% median, 6/9 up."),
    "follow_rule": (f(K2, "follow") + f". Our buy lands at +2, the next buy at +4..+5 (2/3/3 blocks after the first), sell at +4..+5; without the hook tax {100*X2['follow_no_tax']['mean']:+.2f}% mean."),
    "capacity": ("the first real buy is a sniper's (Universal Router execute: nested, not decoded; or third-party routers): assumed minOut = 0.99 x launch-state quote (an assumption): "
                 "0.0212/0.0213/0.0216 ETH (p10/50/90) may sit ahead of it from the launch state; virtual depth 4.2 ETH. Irrelevant here: these buys are not scheduled."),
    "engine_config": ("none worth building. Recognizer if wanted: to 0x2a53386daf0bf3eedd9e715d162649764358c7b5, selector 3d9ab7c9, 292 bytes, value 0.15 ETH, from 0x2c2572da; "
                      "eligibility: hook 0xe5e70264 (4% tax each way) makes any flip of a few percent negative; no exit trigger (no scheduled buyer, no pull)."),
    "verdict": "no-schedule", "candidate_score": 0,
    "notes": ("Launchpad graduations raced by a sniper bot, followed by a competitive multi-bot sniper market at +1; no operator schedule and no pull. Also unprofitable on its own "
              "terms: 8% round-trip hook tax vs a +0.4% gross edge at launch+1.")})
fams.insert(2, {
    "key": K3, "known": "none", "count": 9, "launches_per_day": 4.5,
    "launcher": ("8 unrelated EOAs (0xec2fa7c1 x2, 0x820d27be, 0xad2616dd, 0xca211752, 0x373733c5, 0xf9a8e55f, 0x383c1453, 0x01192597; nonces 319-13,366) using the Uniswap app's "
                 "create-position multicall on the POSM [initializePool f7020405, a permit, modifyLiquidities dd46508f] (2,020 bytes, tip 0-10 wei: wallet-made), custom fee 20% "
                 "ts 2000 hooks 0, with 0.00043-0.1 ETH (median 0.0027): mostly full-range positions, virtual ETH depth 0.001/0.004/0.012 ETH. 8 of the 9 tokens already had ETH pools "
                 "(mostly graduated launchpad tokens with hook-0xe5e70264 pools): extra high-fee LP pools on existing tokens, not launches. Gaps 37k/95k/115k blocks."),
    "first_buy": ("1/9 pools had any non-launch buy within 3,000 blocks: 7.3e-5 ETH at +1,165 via 0x076b3601 (bd6858d6); 0/9 had a buy >= 0.0002 ETH (fraction 0). After the window "
                  "(to head 85,255,938): 270 more swaps, 76 buys >= 0.0002 ETH (0.0015-0.003 ETH) hours to days later (buyers not examined)."),
    "pull": ("0/9 within 3,000 blocks. Later (eth_getLogs to head): the launch liquidity was removed in 6/9 at +4,269/+4,313/+4,623/+13,395/+328,188/+1,365,193 blocks (7 min to 39 h) "
             "and partly in 2 more, through the POSM (owners not examined), with concentrated re-adds in 3 pools: retail LP management, no fixed margin; offsets from a first buy n/a."),
    "outsiders": "no scheduled buy; trap test not computable (0 pulls within 3,000 blocks, no buys).",
    "front_rule": f(K3, "front") + ". Nobody buys by +20; two 20% fees on a stake larger than the pool.",
    "follow_rule": "n 0: no buy >= 0.0002 ETH within 3,000 blocks in any pool (0 trades, $0 a day).",
    "capacity": "n/a: no scheduled buy. Reference (assumed 0.99 x launch-state quote): 1.1e-5/3.4e-5/8.9e-5 ETH ahead cuts a 0.0058 ETH buy 1% (pools of 0.001-0.012 ETH virtual depth).",
    "engine_config": "none: no recognizable operator (8 people), nothing to trade.",
    "verdict": "no-schedule", "candidate_score": 0,
    "notes": "Not an operator: retail users adding 20%-fee pools to existing tokens through the Uniswap app; no buys, pulls hours to days later."})
# controls
v = S["control:vbot-v2.433"]; a = S["control:operator-A"]
fams.append({
    "key": "control:vbot-v2.433 (0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true at value 2.4333285 ETH)", "known": "vbot-v2.433", "count": 1843,
    "launches_per_day": v["launches_per_day_window"],
    "launcher": "POSM multicall 1,444 bytes, exactly 2.4333285 ETH, a fresh wallet per launch (1,843 deployers for 1,843 pools); launch gap p10/50/90 162/173/3597 blocks.",
    "first_buy": ("first non-launch buy (any size) at +2/+3/+3: the dust bot 0xe71a69f4 (940 pools) or the operator's 0x65050a9b-router decoys (854); first >= 0.0002 ETH at "
                  "+2/+8/+10 (decoy 0.00495 via 0x65050a9b in 525 pools). The scheduled buy (bot router 0x1cbaf24d c1120e3d) in 1,842/1,843 pools at +8/+9/+10, "
                  "0.0495/0.175/0.25 ETH, 67 distinct calling wallets (nonces 10k-40k)."),
    "pull": ("1,482/1,843 (80.4%) pulled within 3,000 blocks, all by the launch wallet through the bot router (a0f7978d); from launch +11/+13/+127, from the bot's buy +3/+3/+117 "
             "(exactly +3 in 1,044, +4 in 101, +2 in 14)."),
    "outsiders": ("trap test: with our relay's 0.0058 ETH buy ahead of the bot's buy (1,047 pools) the pull came 3 blocks after the bot's buy in 1,041 (p10/50/90 3/3/3); without it "
                  "(795) only 120 within 5 blocks (3/78/1053). Time-matched (trap_timematched.json): Oct 10 09-11 h, 400/400 relay pools quick-pulled vs 0/16 non-relay pools; "
                  "before Oct 10 09 h, 11 of 636; from 14 h on, every pool (54/56 non-relay at 17 h, 29/32 at 18 h). So the quick pull started as a reaction to us and became "
                  "the rule; it still comes after the bot's buy, so the front sell (bot buy + 1) beats it in 100%."),
    "front_rule": (fmt_rule(C["v2433_front_all"]) + f"; live window Oct 10 09:07-11:40 UTC: {fmt_rule(C['v2433_front_live_window_0907_1140'])} (live record +13.97% on 405: calibration "
                   f"passes). Bot buy kept (1,614): mean {100*C['v2433_front_bot_buy_kept']['mean']:+.2f}%; dropped because it would revert with our stake ahead (229, mostly after "
                   "Oct 10 12 h): +0.01%. Trades/day here are launches/day in the window (921.8), not the engine's capped 300-400."),
    "follow_rule": fmt_rule(C and v["follow"]) + " (the pull 3 blocks after the bot's buy lands on our hold).",
    "capacity": ("minOut decoded from the bot router calldata (word 4): exactly 0.99 x the launch-state quote (p10/50/90 0.99/0.99/0.99). ETH that can sit ahead from the launch "
                 f"state {C['v2433_cap_from_launch_p10_50_90']}; room left at the chain state after the decoys {C['v2433_room_left_p10_50_90']} (handoff: 0.0122-0.0124)."),
    "engine_config": "live today (front): POSM ac9650d8 1,444 bytes, value 2433328500000000000 wei, fee 2500 ts 50; fire at launch, land +1; sell on the bot router's buy; hold 18.",
    "verdict": "control-known", "candidate_score": 0,
    "notes": "Control. My pricer reproduces the live front (+13.98% vs +13.97% live), and predicts 10,160 real buys from the chain's pre-state with 0 errors > 1e-4."})
fams.append({
    "key": "control:operator-A (known label: launcher 0x3194e32622c5d860a0572c74edda99dcfd8fc827, 77 pools in 67 strict families)", "known": "operator-A", "count": 77,
    "launches_per_day": a["launches_per_day_window"],
    "launcher": "0x3194e326 2fcb9108 from a fresh wallet per launch (77 deployers), values 1.88-2.7 ETH, launch gap p10/50/90 497/2343/44776 blocks.",
    "first_buy": ("first non-launch buy at +3/+3/+4: the dust bot (74/77); first >= 0.0002 ETH = its crowd through Universal Router execute in 75/77 at +24/+54/+66, "
                  "0.0143/0.0547/0.120 ETH, 10 distinct crowd wallets (0x8700722d 25, 0x295877ce 23, 0xdc2e8661 15)."),
    "pull": "66/77 (85.7%) within 3,000 blocks by the launch wallet through the POSM (dd46508f); from launch +51/+224/+2180, from the first crowd buy +6/+165/+2157.",
    "outsiders": "no real-size outsider before the first crowd buy in any pool (dust only: 0xe71a69f4, 0xf7b47b17 6e-5); trap test here not computable (the handoff documents pulls 5-13 blocks after outside buys).",
    "front_rule": fmt_rule(a["front"]) + " (no crowd buy by +20).",
    "follow_rule": fmt_rule(a["follow"]) + " (handoff: OURS-orig +2.9% at hold 2, live +2-4%: consistent).",
    "capacity": "crowd buys through Universal Router execute (nested, not decoded): assumed 0.99 x launch-state quote gives 0.0082/0.0115/0.0173 ETH ahead (assumption).",
    "engine_config": "live today (follow).", "verdict": "control-known", "candidate_score": 0, "notes": "Control for the follow pricer."})
res = {"families": fams, "numbers": {"stats": S, "calib": C, "postwindow": PW, "depth": D, "fam2_extra": {k: v for k, v in X2.items()}, "trap_controls": TC}}
json.dump(res, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)
json.dump({"families": fams}, open(os.path.join(HERE, "families_out.json"), "w"), indent=1)
for x in fams: print(x["key"][:60], "|", x["verdict"], "|", x["front_rule"][:150], "|", x["follow_rule"][:120])
