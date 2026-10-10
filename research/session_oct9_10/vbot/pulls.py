"""First liquidity removal (pull) of every PM1444 v3.0 pool, census + new, from ModifyLiquidity logs (chunks of pids); the block time."""
import sys, os, json, pickle, time
sys.path.insert(0, '..')
from chain import rpc, batch, logs, PM, T_ML, W, sgn
from fetch import universe
cen, nw = universe()
allp = cen + nw
head = int(rpc('eth_blockNumber', []), 16)
out = {}
for i in range(0, len(allp), 40):
    ch = allp[i:i+40]
    a = min(p['b0'] for p in ch); b = min(head, max(p['b0'] for p in ch) + 3000)
    ls = logs({"address": PM, "topics": [T_ML, [p['pid'] for p in ch]]}, a, b)
    for p in ch:
        rm = sorted(int(l['blockNumber'], 16) for l in ls if l['topics'][1] == p['pid'] and sgn(W(l['data'], 2)) < 0)
        out[p['pid']] = {'b0': p['b0'], 'src': p['src'], 'pull': rm[0] if rm else None, 'scanned_to': b}
    print(i, file=sys.stderr)
# timestamps: one block per 2000 for interpolation
bs = sorted({p['b0'] for p in allp})
samp = list(range(bs[0], head, 20000)) + [head]
hdr = batch([("eth_getBlockByNumber", [hex(n), False]) for n in samp])
tsm = [(n, int(h['timestamp'], 16)) for n, h in zip(samp, hdr)]
json.dump({'head': head, 'pulls': out, 'ts_samples': tsm}, open('pulls.json', 'w'))
print('done', len(out))
