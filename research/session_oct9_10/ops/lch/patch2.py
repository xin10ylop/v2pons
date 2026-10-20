s=open('trace.py').read()
a = s.index('def outgoing('); b = s.index('def tag(')
s = s[:a] + '''def outgoing(addr, after, maxfwd=20000, want=3, min_eth=0.0, extra=300):
    out = []; hi = min(head() - 5, after + maxfwd)
    for bn, ts, t in bc.txs(after, hi):
        if out and bn > out[0]["bn"] + extra: break
        if t[1] == addr and int(t[3]) / 1e18 >= min_eth:
            out.append(T(bn, ts, t))
            if len(out) >= want: break
    return out, hi
''' + s[b:]
open('trace.py','w').write(s)
