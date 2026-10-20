"""B02: every Swap/Mint/Burn of the WETH-side 13ead562 pools from the launch block to +WIN (default 5000) or the frozen head, as compact
rows; the txs behind every mint, every burn and every swap to +SWTX (default 400); the token's Transfer logs sent by the launch wallet to
+400 (the dEaD transfer). Public RPC, read-only. Caches: b02_ev / b02_tx / b02_tr (*_cache.jsonl). fetch() is reused by b06 for census pools."""
import sys, os, json
from bc import *
EV = Cache("b02_ev"); TX = Cache("b02_tx"); TR = Cache("b02_tr")
def fetch(L, head, win=5000, swtx=400):
    todo = [x for x in L if x["pool"] not in EV or EV[x["pool"]]["ev_to"] < min(x["lb"] + win, head)]
    for i in range(0, len(todo), 10):
        ch = todo[i:i + 10]
        prm = [[{"address": x["pool"], "topics": [[T_SW, T_MI, T_BU]], "fromBlock": hex(x["lb"]), "toBlock": hex(min(x["lb"] + win, head))}] for x in ch]
        try: res = R.batch("eth_getLogs", prm, n=10)
        except RuntimeError: res = [None] * len(ch)
        for x, ls in zip(ch, res):
            if ls is None: ls = R.logs({"address": x["pool"], "topics": [[T_SW, T_MI, T_BU]]}, x["lb"], min(x["lb"] + win, head))
            ls = sorted(ls, key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
            EV.put(x["pool"], {"lb": x["lb"], "ev_to": min(x["lb"] + win, head), "ev": [c for c in (compact(l) for l in ls) if c]})
    want = []
    for x in L:
        for e in EV[x["pool"]]["ev"]:
            if e[0] in ("mi", "b") or (e[0] == "s" and e[1] - x["lb"] <= swtx): want.append(e[-1])
    txs(TX, want)
    todo = [x for x in L if x["pool"] not in TR]
    for i in range(0, len(todo), 10):
        ch = todo[i:i + 10]
        prm = [[{"address": x["token"], "topics": [T_TR, pad(x["launch_from"])], "fromBlock": hex(x["lb"]), "toBlock": hex(min(x["lb"] + 400, head))}] for x in ch]
        res = R.batch("eth_getLogs", prm, n=10)
        for x, ls in zip(ch, res):
            TR.put(x["pool"], [[int(l["blockNumber"], 16), "0x" + l["topics"][2][-40:], int(l["data"], 16), l["transactionHash"]] for l in (ls or [])])
if __name__ == "__main__":
    D = json.load(open(p("b01_launches.json"))); head = D["meta"]["head"]
    L = [x for x in D["launches"] if x["qs"] is not None]
    fetch(L, head)
    print(f"{len(L)} pools, {sum(len(EV[x['pool']]['ev']) for x in L)} events, {len(TX.d)} txs cached; rpc {R.STATS}")
