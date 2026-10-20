"""Judge 1: the 14:00 UTC launch shape (sqrtP 835109957917073511657837871095390, L 94871533698238694366969). Same operator and router? Same
behaviour? Compared with the line's own launches of Oct 12 07:00-14:54. Read-only, offline (j00/j01 caches)."""
from j02_sim import *
pools, head = load_pools()
J0 = json.load(open(JD("j00_launches.json")))
TXS = {}
for fn in (J("c03_txs.jsonl"), SH("s01_txs_new.jsonl"), JD("j00_txs.jsonl")):
    for l in open(fn):
        t = json.loads(l); TXS[t["hash"]] = t
old_eoa = set()
for fn in (J("c03_txs.jsonl"), SH("s01_txs_new.jsonl")):
    for l in open(fn):
        t = json.loads(l)
        if t["to"] == ROUTER: old_eoa.add(t["from"])
# 1. the launch call: byte diff against a line launch
ref = J0["ref"]["input"]; L1400 = [x for x in J0["launches"] if x["sqrtP"] != SQRTP]
print(f"(1) launch calls: line reference {J0['ref']['pid'][:10]} ({(len(ref) - 2) // 2} bytes); 14:00-shape launches {len(L1400)}")
for x in L1400[:3] + L1400[-1:]:
    a, b = ref[2:], x["input"][2:]
    diff = [i // 64 for i in range(0, min(len(a), len(b)), 64) if a[i:i + 64] != b[i:i + 64]]
    print(f"   {x['pid'][:10]} {(len(b)) // 2} bytes, selector {b[:8]}; 32-byte words that differ from the reference (by index after the selector): {sorted(set(diff))[:30]}")
    for w in sorted(set(diff))[:30]:
        wa, wb = a[8 + 64 * w: 8 + 64 * (w + 1)] if 8 + 64 * w < len(a) else "", b[8 + 64 * w: 8 + 64 * (w + 1)]
        if wa != wb: print(f"      w{w:3d} line {wa}  14:00 {wb}")
    break
# 2. who: launch wallets, pulls, the router, the router's EOAs, the dust bots
def rows(sel):
    out = []
    for p in sel:
        rb = [s for s in p["sw"] if s["buy"] and s["cls"] == "router"]
        eo = {TXS[s["tx"]]["from"] for s in rb if s["tx"] in TXS}
        sel_ok = all(TXS[s["tx"]]["sel"] == "e6cb474f" for s in rb if s["tx"] in TXS)
        k0, T = engine_T(dict(p, sw=[s for s in p["sw"] if s["cls"] != "ours"]), 400)
        T = T if k0 is not None else None
        e60 = sum(s["eth"] for s in rb if T is not None and T <= s["off"] <= T + 60)
        dust = sorted({s["from"][:10] for s in p["sw"] if s["buy"] and s["cls"] == "recurring" and s["off"] <= 10})
        hold = [s for s in p["sw"] if s["buy"] and s["cls"] in ("recurring", "oneoff") and s["eth"] >= 0.001 and (T is None or s["off"] <= T + 62)]
        out.append({"pid": p["pid"][:10], "ts": p["ts"], "shape": p["shape"], "T": T, "T_eth": next((s["eth"] for s in rb if T is not None and s["off"] == T), None),
                    "rb": len(rb), "eoa": len(eo), "eoa_known": len(eo & old_eoa), "sel_ok": sel_ok, "e60": e60, "pull": p["pull"], "pull_by_launcher": (p["pull_tx"] or {}).get("from") == p["launcher"],
                    "pull_via_posm": (p["pull_tx"] or {}).get("to") == POSM, "dust_by_L+10": dust, "holders": [(s["from"][:10], round(s["eth"], 4), s["off"] - (T or 0)) for s in hold]})
    return out
recent = [p for p in pools if p["ts"] >= 1791794400]     # Oct 12 07:00 UTC
for shape in ("1400", "line"):
    R = rows([p for p in recent if p["shape"] == shape])
    print(f"\n(2) shape {shape}, launched Oct 12 07:00-14:54: {len(R)} pools")
    if shape == "1400" or True:
        for r in sorted(R, key=lambda r: r["ts"])[-12 if shape == "line" else None:]:
            print(f"   {utc(r['ts'])} {r['pid']} T {str(r['T']):>4s} ({r['T_eth']}) router buys {r['rb']:3d} by {r['eoa']} EOAs ({r['eoa_known']} seen before 14:14), e6cb474f {r['sel_ok']}, "
                  f"router ETH T..T+60 {r['e60']:.3f}; pull L+{r['pull']} by launcher {r['pull_by_launcher']} via PosM {r['pull_via_posm']}; dust by L+10 {r['dust_by_L+10']}; holders {r['holders']}")
    Ts = sorted(r["T"] for r in R if r["T"] is not None); pulls = sorted(r["pull"] for r in R if r["pull"] is not None)
    print(f"   T: n {len(Ts)} median {pct(Ts, .5)} range {Ts[:1]}..{Ts[-1:]}; router ETH T..T+60 median {pct([r['e60'] for r in R if r['T'] is not None], .5):.3f}; "
          f"pull age median {pct(pulls, .5)} min {pulls[:3]}; unpulled {sum(1 for r in R if r['pull'] is None)}")
# 3. launch wallets of the 14:00 shape: fresh? (nonce of the launch tx)
print("\n(3) launch wallets: nonce of the launch transaction (fresh wallets launch at nonce 0..2)")
txl = rpc.batch("eth_getTransactionByHash", [[x["tx"]] for x in J0["launches"]])
for x, t in zip(J0["launches"], txl):
    print(f"   {utc(x['ts'])} {x['pid'][:10]} shape {'1400' if x['sqrtP'] != SQRTP else 'line'} launcher {x['from']} nonce {int(t['nonce'], 16)} gasPrice {int(t['gasPrice'], 16) / 1e9:.4f} gwei")
# 4. the engine-exact replay on the 14:00 shape, as if it were armed (pin false or a second fingerprint)
stake = 2 * 10 ** 15
print("\n(4) the 14:00 shape replayed with the engine's fills (its own launch sqrtP and L), max_blocks 400 and 100:")
for mb in (400, 100):
    R = run([p for p in pools if p["shape"] == "1400"], stake, mb)
    for r in R:
        print(f"   mb {mb} {r['pid'][:10]} T +{r['T']} {'FILL' if r['fill'] else 'rev (' + format(r.get('short', 0), '+.2%') + ')'} pull@buy+{r['pull_after_buy']}"
              + ("  " + "  ".join(f"{k} {r['res'][k][0]:+.2%}" for k in ("hold 20", "hold 25", "hold 30", "hold 60", "tp 4% cap 30")) if r["fill"] else ""))
    v = [usd(r, "hold 30", stake) for r in R]
    print(f"   mb {mb}: attempts {len(R)}, fills {sum(r['fill'] for r in R)}, hold 30 $/attempt {sum(v) / max(1, len(v)):+.3f} [{boot(v)[0]:+.3f}, {boot(v)[1]:+.3f}]")
print("rpc", rpc.STATS)
