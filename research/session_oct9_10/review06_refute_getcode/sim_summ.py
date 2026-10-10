import json, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
R = [json.loads(l) for l in open(os.path.join(HERE, "out/sim.jsonl"))]
R = [r for r in R if r["receipt"]]
print("simulated launches", len(R), "code errors", sum(1 for r in R if "err" in r))
print("code_lag (N - block the getCode reads):", sorted(collections.Counter(r.get("code_lag") for r in R if "code_lag" in r).items()))
print("arm finished at feed head N+k:", sorted(collections.Counter(r["arm_seq_off"] for r in R).items()))
in_time = [r for r in R if r["arm_seq_off"] <= 6]
print(f"seat possible (armed by N+6): {len(in_time)}/{len(R)}")
for g in (7, 8):
    miss = [r for r in R if "code_lag" in r and r["code_lag"] > g]
    hurt = [r for r in miss if r["arm_seq_off"] <= 6]
    print(f"gap {g}: getCode reads '0x' on {len(miss)}/{len(R)} ({100*len(miss)/len(R):.1f}%); of those, armed in time for the seat {len(hurt)} "
          f"-> a seat lost to the '0x' alone on {len(hurt)}/{len(R)} ({100*len(hurt)/len(R):.1f}%); of the seats otherwise possible: {len(hurt)}/{len(in_time)} ({100*len(hurt)/max(1,len(in_time)):.1f}%)")
    for r in hurt[:5]:
        print("   ", r)
