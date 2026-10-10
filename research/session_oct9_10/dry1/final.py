import json, statistics as st
rows = json.load(open("replay.json"))
out = []
for r in rows:
    f, s, d = r["fast"], r["slow"], r["dry"]
    pre_pull = [x for x in r["small_nonbot_buys"]]
    o = {"pid": r["pid"], "b0": r["b0"], "time_utc": r["time_utc"], "eth_ahead_before_fire": f["eth_in_b0"] / 1e18, "skipped": "no" if f["exit"] != "skip" else f["why"],
         "bot_buy_block": r["bot_buy_block"], "bot_buy_eth": round(r["bot_value"] / 1e18, 6),
         "bot_buy_reverts_with_ours": not (r["bot_headroom_fast"] >= 1 and r["bot_headroom_slow"] >= 1),
         "sell_send_block": r["b0"] + f["send"], "ret_fast": round(f["ret"], 5), "ret_slow": round(s["ret"], 5), "tp_ret_engine_model": d["tp_ret"],
         "pull_block": r["pull_block"], "pull_after_launch": r["pull"],
         "why": (f"take profit on the bot's buy at +{r['bot_off']} ({r['bot_value']/1e18:.5f} ETH): sell sent +{f['send']}, lands +{f['S']} fast / +{s['S']} slow; "
                 f"bot output with ours ahead {r['bot_headroom_fast']:.5f}x its minOut; engine tp (live, our buy at B) {f['tp_live']}/{s['tp_live']}; dry run after_buy {d['after_buy']}; "
                 f"no swap between the bot's buy and our sell; pull {('+' + str(r['pull'])) if r['pull'] is not None else 'none yet (to block ' + str(r['logs_to']) + ')'}"
                 + (f", {r['pull'] - f['S']} blocks after the fast sell lands" if r['pull'] is not None else "")),
         "outsider_buys": "none >= 0.0002 ETH; sub-0.0002 non-bot buys (block offset, ETH, wallet, via): " + "; ".join(f"+{a} {b} {c} {e}" for a, b, c, e in pre_pull)}
    out.append(o)
json.dump(out, open("final.json", "w"), indent=1)
for case in ("fast", "slow"):
    v = [r[case]["ret"] for r in rows]
    print(case, len(v), st.mean(v), st.median(v), min(v), max(v))
tp = [r["dry"]["tp_ret"] for r in rows]
print("dry", st.mean(tp[:16]), min(tp[:16]), st.mean(tp), min(tp))
pl = [r["pull"] for r in rows if r["pull"] is not None]; print("pull-launch", sorted(pl))
print("pull-bot", sorted(r["pull"] - r["bot_off"] for r in rows if r["pull"] is not None))
print("pull-S fast", sorted(r["pull"] - r["fast"]["S"] for r in rows if r["pull"] is not None), "slow", sorted(r["pull"] - r["slow"]["S"] for r in rows if r["pull"] is not None))
g93 = []; g65 = []
for r in rows:
    if r["pull"] is None: continue
    for a, b, c, e in r["small_nonbot_buys"]:
        if c.startswith("93b079"): g93.append(r["pull"] - a)
        if e.startswith("65050a"): g65.append(r["pull"] - a)
print("93b079 buy -> pull", sorted(g93)); print("65050a buy -> pull", sorted(g65))
print("bot offsets", sorted(r["bot_off"] for r in rows), "bot eth", sorted(round(r["bot_value"]/1e18,4) for r in rows))
print("headroom", min(min(r["bot_headroom_fast"], r["bot_headroom_slow"]) for r in rows), max(r["bot_headroom_fast"] for r in rows))
print("tail==head", all(abs(r[c]["ret_tail"] - r[c]["ret"]) < 1e-9 for r in rows for c in ("fast", "slow")))
print("tokens_vs_minout", min(r[c]["tokens_vs_minout"] for r in rows for c in ("fast","slow")))
print("max |ret - tp|", max(abs(r["fast"]["ret"] - r["dry"]["tp_ret"]) for r in rows), max(abs(r["slow"]["ret"] - r["dry"]["tp_ret"]) for r in rows))
