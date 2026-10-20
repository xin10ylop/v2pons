#!/usr/bin/env python3
"""line_adapt regime: hour by hour (UTC) for the v3.0 and v5.0 lines, from data/rec.json -> regime.json, regime.txt
bot = a buy through the router 0x1cbaf24d with c1120e3d; its first buy's offset, size, minOut (word 4) / the launch-state quote of its size;
the ETH bought ahead of it; the pull (first negative ModifyLiquidity): early (before any bot buy), its offset, the buys before it;
the pull's delay after the bot's first buy."""
import sys, os, json, time, collections, statistics as st
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"


def q(v, ps=(10, 50, 90)):
    if not v: return None
    v = sorted(v)
    return [v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))] for p in ps]


def pool_facts(r):
    sw = r["swaps"]; pull = r["pull"]
    bots = [s for s in sw if s["bot"] and s["side"] == "B"]
    fb = bots[0] if bots else None
    pk = (pull["off"], pull["li"]) if pull else (10 ** 9, 0)
    fk = (fb["off"], fb["li"]) if fb else (10 ** 9, 0)
    early = pull is not None and pk < fk
    lim = min(pk, fk)
    pre = [s for s in sw if (s["off"], s["li"]) < lim]
    pre_b = [s for s in pre if s["side"] == "B"]
    f = {"pid": r["pid"], "fam": r["fam"], "b0": r["b0"], "ts0": r["ts0"], "hour": time.strftime("%m-%d %H", time.gmtime(r["ts0"])), "nonce": r["nonce"], "from": r["from"],
         "bot_off": fb["off"] if fb else None, "bot_eth": -fb["a0"] / 1e18 if fb else None, "bot_from": fb["from"] if fb else None,
         "n_bot": len(bots), "bot_offs": [s["off"] for s in bots][:12],
         "pull_off": pull["off"] if pull else None, "pull_from_launcher": (pull["from"] == r["from"]) if pull and pull["from"] else None,
         "pull_sel": pull["sel"] if pull else None, "early_pull": early,
         "pre": [(s["off"], s["side"], round(abs(s["a0"]) / 1e18, 7), (s["to"] or "?")[:10], (s["from"] or "?")[:10]) for s in pre],
         "eth_ahead": sum(-s["a0"] for s in pre_b) / 1e18, "eth_ahead_nondust": sum(-s["a0"] for s in pre_b if s["from"] != DUST) / 1e18,
         "net_ahead": sum(-s["a0"] for s in pre) / 1e18,
         "outsider_pre": [(s["off"], round(-s["a0"] / 1e18, 7), (s["from"] or "?")[:10]) for s in pre_b if s["from"] != DUST]}
    if fb:
        q0 = v4math.buy_out_int(r["sp0"], r["L0"], -fb["a0"], r["fee"])
        f["minout_ratio"] = fb["minout"] / q0 if q0 else None
        # the room: the most ETH that can sit ahead of the bot's first buy (from launch state) before it reverts
        lo, hi = 0, int(1e18)
        while hi - lo > int(1e13):
            m = (lo + hi) // 2
            sp = int(v4math.sqrt_after_buy(r["sp0"], r["L0"], m - (m * r["fee"] + 999_999) // 1_000_000))
            if v4math.buy_out_int(sp, r["L0"], -fb["a0"], r["fee"]) >= fb["minout"]: lo = m
            else: hi = m
        f["room_eth"] = lo / 1e18
        f["pull_minus_bot"] = (pull["off"] - fb["off"]) if pull and not early else None
    return f


def summarize(F):
    n = len(F)
    bo = [f["bot_off"] for f in F if f["bot_off"] is not None]
    ep = [f for f in F if f["early_pull"]]
    nob = [f for f in F if f["bot_off"] is None]
    pmb = [f["pull_minus_bot"] for f in F if f.get("pull_minus_bot") is not None]
    return {"n": n, "bot_off_p10_50_90": q(bo), "bot_off_min_max": [min(bo), max(bo)] if bo else None, "no_bot": len(nob), "no_bot_frac": round(len(nob) / n, 3) if n else None,
            "early_pull": len(ep), "early_pull_frac": round(len(ep) / n, 3) if n else None, "early_pull_offs": sorted(f["pull_off"] for f in ep),
            "early_pull_with_outsider_before": sum(1 for f in ep if f["outsider_pre"]),
            "early_pull_outsiders": [f["outsider_pre"] for f in ep if f["outsider_pre"]][:12],
            "pulled_within_1200": sum(1 for f in F if f["pull_off"] is not None), "pull_minus_bot_p10_50_90": q(pmb), "pull_minus_bot_min": min(pmb) if pmb else None,
            "bot_eth_p10_50_90": [round(x, 4) for x in q([f["bot_eth"] for f in F if f["bot_eth"]])] if bo else None,
            "minout_ratio_min_med_max": [round(x, 5) for x in q([f["minout_ratio"] for f in F if f.get("minout_ratio")], (0, 50, 100))] if bo else None,
            "room_eth_min_p10_med": [round(x, 4) for x in q([f["room_eth"] for f in F if f.get("room_eth")], (0, 10, 50))] if bo else None,
            "eth_ahead_p50_p90_max": [round(x, 5) for x in q([f["eth_ahead"] for f in F], (50, 90, 100))],
            "with_outsider_ahead": sum(1 for f in F if f["outsider_pre"]),
            "bot_buys_per_pool_p50": q([f["n_bot"] for f in F], (50,))[0]}


def main():
    R = json.load(open(os.path.join(D, "rec.json")))
    F = [pool_facts(r) for r in R if r["complete"]]
    json.dump(F, open(os.path.join(D, "facts.json"), "w"))
    out = {}; lines = []
    for fam in ("v3.0", "v5.0"):
        G = [f for f in F if f["fam"] == fam]
        out[fam] = {"all": summarize(G), "hours": {}}
        lines.append(f"\n=== {fam}: {len(G)} launches, all: {json.dumps(out[fam]['all'])[:1500]}")
        by = collections.defaultdict(list)
        for f in G: by[f["hour"]].append(f)
        lines.append(f"{'hour':9s} {'n':>3s} {'bot p10/50/90':>15s} {'nobot':>5s} {'early':>5s} {'eoffs':>18s} {'e+out':>5s} {'pull-bot p10/50/90':>20s} {'pulled':>6s} {'bot eth p50':>10s} {'minout med':>10s} {'ahead p90':>9s} {'outs':>4s} {'nbot':>4s}")
        for h in sorted(by):
            s = summarize(by[h]); out[fam]["hours"][h] = s
            lines.append(f"{h:9s} {s['n']:3d} {str(s['bot_off_p10_50_90']):>15s} {s['no_bot']:5d} {s['early_pull']:5d} {str(s['early_pull_offs'][:6]):>18s} {s['early_pull_with_outsider_before']:5d} "
                         f"{str(s['pull_minus_bot_p10_50_90']):>20s} {s['pulled_within_1200']:6d} {str(s['bot_eth_p10_50_90'] and s['bot_eth_p10_50_90'][1]):>10s} "
                         f"{str(s['minout_ratio_min_med_max'] and s['minout_ratio_min_med_max'][1]):>10s} {str(s['eth_ahead_p50_p90_max'][1]):>9s} {s['with_outsider_ahead']:4d} {s['bot_buys_per_pool_p50']:4d}")
    json.dump(out, open(os.path.join(HERE, "regime.json"), "w"), indent=1)
    open(os.path.join(HERE, "regime.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
