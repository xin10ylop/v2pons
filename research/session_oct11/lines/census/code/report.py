#!/usr/bin/env python3
"""top40.json (the merged family ranking) and the generated tables of README.md, from build.py's outputs (no RPC)."""
import sys, os, json, collections, statistics as stt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib2 import CEN, CACHE, jget, jl_iter

J = lambda n: json.load(open(os.path.join(CEN, n)))
S = J("summary.json"); FT = J("families_tok.json"); FL = J("families_lc.json"); FF = J("families_fund.json"); FM = J("families_tokm.json")
OV = J("overlap.json"); B = J("bonding.json") if os.path.exists(os.path.join(CEN, "bonding.json")) else None
TIM = jget("timing.json", {})


def jac(a, b):
    a, b = set(a), set(b); return len(a & b) / len(a | b) if a or b else 0


cands = sorted([("tok", f) for f in FT] + [("lc", f) for f in FL], key=lambda x: -x[1]["count"])
top = []
for g, f in cands:
    hit = None
    for e in top:
        if e["grouping"] != g and jac(e["_pools"], f["pools"]) >= 0.8: hit = e; break
    if hit: hit["same_as"].append(f"{g}:{f['key']}"); continue
    if len(top) >= 40: continue
    top.append({"grouping": g, "key": f["key"], "count": f["count"], "per_day": f["per_day"], "frb_off_med": f["frb_off_p10_50_90"][1],
                "first_buy_off_med": f["first_buy_off_med"], "pull_off_med": f["pull_off_p10_50_90"][1], "pulled": f"{f['n_pulled']}/{f['n_with_events']}",
                "outsider_reaction_rate": f["outsider_reaction_rate"], "outsider_reactions": f"{f['outsider_reactions']}/{f['outsider_pools']}",
                "reaction_baseline_rate": f["reaction_baseline_rate"], "reaction_baseline": f"{f['reaction_baseline_quick']}/{f['reaction_baseline_pools']}",
                "outsider12_reaction_rate": f["outsider12_reaction_rate"], "outsider12_reactions": f"{f['outsider12_reactions']}/{f['outsider12_pools']}",
                "baseline12_rate": f["baseline12_rate"], "baseline12": f"{f['baseline12_quick']}/{f['baseline12_pools']}",
                "outsider12_nf_reaction_rate": f["outsider12_nf_reaction_rate"], "outsider12_nf_reactions": f"{f['outsider12_nf_reactions']}/{f['outsider12_nf_pools']}",
                "pull_after_outsider12_med": f["pull_after_outsider12_med"], "outsider12_fp_top": f["outsider12_fp_top"][:2],
                "frb_fp_top": f["frb_fp_top"][:1], "n_deployers": f["n_deployers"], "first_utc": f["first_utc"], "last_utc": f["last_utc"],
                "pull_minus_frb_med": f["pull_minus_frb_med"], "frb_eoa_in_same_tok_family": f"{f['frb_eoa_in_same_tok_family']}/{f['frb_n']}",
                "known_fp": [f"{k} {n}" for k, n in f["known_fp"] if k], "frb_n": f["frb_n"], "desc": f["desc"], "same_as": [], "_pools": f["pools"]})
for e in top: del e["_pools"]
json.dump(top, open(os.path.join(CEN, "top40.json"), "w"), indent=1)


def fmt(v):
    if v is None: return "-"
    if isinstance(v, float): return f"{v:g}"
    return str(v)


L = []
L.append("| # | grouping:key | n | /day | pools with a real buy | first real buy (med off) | first pull (med off) | pulled | pull - frb | early-outsider reaction | same, shared fingerprints excluded | baseline | all-fetched outsider reaction | baseline | frb wallet also in family | known | description |")
L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for k, e in enumerate(top, 1):
    key = e["key"] if len(e["key"]) < 30 else e["key"][:16] + "…" + e["key"][-12:]
    same = f" (= {', '.join(x.split(':')[0] + ':' + x.split(':', 1)[1][:10] for x in e['same_as'])})" if e["same_as"] else ""
    L.append(f"| {k} | `{e['grouping']}:{key}`{same} | {e['count']} | {e['per_day']} | {e['frb_n']} | {fmt(e['frb_off_med'])} | {fmt(e['pull_off_med'])} | {e['pulled']} | "
             f"{fmt(e['pull_minus_frb_med'])} | {e['outsider12_reactions']} | {e['outsider12_nf_reactions']} | {e['baseline12']} | {e['outsider_reactions']} | {e['reaction_baseline']} | {e['frb_eoa_in_same_tok_family']} | {','.join(e['known_fp']) or '-'} | {e['desc'].split('] ', 1)[-1]} |")
