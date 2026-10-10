"""label map: crowd A (32), crowd B (31), main-loop dispatchers/sweeps (Oct 9 scans), fingerprint families (b_list fam), key addresses"""
import json, collections
S = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/"
b = json.load(open(S + "ops/b_list.json")); l = json.load(open(S + "money/loop.json")); p = json.load(open(S + "money/pots.json"))
A = set(b["A"]); B = set(b["B"]); FAM = b["fam"]
DISP = set(); SWEEP = set(); BDISP = set(); BSWEEP = set()
for k, v in p["pots"].items():
    D_, S_ = (DISP, SWEEP) if k.startswith("A") else (BDISP, BSWEEP)
    for d in v.get("dispatchers", []): D_.add(d["addr"]); [S_.add(g[0]) for g in d["got"]]
    for s_ in v.get("sweeps", []): S_.add(s_["addr"])
KEY = {"0x3fc5b8b8dada622d7f41a35a0ad8ac2e5d0f8d8a": "COLLECTOR", "0x5861708803b8b73b2df8d985bed333b88c92dcc0": "A-5861",
       "0x20d811c806351d2edc6cb297f6e75e954bf443a5": "A-20d8", "0x3194e32622c5d860a0572c74edda99dcfd8fc827": "LAUNCHER",
       "0x58daec3116aae6d93017baaea7749052e8a04fa7": "POSMGR"}
def lab(a):
    if a in KEY: return KEY[a]
    if a in A: return "[A]"
    if a in B: return "[B]"
    if a in DISP: return "[A-DISP]"
    if a in SWEEP: return "[A-SWEEP]"
    if a in BDISP: return "[B-DISP]"
    if a in BSWEEP: return "[B-SWEEP]"
    if a in FAM: return "[fp:" + FAM[a] + "]"
    return ""
