import pickle, json, sys
sys.path.insert(0, ".")
C = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/analysis/C"
E = pickle.load(open(C + "/ev.pkl", "rb")); D = json.load(open("w05_recent_8h.json"))
from wcommon import compact
x = [y for y in D["line"] if y["pool"] == "0x10e8fb75088ba5a0b4796760df900f884b1d477d"][0]
mine = [c for c in (compact(l) for l in x["logs"]) if c]; cen = E[x["pool"]]["ev"]; lb = x["lb"]
print(len(mine), len(cen))
for a, b in zip([m for m in mine if m[1] < lb + 82][:60], [c for c in cen if c[1] < lb + 82][:60]):
    if a[:12] != list(b[:12]): print("mine", a[:12]); print("cen ", list(b[:12])); break
else: print("first rows equal")
print([ (m[0], m[1]-lb) for m in mine if m[1] < lb+82][:40])
print([ (c[0], c[1]-lb) for c in cen if c[1] < lb+82][:40])
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/C")
from replay import replay
R = pickle.load(open(C + "/v23.pkl", "rb")); r = R[x["pool"]]
print("row fee/qs", r["fee"], r["quote_side"])
o1 = {"lb": lb, "ev": cen, "ev_to": E[x["pool"]]["ev_to"]}; o2 = {"lb": lb, "ev": mine, "ev_to": 10**12}
print(replay(r, o1, 2, 80, 0.0058)); print(replay(r, o2, 2, 80, 0.0058)); print(replay({"dex": "v3", "quote_side": 0, "fee": 100}, o1, 2, 80, 0.0058))
diff = [(i, a, list(b)) for i, (a, b) in enumerate(zip(mine, cen)) if a != list(b)]
print(len(diff), diff[:2])