TOP_MD = "\n".join(L)

D = ["| dex | pools | quote pairs | with events | with liquidity | with swaps | with real buy | pulled (3,000 blocks) | first pull full | outsider bought | reactions | launch txs | launch wallets | token families | launcher families |",
     "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for d, x in S["per_dex"].items():
    D.append(f"| {d} ({', '.join(f'{k} {v}' for k, v in x['by_quote'].items())}) | {x['pools']} | {x['quote_pairs']} | {x['with_events']} | {x['with_liquidity']} | {x['with_swaps']} | "
             f"{x['with_real_buy']} | {x['with_pull']} | {x['first_pull_full']} | {x['with_outsider_buy']} | {x['outsider_reactions']} | {x['launch_txs']} | {x['launch_wallets']} | {x['tok_families']} | {x['lc_families']} |")
DEX_MD = "\n".join(D)

F = ["| grouping | key | families | >= 5 launches | pools in them | >= 20 | singletons |", "|---|---|---|---|---|---|---|"]
names = {"tok": "token code skeleton (opcodes only)", "tokm": "token code, immutables masked (PUSH32 zeroed, metadata stripped)",
         "tokx": "token code, exact keccak", "lc": "launch target code hash | selector", "strict": "lc | calldata length | fee | tick spacing | hooks",
         "fund": "funding root (sample)", "fund1": "direct funder (sample)"}
for k, v in S["families"].items():
    F.append(f"| {k} | {names.get(k, k)} | {v['all']} | {v['ge5']} | {v['ge5_pools']} | {v['ge20']} | {v['singletons']} |")
FAM_MD = "\n".join(F)

O = ["| A vs B | families of A (>= 5) | >= 90% of A's pools in one B family | A split over >= 3 B families | median B families per A family |", "|---|---|---|---|---|"]
for k, v in OV.items():
    if k.startswith("matrix"): continue
    O.append(f"| {k.replace('_vs_', ' vs ')} | {v['families']} | {v['pure_ge_0.9']} | {v['split_ge_3']} | {fmt(v['median_n_other'])} |")
OV_MD = "\n".join(O)

fs = S["funding_sample"]
FU = []
st_ = collections.Counter(); kinds = collections.Counter(); bb = []; funders = collections.Counter(); fn = []
import itertools
cache_n = 0
for x in itertools.chain(jl_iter("funding.jsonl"), jl_iter("funding_cache.jsonl")):
    cache_n += 1 if x.get("from_cache") else 0
    st_[x["status"]] += 1
    f = x.get("first")
    if f: kinds[f["kind"]] += 1; bb.append(x["first_blocks_before_launch"]); funders[f["funder"]] += 1; fn.append(f["funder_nonce"])
h2 = collections.Counter(x["status"] for x in jl_iter("funding_hop2.jsonl"))
q = lambda v, p: sorted(v)[min(len(v) - 1, int(p * len(v)))] if v else None
FU_MD = (f"Launch wallets with a funding scan: {sum(st_.values())} ({sum(st_.values()) - cache_n} scanned over the RPC, {cache_n} resolved from the cached blocks; status: {dict(st_)}); funding kinds: {dict(kinds)}; blocks before the launch p10/p50/p90: "
         f"{q(bb, .1)}/{q(bb, .5)}/{q(bb, .9)}; funder nonce p10/p50/p90: {q(fn, .1)}/{q(fn, .5)}/{q(fn, .9)}; distinct funders {len(funders)}, "
         f"top: {', '.join(f'{a[:10]} x{n}' for a, n in funders.most_common(6))}. Hop 2 (fresh funders, nonce <= 20): {dict(h2)}. Pools covered (their launch "
         f"wallet sampled): {fs['pools_covered']}, with a funder: {fs['pools_with_funder']}; funding-root families with >= 5 pools: {S['families']['fund']['ge5']}.")
open(os.path.join(CEN, "report_tables.md"), "w").write("\n\n".join([DEX_MD, FAM_MD, OV_MD, FU_MD, TOP_MD]))
print("top", len(top)); print(DEX_MD); print(FAM_MD); print(OV_MD); print(FU_MD)
