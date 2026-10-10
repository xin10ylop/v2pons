"""Independent re-implementation of the release 0.3 exit on the operator's sub-1% launches (slowrug_op.json.gz).
Pool model: one full-range position (verified), exact-in swaps with fee on input (verified to 4e-16 on 44,975 swaps).
Our buy is inserted into the pool (shadow replay), so every later swap and our sell see the pool WITH our buy."""
import sys, statistics as st, collections
sys.path.insert(0, '.'); sys.path.insert(0, '/home/user/v2pons/src')
from load import *
import v4math
P, S, L, T, TS = load()
Q = 1 << 96
STAKE = int(0.0012e18); GAS = int(2 * 110000 * 0.0201e9); TP = 0.01; SLIP = 0.03
low = sorted([p for p in P if P[p]['fee'] < 10000 and T.get(P[p]['tx'], ['', ''])[1] == OP], key=lambda p: P[p]['bn'])

def sim(p, land=2, sell_lat=2, head=True, shadow=True, tp=TP, deadline_send=2, engine_model=True, max_trig=None, revert=True, gas=GAS):
    """land: our buy's block after the trigger block F. sell_lat: blocks from the feed block the sell is sent in to its landing.
    head: our buy at the head of its block (else at the tail). Returns dict or None (no trade)."""
    b0 = P[p]['bn']; fee = P[p]['fee']
    sw = sorted(S.get(p, []), key=lambda x: (x[0], x[1]))
    rems = sorted((x[0], x[1]) for x in L.get(p, []) if x[5] < 0); pull = rems[0] if rems else None
    real = [x for x in sw if x[3] < 0 and -x[3] >= 2e14 and x[0] > b0]
    if not real: return None
    F = real[0][0]
    if max_trig is not None and F - b0 > max_trig: return None
    B = F + land
    # pool state the engine sees at fire time (feed: all txs through block F); engine tracks buys only
    adds = [x for x in L.get(p, []) if x[5] > 0]; Lq = sum(x[5] for x in adds)
    pre_F = [x for x in sw if x[0] <= F]
    sp_feed = pre_F[-1][5]
    expected = v4math.buy_out_int(sp_feed, Lq, STAKE, fee); min_out = int(expected * (1 - SLIP))
    # our buy's position
    before = [x for x in sw if (x[0] < B) or (not head and x[0] == B)]
    if pull is not None and pull[0] < B or (pull is not None and not head and pull[0] == B):
        return {'res': 'pulled_before_buy', 'r': None, 'F': F - b0}
    sp = before[-1][5]
    tok = v4math.buy_out_int(sp, Lq, STAKE, fee)
    if revert and tok < min_out:
        return {'res': 'buy_reverted', 'r': -gas / 2 / STAKE, 'F': F - b0, 'moved': tok / expected - 1}
    # shadow state: 1/s after our buy
    net = STAKE - (STAKE * fee + 999_999) // 1_000_000
    s = sp / Q; s = 1 / (1 / s + net / Lq) if shadow else s
    s_eng = s   # engine: buys only
    after = [x for x in sw if x[0] > B or (head and x[0] == B)]
    def apply(s, x, buys_only=False):
        f = x[7] / 1e6
        if x[3] < 0: return 1 / (1 / s + (-x[3]) * (1 - f) / Lq)
        if buys_only: return s
        return s + (-x[4]) * (1 - f) / Lq
    def sellval(s):
        return v4math.sell_out_int(int(s * Q), Lq, tok, fee)
    # decision: TP on buys >= 2e14 in blocks B..B+deadline_send ; deadline when feed shows B+deadline_send
    send_blk = B + deadline_send; why = 'deadline'
    for x in after:
        if x[0] > B + deadline_send: break
        s_eng = apply(s_eng, x, buys_only=engine_model)
        if x[3] < 0 and -x[3] >= 2e14:
            sv = sellval(s_eng if engine_model else apply(s, x))
            if (sv - STAKE - gas) / STAKE >= tp:
                send_blk = x[0]; why = 'tp'; break
    land_blk = send_blk + sell_lat
    if pull is not None and pull[0] <= land_blk:
        return {'res': 'pulled', 'r': -1.0 - gas / 2 / STAKE, 'F': F - b0, 'why': why, 'exit': land_blk - B, 'pull': pull[0] - B}
    # price at head of land_blk: every swap in blocks < land_blk, shadowed
    s2 = s
    for x in after:
        if x[0] >= land_blk: break
        s2 = apply(s2, x)
    r = (sellval(s2) - STAKE - gas) / STAKE
    return {'res': 'ok', 'r': r, 'F': F - b0, 'why': why, 'exit': land_blk - B, 'pull': (pull[0] - B) if pull else None}

def report(name, **kw):
    rs = [sim(p, **kw) for p in low]; rs = [x for x in rs if x is not None]
    tr = [x for x in rs if x['res'] in ('ok', 'pulled')]; v = [x['r'] for x in tr]
    rev = [x for x in rs if x['res'] == 'buy_reverted']; pb = [x for x in rs if x['res'] == 'pulled_before_buy']
    whys = collections.Counter((x['why'], x['exit']) for x in tr)
    print(f"{name}: n {len(v)} mean {st.mean(v):+.2%} median {st.median(v):+.2%} pos {sum(1 for a in v if a > 0)/len(v):.0%} "
          f"worst {min(v):+.2%} -100%: {sum(1 for a in v if a <= -0.99)} | buy reverts {len(rev)} pulled-before-buy {len(pb)} | exits {sorted(whys.items())}")
    return rs

if __name__ == '__main__':
    print(f"{len(low)} sub-1% launches by the operator; with a real buy after the launch block: {sum(1 for p in low if sim(p) is not None)}")
    report("A head of F+2, sell lands send+2, shadowed, engine model, reverts on")
    report("B same, sell lands send+1", sell_lat=1)
    report("C same as A but no revert check (bt.py-like)", revert=False)
    report("D same as A, NOT shadowed (bt.py-like)", shadow=False, revert=False)
    report("E tail of F+2 (behind crowd buys in our block)", head=False)
    report("F head of F+1", land=1)
    report("G A + engine TRIGGER_MAX_BLOCKS 150", max_trig=150)
    report("H no take profit, deadline only", tp=9)
    report("I true-state TP decision (not buys-only)", engine_model=False)
    report("J sell lands send+3 (slower)", sell_lat=3)
