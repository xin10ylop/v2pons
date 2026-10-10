"""Family definitions (launch-time observable fields only) shared by the analysis scripts."""
import pickle, collections, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
GENERIC = {PM_POS, PM}
BT = json.load(open(os.path.join(HERE, "blockts.json")))
T0 = 1791417600
def hours(b):
    for (b1, t1), (b2, t2) in zip(BT, BT[1:]):
        if b1 <= b <= b2: return (t1 + (b - b1) * (t2 - t1) / (b2 - b1) - T0) / 3600
    (b1, t1), (b2, t2) = BT[-2], BT[-1]; return (t1 + (b - b1) * (t2 - t1) / (b2 - b1) - T0) / 3600
WINDOW_H = (BT[-1][1] - T0) / 3600
MID_H = WINDOW_H / 2
def nb(n):
    if n is None: return "n?"
    for lo, hi in ((0, 0), (1, 1), (2, 2), (3, 3), (4, 9), (10, 19), (20, 49), (50, 99), (100, 199), (200, 299), (300, 999)):
        if lo <= n <= hi: return f"n{lo}-{hi}" if lo != hi else f"n{lo}"
    return "n1000+"
def short(a): return (a or "none")[:10]
def base_key(p, cnt_to):
    if p["ours"]: return f"OURS-{p['ours']}"
    to = p["to"] or "none"
    if to.startswith("create:") or cnt_to[to] < 3: c = "code:" + (p["code"] or "?")[:8] if not to.startswith("create:") else "create"
    else: c = short(to)
    return f"{c}|{p['sel']}|len{p['inlen']}|fee{p['fee']}|ts{p['ts']}|v{round(p['value'] or 0, 3)}"
def families(P, pids):
    cnt_to = collections.Counter(P[q]["to"] or "none" for q in P)
    F = collections.defaultdict(list)
    for i, q in enumerate(pids):
        p = P[q]; k = base_key(p, cnt_to)
        F["L:" + k].append(i)                                     # launch-field family
        if (p["to"] or "") in GENERIC:                             # behaviour sub-family: one bot's habit (nonce band, initial tick)
            F["B:" + k + "|" + nb(p["nonce"])].append(i)
            if p["to"] == PM: F["B:" + k + f"|tick0={p['tick0']}"].append(i)
        if p["ours"] == "orig":
            F["L:OURS-orig|fee<1%"].append(i) if p["fee"] < 10000 else None
    # unions (baselines)
    for i, q in enumerate(pids):
        p = P[q]
        F["U:ALL hooks0 fee<=1%"].append(i)
        if p["to"] == PM_POS and p["inlen"] == 1444: F["U:PM1444 all"].append(i)
        if p["fee"] < 10000: F["U:ALL fee<1%"].append(i)
    return F
