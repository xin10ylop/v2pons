NEW30 = 1791692539          # 2026-10-11 04:22:19 UTC, the 3.0 line's late-bot regime (REPORT_R)
def regime(D, bn):
    bps = (D["end"] - D["start"]) / (D["t1"] - D["t0"])
    return "new" if D["t0"] + (bn - D["start"]) / bps >= NEW30 else "old"
