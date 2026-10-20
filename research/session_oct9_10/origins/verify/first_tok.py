"""Earliest ERC20 Transfer (to = wallet) and earliest (from = wallet) for a wallet list, by eth_getLogs in windows walking back from END to FLOOR.
usage: first_tok.py END FLOOR addr1,addr2,...  -> prints per-wallet first block seen (to or from) and count"""
import sys, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import logs, keccak
TT = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
END, FLOOR = int(sys.argv[1]), int(sys.argv[2]); W = [w.lower() for w in sys.argv[3].split(",")]
TW = ["0x" + "0" * 24 + w[2:] for w in W]
first = {}; cnt = {w: 0 for w in W}; tokens = {}
hi = END; step = 400000
while hi > FLOOR:
    lo = max(FLOOR, hi - step + 1)
    for pos in (1, 2):
        topics = [TT, TW, None] if pos == 1 else [TT, None, TW]
        for l in logs({"topics": topics}, lo, hi):
            w = "0x" + l["topics"][pos][-40:]; bn = int(l["blockNumber"], 16)
            cnt[w] += 1
            if w not in first or bn < first[w][0]: first[w] = (bn, l["address"], l["transactionHash"])
    print("window", lo, hi, "seen", len(first), flush=True)
    hi = lo - 1; time.sleep(0.5)
for w in W: print(w, first.get(w), cnt[w])
