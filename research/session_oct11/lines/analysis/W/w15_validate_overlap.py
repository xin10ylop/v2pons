"""My forward-test pipeline (chain logs -> compact rows -> analyst C's replay) against analyst C's census events on the launches both cover"""
import pickle, json, sys
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/C")
from replay import replay
C = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/analysis/C"
R = pickle.load(open(C + "/v23.pkl", "rb")); E = pickle.load(open(C + "/ev.pkl", "rb"))
F = json.load(open("w05_recent_8h_forward.json")); n = 0; same = 0
for z in F:
    r = R.get(z["pool"])
    if not r or z["pool"] not in E: continue
    bs = [(e[1] - E[z["pool"]]["lb"], e[7] if r["quote_side"] == 0 else e[8]) for e in E[z["pool"]]["ev"] if e[0] == "s"]
    trig = [o for o, dq in bs if dq >= 5e15 and o >= 2]; b = trig[0] + 20 if trig and trig[0] + 20 <= 80 else 80
    x = replay(r, E[z["pool"]], 2, b, 0.0058); n += 1
    ok = x["ok"] and abs(x["ret"] - z["ret"]) < 1e-9 and b == z["exit"]; same += ok
    print(z["lb"], z["pool"][:10], "census", b, round(x["ret"] * 100, 4) if x["ok"] else x, "| mine", z["exit"], round(z["ret"] * 100, 4), "OK" if ok else "DIFF")
print(f"{same}/{n} identical")
