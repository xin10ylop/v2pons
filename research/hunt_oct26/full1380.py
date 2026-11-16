#!/usr/bin/env python3
"""full1380.py: the 1,380 B line's outsider pools followed for 4 hours: every swap with its EOA, the liquidity pulls, and what each
outsider did (sold? when? return?). Pools listed in react1380_nov.out. Read-only, RH RPC."""
import sys, json, os, collections, re
import hlib as H
from eth_utils import keccak
HERE = os.path.dirname(os.path.abspath(__file__)); url = H.CH["rh"]["rpc"]; PM = H.CH["rh"]["pm"]
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
T_SWAP4 = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
sg = lambda h: (lambda x: x - (1 << 256) if x >= 1 << 255 else x)(int(h, 16))
allp = {}
for f in ("out/dump_rh_nov1011.json", "out/dump_rh_nov1415.json"):
    allp.update(json.load(open(f))["pools"])
short = re.findall(r"^\s+(v4:0x[0-9a-f]+) \+(\d+)\s+\S+\s+([0-9.]+)", open("react1380_nov.out").read(), re.M)
SPAN = 144000                                                                      # 4 hours at 10 blocks/s
for sid, off, eth in short:
    pid = next(k for k in allp if k.startswith(sid)); p = allp[pid]; bn = p["bn"]
    sw, ml = [], []
    for a in range(bn, bn + SPAN, 25000):
        b = min(bn + SPAN, a + 24999)
        sw += H.rpc(url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(b), "address": PM, "topics": [T_SWAP4, pid[3:]]}]) or []
        ml += H.rpc(url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(b), "address": PM, "topics": [T_ML, pid[3:]]}]) or []
    hs = sorted({x["transactionHash"] for x in sw})
    frm = {h: (x["from"].lower() if x else None) for h, x in zip(hs, H.batch(url, [("eth_getTransactionByHash", [h]) for h in hs], size=50, workers=4, tries=8))}
    pulls = [int(m["blockNumber"], 16) - bn for m in ml if sg(m["data"][2 + 128:2 + 192]) < 0]
    ev = []
    for x in sw:
        d = x["data"][2:]; a0 = sg(d[0:64]); a1 = sg(d[64:128]); snd = "0x" + x["topics"][2][26:]
        w = frm.get(x["transactionHash"]) if snd == UR else snd
        ev.append((int(x["blockNumber"], 16) - bn, -a0 / 1e18, a1, w))     # native in (+buy), token out (+buy)
    ev.sort()
    o = next(e for e in ev if e[0] == int(off) and abs(e[1] - float(eth)) < 1e-4)
    w = o[3]; mine = [e for e in ev if e[3] == w]
    nin = sum(e[1] for e in mine if e[1] > 0); nout = sum(-e[1] for e in mine if e[1] < 0)
    tb = sum(e[2] for e in mine if e[1] > 0); ts = sum(-e[2] for e in mine if e[1] < 0)
    last = ev[-1][0] if ev else None
    print(f"{sid} outsider {w[:10]} in +{off} {float(eth):.4f} | its trades {[(e[0], round(e[1], 4)) for e in mine][:6]}"
          f" | sold {ts / tb if tb else 0:.0%} for {nout:.4f} ({(nout / nin - 1) if nin else 0:+.0%}) | pulls {pulls[:3]} | swaps {len(ev)}, last at +{last}")
