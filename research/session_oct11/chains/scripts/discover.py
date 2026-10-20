"""24h scan of pool/pair-creation events across ALL emitters (no address filter), tallied by emitter.
usage: discover.py <chain> <rpc_url> [hours=24] [chunk=10000]"""
import json, sys, os, time, collections
sys.path.insert(0, os.path.dirname(__file__))
import rpc
OUT = os.path.join(os.path.dirname(__file__), "..", "out")
T = {
 "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9": "V2 PairCreated",
 "0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118": "V3 PoolCreated",
 "0x2128d88d14c80cb081c1252a5acff7a264671bf199ce226b53788fb26065005e": "Solidly PoolCreated(stable)",
 "0xab0d57f0df537bb25e80245ef7748fa62353808c54d6e528a9dd20887aed9ac2": "Slipstream PoolCreated(tickSpacing)",
 "0x91ccaa7a278130b65168c3a0c8d3bcae84cf5e43704342bd3ec0b59e59c036db": "Algebra Pool",
 "0x8a5f030f5fc13b04a1e4ef7c47177e3d76b0e80e1d9be9843db37caa5b7b9b8f": "Algebra CustomPool",
 "0xdd466e674ea557f56295e2d0218a125ea4b4f0f6f3307b95f85e6110838d6438": "V4 Initialize",
 "0x426cc62fe6a33a40ba2788c2c87a9c34ee4582b95bc9fa5a7bb7ae70b750b99c": "PCS Infinity CL Initialize",
 "0xc60523754e4c8d044ae75f841c3a7f27fefeed24c086155510c2ae0edf538fa0": "four.meme TokenCreate(7)",
 "0x396d5e902b675b032348d3d2e9517ee8f0c4a926603fbc075d3d282ff00cad20": "four.meme TokenCreate(8)",
}
def block_at_time(url, target_ts, head):
    """binary search block with timestamp >= target_ts"""
    lo, hi = max(0, head - 5_000_000), head
    hb = rpc.get_block(url, head); ht = int(hb["timestamp"], 16)
    # fast estimate using recent block time
    b2 = rpc.get_block(url, head - 1000); bt = (ht - int(b2["timestamp"], 16)) / 1000
    est = int(head - (ht - target_ts) / max(bt, 1e-3))
    lo, hi = max(0, est - 20000), min(head, est + 20000)
    while lo < hi:
        mid = (lo + hi) // 2
        if int(rpc.get_block(url, mid)["timestamp"], 16) < target_ts: lo = mid + 1
        else: hi = mid
    return lo, bt, ht
if __name__ == "__main__":
    chain, url = sys.argv[1], sys.argv[2]
    hours = float(sys.argv[3]) if len(sys.argv) > 3 else 24
    chunk = int(sys.argv[4]) if len(sys.argv) > 4 else 10000
    maxc = int(sys.argv[5]) if len(sys.argv) > 5 else chunk * 8
    head = rpc.block_number(url)
    frm, bt, ht = block_at_time(url, int(rpc.get_block(url, head)["timestamp"], 16) - int(hours * 3600), head)
    log = []
    t0 = time.time()
    logs, ch = rpc.get_logs_range(url, None, [list(T)], frm, head, chunk=chunk, max_chunk=maxc, log=log)
    tally = collections.Counter((l["address"].lower(), T[l["topics"][0]]) for l in logs)
    res = {"chain": chain, "url": url, "from": frm, "to": head, "head_ts": ht, "hours": hours,
           "block_time_est": bt, "n_logs": len(logs), "secs": round(time.time() - t0, 1), "final_chunk": ch,
           "errlog": log[:20], "by_emitter": [[a, k, n] for (a, k), n in tally.most_common()]}
    json.dump(res, open(os.path.join(OUT, f"discover_{chain}.json"), "w"), indent=1)
    with open(os.path.join(OUT, f"creations_{chain}.jsonl"), "w") as f:
        for l in logs: f.write(json.dumps(l) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "by_emitter"}))
    for a, k, n in res["by_emitter"][:25]: print(n, k, a)
    print("stats", rpc.STATS)
