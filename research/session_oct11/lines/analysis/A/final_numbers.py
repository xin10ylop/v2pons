"""Pull the chosen rules' numbers (all days, per day, last 24 h = day 6) out of the grid outputs for REPORT.md."""
import json
F = json.load(open("follow_grid.json")); R = json.load(open("rules_results.json")); TP = json.load(open("tp_grid.json"))
def line(tag, st):
    dd = " | ".join(f"d{d}: n={st['by_day'][str(d)]['n']} mean={st['by_day'][str(d)].get('mean', 0):+.3f} win={st['by_day'][str(d)].get('win', 0):.2f} pulled={st['by_day'][str(d)].get('pulled', 0):.3f}" if st['by_day'][str(d)].get('n') else f"d{d}: -" for d in range(7))
    print(f"{tag}: n={st['n']} mean={st['mean']:+.4f} median={st['median']:+.4f} win={st['win']:.3f} worst={st['worst']:+.3f} pulled={st['pulled']:.3f} $/trade={st['mean_usd']:+.3f} $/day={st.get('usd_day')} tradable={st.get('tradable_share')}\n    {dd}")
for k in ("C1_eth|frb via 0xd6d35b56|d2|H60|q0.0058", "C1_eth|frb via 0xd6d35b56|d2|H60|q0.002", "C1_eth|frb via 0xd6d35b56|d2|H40|q0.0058", "C1_eth|frb via 0xd6d35b56|d2|H20|q0.0058",
          "C1_eth|buy>=0.02|d2|H60|q0.0058", "C1_eth|frb via 0xd6d35b56|d2|H100|q0.0058",
          "C1_weth|frb via 0xd6d35b56|d2|H60|q0.0058", "a98b_hook|buy>=0.02|d2|H60|q0.0058", "564f_weth_hook|buy>=0.005|d2|H100|q0.0058", "odd2_1444|buy>=0.005|d2|H60|q0.0058"):
    line(k, F[k])
for name in ("C1_eth", "C1_weth", "a98b_hook", "564f_weth_hook", "odd2_1444"):
    o = R[name]
    print(f"\n{name}: n={o['n']} /day={o['per_day']} frb share={o['frb_share']} frb off p10/50/90={o['frb_off']} eth={o['frb_eth']} top fp={o['frb_top_fp']} price move %={o['frb_move_pct']} our impact %={o['our_impact_on_frb_output_pct']}")
    for rk in ("front a2 b=frb+1 (frb pools)|q=0.0058", f"front a2 b=frb+1 else a+{o['fallback_hold']}|q=0.0058", "front a2 b=frb+1 (frb pools)|q=0.002", "delayed(oracle) a=frb-2 b=a+60|q=0.0058", "follow a=frb+2 b=a+20|q=0.0058", "follow a=frb+2 b=a+60|q=0.0058", "follow a=frb+2 b=a+60|q=0.002", "front a2 b40|q=0.0058"):
        if rk in o["rules"]: line("   " + rk, o["rules"][rk])
for k in ("C1_eth|a2|H150|tp0.2|q0.0058", "C1_eth|a2|H100|tp0.2|q0.0058", "odd2_1444|a2|H600|tp0.03|q0.0058"):
    if k in TP: line(k, TP[k])
