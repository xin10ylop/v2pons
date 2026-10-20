"""Skeptic step 5: identity. The bot-buy wallets and launch wallets of v3.0/v5.0 vs the v2.433 family's (same census), operator A's
addresses (HANDOFF 1, money/loop.json), the outsiders' presence elsewhere in the census; time overlap of v3.0 launches with v2.433 launches."""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
HERE = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/skeptic_0x58daec3116aae6d93017baaea7749052e8a04f"
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
P = load_pools(); F = load_families(); T = load_txs()
rows = json.load(open(HERE + "/rows.json"))
K2433 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true"
p2433 = set(F[K2433]["pids"])
# bot-buy wallets and launch wallets per family from txs.jsonl refs
def fam_wallets(pids):
    bot, launch, pull = set(), set(), set()
    for t in T.values():
        for pid, kind, rank in t.get("refs") or []:
            if pid in pids:
                if kind == "swap" and t["to"] == ROUTER and t["selector"] == "c1120e3d": bot.add(t["from"])
                if kind == "launch": launch.add(t["from"])
                if kind == "pull": pull.add(t["from"])
    return bot, launch, pull
v3 = {r["pid"] for r in rows if r["sub"] == "v3.0"}; v5 = {r["pid"] for r in rows if r["sub"] == "v5.0"}
b3, l3, u3 = fam_wallets(v3); b5, l5, u5 = fam_wallets(v5); b2, l2, u2 = fam_wallets(p2433)
loop = json.load(open("/home/user/v2pons/research/session_oct9_10/money/loop.json"))
opA = set(a.lower() for k in ("crowd", "disp", "sweeps") for a in loop[k]) | set(a.lower() for c in loop["chains"] for a in c)
opA |= {"0x3194e32622c5d860a0572c74edda99dcfd8fc827", "0x3b11cafa6b570e3bc75bb6529b16dd35fe4b64b5"}
out = {"v3.0": {"bot_wallets": len(b3), "launch_wallets": len(l3)}, "v5.0": {"bot_wallets": len(b5), "launch_wallets": len(l5)}, "v2.433": {"bot_wallets": len(b2), "launch_wallets": len(l2)},
       "bot_wallets_v3_and_v2433": len(b3 & b2), "bot_wallets_v5_and_v2433": len(b5 & b2), "bot_wallets_v3_and_v5": len(b3 & b5),
       "launch_wallets_v3_and_v2433": len(l3 & l2), "launch_wallets_v5_and_v2433": len(l5 & l2),
       "launch_wallet_also_bot_buyer_any": len((l3 | l5) & (b2 | b3 | b5)),
       "opA_overlap": len((b3 | b5 | l3 | l5) & opA), "n_opA_addrs": len(opA)}
# reused launch wallets: nonce 257-268 in v3.0; do the same wallets launch v2.433 too?
reused = [r for r in rows if r["sub"] == "v3.0" and r["nonce"] > 3]
out["v3_reused_launch_wallets"] = len(set(r["from"] for r in reused))
# the same wallet across families: does a wallet launch both a v3.0 and a v2.433 pool (by from)
fr2433 = collections.Counter(P[p]["launch_from"] for p in p2433)
out["v3_launch_from_seen_in_v2433"] = sum(1 for r in rows if r["sub"] == "v3.0" and r["from"] in fr2433)
# outsiders elsewhere in the census (any pool, as a tx from in the first 8 swaps)
OUT = ["0xfeda1c58462150b4cb94c63efce3647e78f883eb", "0x9a12867607c191a7191c08e3d8dea7018e277416", "0x9f3b9a449dfaa2fdfb4dd5e1d8c47b9f12d051ea"]
fam_of = {pid: P[pid]["family"] for pid in P}
for w in OUT:
    c = collections.Counter(); first = None; last = None
    for t in T.values():
        if t["from"] == w:
            for pid, kind, rank in t.get("refs") or []:
                c[(fam_of.get(pid, "?")[:60], kind, "buy" if t["value_wei"] else "")] += 1
            first = min(first or t["bn"], t["bn"]); last = max(last or 0, t["bn"])
    out["outsider " + w] = {"refs": c.most_common(8), "first_bn": first, "last_bn": last}
# v2.433 overlap in time: for each v3.0 launch, is a v2.433 launch within [b0-25, b0+12] (one engine slot)
b2433 = sorted(P[p]["launch_block"] for p in p2433)
import bisect
def near(b, lo, hi):
    i = bisect.bisect_left(b2433, b + lo); return i < len(b2433) and b2433[i] <= b + hi
out["v3_with_v2433_launch_in_slot"] = sum(1 for r in rows if r["sub"] == "v3.0" and near(r["b0"], -12, 12))
out["v3_count"] = len(v3)
# bursts: is v3.0 interleaved with v2.433 by hour
by = collections.defaultdict(lambda: [0, 0])
for r in rows:
    if r["sub"] == "v3.0": by[(r["ts"] // 3600)][0] += 1
for p in p2433: by[P[p]["launch_ts"] // 3600][1] += 1
hrs = sorted(by)
out["hours_v3_only"] = sum(1 for h in hrs if by[h][0] and not by[h][1]); out["hours_v2433_only"] = sum(1 for h in hrs if by[h][1] and not by[h][0]); out["hours_both"] = sum(1 for h in hrs if by[h][0] and by[h][1])
print(json.dumps(out, indent=1))
json.dump(out, open(HERE + "/s5_identity.json", "w"), indent=1)
