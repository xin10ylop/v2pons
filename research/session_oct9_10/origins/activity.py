"""When were a wallet set active? ERC20 Transfer logs to (topic2) any wallet of the set, in 30000-block windows, walking back from START.
Usage: activity.py setname start stop_after_empty_windows out.jsonl  (set from state_now.json 'sets' or a comma list)"""
import sys, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import rpc, keccak
T_TR = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins/"
name, start, stop_after, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
S = json.load(open(D + "state_now.json"))["sets"]
ws = S[name] if name in S else name.split(",")
tops = ["0x" + "0" * 24 + w.lower()[2:] for w in ws]
f = open(D + out, "a"); empty = 0; hi = start
LOW = int(sys.argv[5]) if len(sys.argv) > 5 else 19000000
while hi > LOW:
    lo = hi - 29999
    for k in range(10):
        try:
            r = rpc("eth_getLogs", [{"fromBlock": hex(lo), "toBlock": hex(hi), "topics": [T_TR, None, tops]}]); break
        except Exception as e:
            print("retry", lo, str(e)[:120], flush=True); time.sleep(3 + 3 * k)
    else: raise SystemExit("fail")
    per = {}
    for l in r:
        w = "0x" + l["topics"][2][26:]; b = int(l["blockNumber"], 16)
        per.setdefault(w, [b, b, 0]); per[w][0] = min(per[w][0], b); per[w][1] = max(per[w][1], b); per[w][2] += 1
    rec = {"lo": lo, "hi": hi, "n": len(r), "wallets": len(per), "per": per}
    f.write(json.dumps(rec) + "\n"); f.flush()
    print(lo, hi, len(r), len(per), flush=True)
    empty = empty + 1 if not r else 0
    if empty >= stop_after: break
    hi = lo - 1
    time.sleep(0.2)
