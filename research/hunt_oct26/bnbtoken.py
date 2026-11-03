#!/usr/bin/env python3
"""bnbtoken.py: how BNB's 4,050 B crowd token decides a transfer, and the line's timeline pool by pool (Nov 2, out/line_bnb_full.json).

1. The rule, from the token's own code run by minievm.py on its real storage (no sends): a buy (the pair sends), a sell (to the pair) and a
   move (wallet to wallet), by a team wallet and an outsider, at gas price 0 / 0.1 gwei, with block.coinbase set / 0, inside the lock
   window, after it, and before the token's pose (the window's start).
2. The timeline of every pool from the token's events: TeamSet (0x03b34e9b) for the crew, Moored (0xea08d792: the pair registered),
   Posed (0x1865bbf6: the lock window starts, 7 days), the crowd's first real buy (0.05 BNB+), the LP burn; and every outsider's buy and
   whether it sold. Read-only."""
import os, sys, json, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib as H
from minievm import EVM
from eth_utils import keccak

HERE = os.path.dirname(os.path.abspath(__file__))
T_TEAM, T_MOOR, T_POSE = "0x03b34e9b", "0xea08d792", "0x1865bbf6"
ad = lambda a: "0" * 24 + a[2:]
K = int("5a" * 32, 16)                                   # slot 8 (flag | horizon) is stored XOR this 32-byte constant from the code


def rule(tok, pair, outsider, team):
    e = EVM("bnb", tok); dec = e.sload_chain(8) ^ K; horizon = dec & ((1 << 255) - 1)
    bal = lambda a: int.from_bytes(keccak(bytes.fromhex(ad(a)) + (0).to_bytes(32, "big")), "big")
    rnd = "0x" + "ab" * 20; ov = {bal(team): 10 ** 24, bal(pair): 10 ** 24, bal(outsider): 10 ** 24}
    CB = "0x" + "11" * 20; now = horizon - 86400
    print(f"token {tok}: pair {pair}, lock window ends {horizon} (pose + 7 days)")
    cases = [("buy (the pair sends to an outsider)", pair, outsider, {}), ("sell by an outsider", outsider, pair, {}),
             ("sell by an outsider, gas price 0", outsider, pair, {"gasprice": 0}), ("sell by an outsider, coinbase 0", outsider, pair, {"coinbase": 0}),
             ("move outsider -> wallet", outsider, rnd, {}), ("move outsider -> wallet, gas price 0", outsider, rnd, {"gasprice": 0}),
             ("sell by a team wallet", team, pair, {}), ("move team -> wallet", team, rnd, {}),
             ("sell by an outsider after the window", outsider, pair, {"timestamp": horizon + 1}),
             ("sell by an outsider before pose (window unset)", outsider, pair, {"over": {8: K}})]
    for label, frm, to, kw in cases:
        o = dict(ov); o.update(kw.pop("over", {}))
        env = dict(gasprice=10 ** 8, coinbase=CB, timestamp=now); env.update(kw)
        r = e.run("0xa9059cbb" + ad(to) + format(10 ** 18, "064x"), sender=frm, overrides=o, **env)
        print(f"   {label:48s} {'REVERT ' + r['revert'].hex()[:8] + (' Hush()' if r['revert'].hex().startswith('1887aac7') else '') if r['revert'] is not None else 'OK'}")


def main():
    d = json.load(open(os.path.join(HERE, "out/line_bnb_full.json")))
    p0 = next(q for q in d["pools"] if q["id"].startswith("v2:0x8778fbb"))
    rule(p0["tok"], p0["id"][3:], next(e[6] for e in p0["ev"] if e[6].startswith("0xf7093a4d")), "0xc0c84518ced6a61d2a4f4a50bc0f438e0cb1031b")
    print("\npool          launch  team set  moor  pose  crowd 0.05+  LP burn   outsiders (offset, BNB, sold BNB)")
    agg = {"team": [], "moor": [], "pose": [], "crowd": [], "burn": []}
    crew = set()
    for p in d["pools"]:
        L = H.logs("bnb", p["bn"] - 200, p["bn"] + 200, [], p["tok"])
        team = [int(x["blockNumber"], 16) - p["bn"] for x in L if x["topics"][0].startswith(T_TEAM)]
        for x in L:
            if x["topics"][0].startswith(T_TEAM):
                crew.add("0x" + x["topics"][1][26:])
        moor = [int(x["blockNumber"], 16) - p["bn"] for x in L if x["topics"][0].startswith(T_MOOR)]
        pose = [int(x["blockNumber"], 16) - p["bn"] for x in L if x["topics"][0].startswith(T_POSE)]
        p["_team"], p["_moor"], p["_pose"] = team, moor, pose
    for p in d["pools"]:
        crowd = min((e[0] for e in p["ev"] if e[2] >= 0.05 and e[6] in crew), default=None)
        outs = {}
        for e in p["ev"]:
            if e[6] in crew or e[6] == p["launcher"] or abs(e[2]) < 0.001:
                continue
            o = outs.setdefault(e[6], [None, 0.0, 0.0])
            if e[2] > 0:
                o[0] = o[0] if o[0] is not None else e[0]; o[1] += e[2]
            else:
                o[2] += -e[2]
        row = [(o[0], round(o[1], 3), round(o[2], 3)) for o in outs.values() if o[0] is not None]
        for k, v in (("team", min(p["_team"], default=None)), ("moor", min(p["_moor"], default=None)), ("pose", min(p["_pose"], default=None)), ("crowd", crowd), ("burn", p["burn"])):
            if v is not None:
                agg[k].append(v)
        print(f"{p['id'][:12]}  {p['bn']}  {min(p['_team'], default='-')!s:>5}  {min(p['_moor'], default='-')!s:>5} {min(p['_pose'], default='-')!s:>5}  {crowd!s:>8}  {p['burn']!s:>8}   {row}")
    print("\nmedians (blocks after the launch, 0.45 s each): " + ", ".join(f"{k} {st.median(v):g} ({min(v)}..{max(v)})" for k, v in agg.items() if v))
    print(f"team wallets across the line: {len(crew)}")


if __name__ == "__main__":
    main()
