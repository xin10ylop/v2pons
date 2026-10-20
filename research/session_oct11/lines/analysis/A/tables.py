"""Markdown tables for REPORT.md from groups.json, groups_value.json, spectrum.json -> tables.md"""
import json
G = json.load(open("groups.json")); V = json.load(open("groups_value.json")); SP = json.load(open("spectrum.json"))
out = []
def fmt(x): return "-" if x is None else (f"{x:g}" if isinstance(x, (int, float)) else str(x))
def p(v): return "/".join(fmt(None if a is None else round(a, 4)) for a in v)
HDR = "| key | n | per day d0..d6 | wallets | nonce p10/50/90 | fresh (nonce<=3) | any buy | frb | frb off p10/50/90 | frb ETH p10/50/90 | frb top fingerprint (n) | frb EOAs | frb repeat (>=3 pools) / also in lc fam | pulled | pull off p10/50/90 | pull<frb | pull via | early-outsider reaction nf | baseline |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
def row(key, s):
    fpt = s["frb_fp_top"][0] if s["frb_fp_top"] else ["-", 0]
    pv = s["pull_via"][0] if s["pull_via"] else ["-", 0]
    return (f"| {key} | {s['n']} | {' '.join(str(x) for x in s['per_day'])} | {s['wallets']} | {p(s['nonce_p10_50_90'])} | {s['fresh_le3']} | {s['any_buy']} | {s['frb_share']} | {p(s['frb_off_p'])} | {p(s['frb_eth_p'])} | "
            f"{fpt[0]} ({fpt[1]}) | {s['frb_eoa_distinct']} | {s['frb_repeat_ge3']} / {s['frb_also_lc']} | {s['pulled_share']} | {p(s['pull_off_p'])} | {s['pull_before_frb']} | {pv[0]} ({pv[1]}) | {s['o12_nf_reaction']} | {s['baseline12']} |")
out.append("### Exact launch shape (value wei, calldata len, fee, tick spacing, sqrt_p0, mint L, quote, hook-free): every group with >= 15 launches\n")
out.append(HDR)
for s in G["shape"]:
    k = eval(s["key"]); key = f"{k[0]} wei, {k[1]} B, {k[2]}/{k[3]}, sqrt {str(k[4])[:8]}.., L {str(k[5])[:8]}.., {k[6]}, {'no hook' if k[7] else 'HOOK'}"
    out.append(row(key, s))
out.append("\n### Engine view: (value wei, calldata len, fee, tick spacing, quote, hook-free), any price/liquidity: every group with >= 15 launches and a first-real-buy share >= 5% (the other groups are listed after)\n")
out.append(HDR.replace("| key |", "| key (distinct sqrt,L) |"))
rest = []
for s in V["value_shape"]:
    k = eval(s["key"]); key = f"{k[0]} wei, {k[1]} B, {k[2]}/{k[3]}, {k[4]}, {'no hook' if k[5] else 'HOOK'} ({s['n_price_liq']})"
    if s["frb_share"] >= 0.05: out.append(row(key, s))
    else: rest.append(f"{key}: n {s['n']}, wallets {s['wallets']}, frb {s['frb_share']}, pulled {s['pulled_share']}")
out.append("\nGroups with a first-real-buy share below 5% (no buyer to trade with): " + "; ".join(rest))
out.append("\n### Token-code skeleton (fam.tok) within the non-vbot launches: every family with >= 15 launches\n")
out.append(HDR)
for s in G["tok"]: out.append(row(s["key"][:12], s))
out.append("\n### Launch wallet: the 15 largest of the 124 wallets with >= 15 launches (none has a first-real-buy share >= 20%)\n")
out.append(HDR)
for s in G["wallet"][:15]: out.append(row(s["key"][:12], s))
import collections as C
fs = C.Counter(round(s["frb_share"], 1) for s in G["wallet"])
out.append(f"\nAll 124 wallet groups: first-real-buy share distribution {dict(fs)}; median launch nonce of these wallets: " + str(sorted(s['nonce_p10_50_90'][1] for s in G['wallet'])[62]))
out.append("\n### msg.value spectrum of the whole launcher family (vbot included; 21,018 pools, quote pairs excluded): top 40 exact values\n")
out.append("| value (ETH) | pools | of which non-vbot |\n|---|---|---|")
nv = dict(SP["spec_nonvbot"])
for v, n in SP["spec_all"][:40]: out.append(f"| {v} | {n} | {nv.get(v, 0)} |")
out.append(f"\nDistinct exact values: {len(SP['spec_all'])} (non-vbot {len(SP['spec_nonvbot'])}). Non-vbot by decade: {json.dumps(SP['decades_nonvbot'])}.")
out.append("\n1,444-byte ETH hook-free non-vbot launches by value (top 25): " + ", ".join(f"{v} x{n}" for v, n in SP["spec_1444_eth_nohook"][:25]))
open("tables.md", "w").write("\n".join(out) + "\n")
print(len(out), "lines")
