s=open('trace.py').read()
old_start = s.index('def incoming(')
old_end = s.index('def outgoing(')
s = s[:old_start] + '''def incoming(addr, before, maxback=30000, want=1, extra=300):
    """value>0 txs to addr before block `before`, scanning backwards; after the first hit look only `extra` blocks further back"""
    out = []; lo = max(0, before - maxback)
    for bn, ts, t in bc.txs_desc(lo, before - 1):
        if out and bn < out[0]["bn"] - extra: break
        if t[2] == addr and int(t[3]) > 0:
            out.append(T(bn, ts, t))
    return out, lo
''' + s[old_end:]
s=s.replace("inc, lo = incoming(cur, before, maxback=30000 if hop < 2 else 15000, want=2)","inc, lo = incoming(cur, before, maxback=20000 if hop < 2 else 12000)")
s=s.replace("f = inc[0]","f = max(inc, key=lambda x: x['eth'])")
open('trace.py','w').write(s)
