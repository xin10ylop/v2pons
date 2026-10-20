"""Who funded a wallet: scan blocks backward from B (shared cache, polite fetcher) for value>0 txs to it, and its own txs, until the first
incoming is found (then EXTRA more blocks). Usage: hopback.py addr B [maxback] [extra]  -> appends to hops.jsonl"""
import sys, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins")
import fb
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins/"
a = sys.argv[1].lower(); B = int(sys.argv[2]); mb = int(sys.argv[3]) if len(sys.argv) > 3 else 60000; extra = int(sys.argv[4]) if len(sys.argv) > 4 else 300
hits = []; first_in = None; t0 = time.time(); last_c = None
for bn, ts, t in fb.txs_desc(B - mb, B):
    if first_in is not None and bn < first_in - extra: break
    c = bn // 250
    if c != last_c:
        last_c = c
        if c % 8 == 0: print("  at", bn, f"{time.time()-t0:.0f}s", fb.STATS, flush=True)
    if t[2] == a and int(t[3]) > 0 or t[1] == a:
        r = [bn, ts, t[0], t[1], t[2], t[3], t[4], t[5]]; hits.append(r)
        print(bn, time.strftime("%m-%d %H:%M:%S", time.gmtime(ts)), t[1], "->", t[2], int(t[3]) / 1e18, "n", t[4], t[5], t[0], flush=True)
        if t[2] == a and int(t[3]) > 0 and first_in is None and int(t[3]) > 10**15: first_in = bn
json.dump({"addr": a, "B": B, "scanned_to": bn, "hits": hits}, open(D + "hops.jsonl", "a")); open(D + "hops.jsonl", "a").write("\n")
print("done", a, "scanned back to", bn, flush=True)
