#!/usr/bin/env python3
"""opfee0.py DAYS: who runs the fee-0 launch family (fee 0, tick spacing 60, no hook, launch sqrtP 2505036234966386302045715536678303)?

Without archive state or an explorer, from logs and current state:
  launchers   each launch transaction's sender, target contract and value; senders reused or single-use (current nonce); whether the
              target was created by the sender itself (CREATE address from the sender and a recent nonce) and the targets' code
  the launch  which contract makes the launch-block buys (the PoolManager's swap sender), and the launcher's later sells and pulls in its own
              pool (ETH it takes back out)
  the crowd   Universal Router buyers resolved to their wallets; how many recur (3+ pools); and how many of them also buy in the 2.433
              operator's 3.0 / 5.0 ETH families and operator A's 1,380 B line over the last day (a shared bot fleet = a shared operator)
Read-only."""
import os, sys, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib as H, watchfee0 as W
from eth_utils import keccak
import rlp

DAYS = float(sys.argv[1]) if len(sys.argv) > 1 else 3
url = W.url; head = int(H.rpc(url, "eth_blockNumber", []), 16)
FAM = (0, 60, 2505036234966386302045715536678303)
OTHER = {"2.433 op 3.0 ETH": (10000, 200, 679394651928963067279918579724198), "2.433 op 5.0 ETH": (10000, 200, 526364174002223567019744861584709),
         "op A 5.6 ETH tier": (1, 1, 3543191142285917749113176609134040)}


def pools_of(key, hours):
    init = W.getlogs(head - int(hours * 36000), head - 3000, [W.T_INIT4], W.PM)
    return [(l["topics"][1], int(l["blockNumber"], 16), l["transactionHash"]) for l in init if l["topics"][2] == "0x" + "0" * 64
            and int(l["data"][2:][128 + 24:192], 16) == 0 and (int(l["data"][2:][0:64], 16), H.i256(l["data"][2:][64:128]), int(l["data"][2:][192:256], 16)) == key]


def batch_tx(hashes):
    out = {}
    hs = sorted(set(hashes))
    for i in range(0, len(hs), 2000):
        g = hs[i:i + 2000]
        for h, x in zip(g, H.batch(url, [("eth_getTransactionByHash", [h]) for h in g], size=50, workers=4, tries=8)):
            out[h] = x
    return out


def create_addr(sender, nonce):
    return "0x" + keccak(rlp.encode([bytes.fromhex(sender[2:]), nonce]))[12:].hex()


def ur_buyers(pools, win=3000):
    """wallets buying through the Universal Router in the pools' first `win` blocks, per pool"""
    per = {}; hashes = []
    for pid, bn, _ in pools:
        sw = [s for s in W.getlogs(bn, bn + win, [W.T_SWAP4, pid], W.PM) if s["topics"][2].endswith(W.UR[2:]) and W.sg(s["data"][2:66]) < 0]
        per[pid] = sw; hashes += [s["transactionHash"] for s in sw]
    txs = batch_tx(hashes)
    return {pid: {(txs.get(s["transactionHash"]) or {}).get("from", "").lower() for s in sw} - {""} for pid, sw in per.items()}


fam = pools_of(FAM, DAYS * 24)
print(f"fee-0 family, last {DAYS:g} days: {len(fam)} launches", flush=True)
ltx = batch_tx([t for _, _, t in fam])
senders = collections.Counter(); targets = []; values = collections.Counter(); self_created = 0; codes = collections.Counter()
for pid, bn, h in fam:
    t = ltx.get(h)
    if not t:
        continue
    s = t["from"].lower(); to = (t.get("to") or "").lower(); n = int(t["nonce"], 16)
    senders[s] += 1; values[round(int(t["value"], 16) / 1e18, 2)] += 1; targets.append(to)
    if any(create_addr(s, k) == to for k in range(max(0, n - 6), n)):
        self_created += 1
for to in targets[:40]:
    c = H.rpc(url, "eth_getCode", [to, "latest"])
    codes[(keccak(bytes.fromhex(c[2:])).hex()[:12] if len(c) > 2 else "none", (len(c) - 2) // 2)] += 1
print(f"  launch senders: {len(senders)} distinct for {sum(senders.values())} launches; reused: {sum(1 for n in senders.values() if n > 1)} (top {senders.most_common(3)})")
cur = {s: int(H.rpc(url, "eth_getTransactionCount", [s, "latest"]), 16) for s in list(senders)[:40]}
print(f"  their nonces now: median {st.median(cur.values()) if cur else '-'}, max {max(cur.values()) if cur else '-'} (small = near single-use wallets)")
print(f"  launch values (ETH): {values.most_common(5)}")
print(f"  launch target created by its own sender in the few txs before the launch: {self_created}/{len(targets)}")
print(f"  target contract code (sample of {min(40, len(targets))}): {codes.most_common(4)}")
# launch-block buys and the launcher's later exits, on a sample
devr = collections.Counter(); taken = []; pulls_by = collections.Counter()
for pid, bn, h in fam[-12:]:
    t = ltx.get(h); s = t["from"].lower() if t else None
    sw = W.getlogs(bn, bn + 6000, [W.T_SWAP4, pid], W.PM); ml = W.getlogs(bn + 1, min(head, bn + 72000), [W.T_ML, pid], W.PM)
    for x in sw:
        if int(x["blockNumber"], 16) == bn:
            devr["0x" + x["topics"][2][26:]] += 1
    stx = batch_tx([x["transactionHash"] for x in sw if W.sg(x["data"][2:66]) > 0] + [m["transactionHash"] for m in ml])
    out_eth = sum(W.sg(x["data"][2:66]) for x in sw if W.sg(x["data"][2:66]) > 0 and (stx.get(x["transactionHash"]) or {}).get("from", "").lower() == s) / 1e18
    taken.append(out_eth)
    for m in ml:
        if W.sg(m["data"][2 + 128:2 + 192]) < 0:
            pulls_by["launcher" if (stx.get(m["transactionHash"]) or {}).get("from", "").lower() == s else (stx.get(m["transactionHash"]) or {}).get("from", "?")[:10]] += 1
print(f"  launch-block buys made through: {devr.most_common(3)}")
print(f"  ETH the launcher sold back out of its own pool in 6,000 blocks (last 12 launches): {[round(x, 3) for x in taken]}")
print(f"  liquidity pulls within 2 h, by: {dict(pulls_by)}")
# the crowd, and overlap with other operators' crowds
fb = ur_buyers(fam)
cnt = collections.Counter(w for ws in fb.values() for w in ws); crowd = {w for w, n in cnt.items() if n >= 3}
print(f"\n  crowd: {len(cnt)} Universal Router buyers, {len(crowd)} in 3+ of the family's pools", flush=True)
for name, key in OTHER.items():
    ps = pools_of(key, 24)
    ob = ur_buyers(ps[:120])
    ow = set().union(*ob.values()) if ob else set()
    print(f"  {name}: {len(ps)} pools in 24 h, {len(ow)} UR buyers; shared with the fee-0 crowd: {len(ow & crowd)} (of the fee-0 family's {len(crowd)} recurring wallets)", flush=True)
