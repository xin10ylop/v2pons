"""The 3.0/5.0 launches run on a 10-minute clock (most at hh:m8:04-14 UTC). Is the first buy T tied to that clock rather than to L?
Per 10-minute tick: the launches in it, their order, and T measured from the tick (block clock: the tick block = first block with
ts >= the tick, interpolated from L's block and timestamp at 9.77 blocks/s) against T measured from L."""
import pickle, json, collections, statistics as st
D = pickle.load(open("cache/data.pkl", "rb")); pools = D["pools"]; bps = D["meta"]["bps"]
B = {}
for l in open("blocks.jsonl"): x = json.loads(l); B[x["n"]] = x
P = sorted([p for p in pools if p["line"] in ("3.0", "5.0") and p["L"] in B], key=lambda p: p["L"])
ticks = collections.defaultdict(list)
for p in P:
    ts = B[p["L"]]["ts"]; ticks[ts // 600].append(p)
print("launches per 10-minute window:", sorted(collections.Counter(len(v) for v in ticks.values()).items()))
print("launch second within the window (ts mod 600) for the slot-8 launches:", sorted(collections.Counter(B[p['L']]['ts'] % 600 for p in P if (B[p['L']]['ts'] % 600) // 60 == 8).items()))
rows = []
for k, v in ticks.items():
    s8 = [p for p in v if (B[p["L"]]["ts"] % 600) // 60 == 8 and p["T"] is not None]
    for i, p in enumerate(s8):
        tick_ts = k * 600 + 480
        # approximate tick block from L: L - (ts(L) - tick) * bps (1 s resolution, so +-10 blocks)
        rows.append((p["T"], p["Tbn"] - (p["L"] - (B[p["L"]]["ts"] - tick_ts) * bps), B[p["Tbn"]]["ts"] - tick_ts if p["Tbn"] in B else None, B[p["L"]]["ts"] - tick_ts, i, p["line"], p["lnonce"]))
T_L = [r[0] for r in rows]; T_tick_s = [r[2] for r in rows if r[2] is not None]; L_tick_s = [r[3] for r in rows]
print(f"slot-8 launches with T: {len(rows)}; sd of T-L {st.pstdev(T_L)/bps:.2f} s ({st.pstdev(T_L):.1f} blocks); sd of T-tick {st.pstdev(T_tick_s):.2f} s; sd of L-tick {st.pstdev(L_tick_s):.2f} s")
print("T - tick (s):", sorted(collections.Counter(T_tick_s).items()))
print("by order inside the tick (0 = first launch): T-L p50", {i: sorted(r[0] for r in rows if r[4] == i)[len([r for r in rows if r[4] == i]) // 2] for i in sorted(set(r[4] for r in rows))},
      " n", dict(collections.Counter(r[4] for r in rows)))
print("order/line/nonce pattern of the ticks:", collections.Counter(tuple((p["line"], p["lnonce"] < 10) for p in v) for v in ticks.values()).most_common(6))
