# exact replay of "buy 0.0058 ETH at launch + 1, sell at block S" on every pool of the family (full-range single position: L constant)
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/user/v2pons/src")
import json, collections, statistics as st
import v4math
HERE = os.path.dirname(os.path.abspath(__file__))
F = json.load(open(os.path.join(HERE, 'data/fam.json')))
Q96 = 1 << 96
STAKE = int(0.0058e18); GAS = int(0.012 / 2586 * 1e18)   # $0.012 round trip at $2586/ETH ($15 = 0.0058 ETH)
def net(x, f): return x - (x * f + 999_999) // 1_000_000
class Pool:
    def __init__(s, r):
        s.r = r; s.lb = r['lb']; s.L = r['L0']; s.sp0 = r['sp0']; s.fee = r['fee']
        s.full = all(lo <= -887000 and hi >= 887000 for lo, hi, d in r['adds'])
        prev = s.sp0; s.seq = []
        for x in r['swaps']:
            if x['in_launch']: prev = x['sp']; continue
            d = dict(x)
            if x['buy']: d['d_inv'] = Q96 / x['sp'] - Q96 / prev
            else: d['d_sp'] = x['sp'] - prev
            prev = x['sp']; s.seq.append(d)
        s.pull = r['pull']
    def trade(s, B, S, stake=STAKE):
        """our buy at the END of block lb+B, sell at the HEAD of block lb+S"""
        if s.pull is not None and s.pull <= B: return dict(exit='pulled_before_buy', ret=-GAS / 2 / stake)
        sp = float(s.sp0)
        for x in s.seq:
            if x['rel'] > B: break
            sp = Q96 / (Q96 / sp + x['d_inv']) if x['buy'] else sp + x['d_sp']
        tok = v4math.buy_out_int(int(sp), s.L, stake, s.fee)
        sp = Q96 / (Q96 / sp + net(stake, s.fee) / s.L)
        if s.pull is not None and s.pull <= S: return dict(exit='pulled_first', ret=(-stake - GAS) / stake)
        for x in s.seq:
            if x['rel'] <= B: continue
            if x['rel'] >= S: break
            sp = Q96 / (Q96 / sp + x['d_inv']) if x['buy'] else sp + x['d_sp']
        out = v4math.sell_out_int(int(sp), s.L, tok, s.fee)
        return dict(exit='sold', ret=(out - stake - GAS) / stake)
def rule_k(p, k=10, abort_first=640, deadline=2400, gap=None, B=1):
    cr = p.r['cr_rel']
    if not cr or cr[0] > abort_first: return p.trade(B, abort_first)
    last = cr[0]
    for i, x in enumerate(cr):
        if gap is not None and x - last > gap: return p.trade(B, last + gap)
        last = x
        if i + 1 == k: return p.trade(B, x + 1)
    end = deadline if gap is None else min(deadline, last + gap)
    return p.trade(B, end)
def summ(rs):
    v = [r['ret'] for r in rs]
    if not v: return {}
    ex = collections.Counter(r['exit'] for r in rs)
    return dict(n=len(v), mean=round(st.mean(v) * 100, 2), median=round(st.median(v) * 100, 2), win=round(sum(a > 0 for a in v) / len(v), 3),
                pulled_first=ex.get('pulled_first', 0), usd_trade=round(st.mean(v) * 15, 3))
if __name__ == '__main__':
    P = [Pool(r) for r in F]
    print('full range all:', all(p.full for p in P))
    def era(p):
        mo = [x['mo'] / x['tok'] for x in p.r['swaps'] if x['crowd'] and x['mo']]
        return 'mo0.8' if st.median(mo) <= 0.9 else 'mo0.98'
    groups = {'all': P, 'mo0.8 (Sep 28 on)': [p for p in P if era(p) == 'mo0.8'], 'mo0.98 (Sep 11-27)': [p for p in P if era(p) == 'mo0.98'],
              'claim17': [p for p in P if p.r['pid'] in set(json.load(open('/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census/families.json'))['0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true']['pids'])]}
    c2 = json.load(open(os.path.join(HERE, 'data/c2.json')))
    analog = {g['pid'] for g in c2['mo0.8|real>=0.002']}
    tiny = {g['pid'] for g in c2['mo0.8|tiny<0.002']}
    groups['analog 0x578e (0.005 held before crowd)'] = [p for p in P if p.r['pid'][:10] in analog]
    groups['tiny outsider held before crowd (mo0.8)'] = [p for p in P if p.r['pid'][:10] in tiny]
    groups['no outsider before crowd (mo0.8)'] = [p for p in groups['mo0.8 (Sep 28 on)'] if p.r['pid'][:10] not in analog | tiny]
    out = {}
    for name, G in groups.items():
        print(f'\n== {name} (n {len(G)})')
        for lab, fn in [('claim rule k10/abort640/dl2400', lambda p: rule_k(p, 10)),
                        ('k10 + gap300', lambda p: rule_k(p, 10, gap=300)),
                        ('k8', lambda p: rule_k(p, 8)), ('k6', lambda p: rule_k(p, 6)), ('k5', lambda p: rule_k(p, 5)), ('k3', lambda p: rule_k(p, 3)), ('k1', lambda p: rule_k(p, 1)),
                        ('k5 + gap250', lambda p: rule_k(p, 5, gap=250)),
                        ('follow: B=1st crowd+1, k10', lambda p: rule_k(p, 10, B=(p.r['cr_rel'][0] + 1) if p.r['cr_rel'] else 1))]:
            s = summ([fn(p) for p in G]); out[f'{name}|{lab}'] = s
            print(f'  {lab:34s} {s}')
    json.dump(out, open(os.path.join(HERE, 'data/c3.json'), 'w'), indent=1)
