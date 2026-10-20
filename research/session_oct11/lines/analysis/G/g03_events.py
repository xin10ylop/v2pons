"""load the census events of every kept family's pools, keep [L, L+SPAN_KEEP] in a compact parsed form -> ev.pkl
per pool: sw = [(bn, li, buy, qin, tin, sqrt_after, liq_after, fee, sender, in_launch_tx)], mods = [(bn, li, lo, hi, delta, sender, in_launch_tx)]"""
from common import *
sys.path.insert(0, CEN)
from load import load_events
SPAN_KEEP = 700
kept = json.load(open(os.path.join(G, "families_kept.json")))
rows = {r["pool"]: r for r in load_rows()}
ids = set(p for v in kept.values() for p in v)
E = load_events(ids)
out = {}; senders = C.Counter(); n_ev = 0
for p, o in E.items():
    r = rows[p]; L = r["launch_block"]; qs = r["quote_side"]; ltx = (r["launch_tx"] or "").lower()
    sw, mods = [], []
    for e in o["ev"]:
        if e[1] > L + SPAN_KEEP: break
        n_ev += 1
        if e[0] == "s":
            a0, a1 = e[6], e[7]
            dq, dt = (a0, a1) if qs == 0 else (a1, a0)
            buy = dq < 0
            sw.append((e[1], e[3], buy, -dq if buy else 0, -dt if not buy else 0, e[8], e[9], e[11], e[5].lower(), e[12].lower() == ltx))
            senders[e[5].lower()[:10]] += 1
        elif e[0] == "m":
            mods.append((e[1], e[3], e[6], e[7], e[8], e[5].lower(), e[10].lower() == ltx))
    out[p] = {"sw": sw, "mods": mods, "kind": o["kind"]}
pickle.dump(out, open(os.path.join(G, "ev.pkl"), "wb"))
print("pools with events", len(out), "of", len(ids), "events kept", n_ev)
print("top swap senders", senders.most_common(15))
print("our relay as swap sender:", sum(v for k, v in senders.items() if k.startswith(OUR_RELAY)))
