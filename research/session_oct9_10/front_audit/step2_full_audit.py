"""Every live front trade since 09:00 UTC: the pool's launch, our buy, every buy behind ours (the bot's by its router), the pull, our sell."""
import sys, json, datetime, collections, statistics as st
sys.path.insert(0, '/home/user/v2pons/research/session_oct9_10'); sys.path.insert(0, '/home/user/v2pons/src')
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML, W, sgn
import v4math
RELAY = '0x2abb5653352f6b2f3b4f4261877cd02d9e05a957'; BOT_ROUTER = '0x1cbaf24d53fe930fce8eff149fa797d2611da149'; UR = '0x8876789976decbfcbbbe364623c63652db8c0904'
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
ours = json.load(open('our_swaps.json')); pids = [x['pid'] for x in ours]; by_pid = {x['pid']: x for x in ours}
a = min(x['buy_bn'] for x in ours) - 60; b = max((x['sell_bn'] or x['buy_bn']) for x in ours) + 80
lg = []; inits = []
for i in range(0, len(pids), 20):
    lg += logs({'address': PM, 'topics': [[T_SWAP, T_ML], pids[i:i + 20]]}, a, b)
    inits += logs({'address': PM, 'topics': [T_INIT, pids[i:i + 20]]}, a, b)
print('pool logs', len(lg), 'inits', len(inits))
launch = {l['topics'][1]: int(l['blockNumber'], 16) for l in inits}
fee = {l['topics'][1]: W(l['data'], 0) for l in inits}
txh = sorted({l['transactionHash'] for l in lg if l['topics'][0] == T_SWAP})
txs = {}
for i in range(0, len(txh), 200):
    ch = txh[i:i + 200]; txs.update(dict(zip(ch, batch([('eth_getTransactionByHash', [h]) for h in ch]))))
print('swap txs', len(txs))
pools = collections.defaultdict(lambda: {'swaps': [], 'pulls': []})
for l in lg:
    pid = l['topics'][1]; d = l['data']; bn = int(l['blockNumber'], 16); ti = int(l['transactionIndex'], 16)
    if l['topics'][0] == T_SWAP:
        t = txs.get(l['transactionHash']) or {}
        pools[pid]['swaps'].append({'bn': bn, 'ti': ti, 'sender': '0x' + l['topics'][2][-40:], 'to': (t.get('to') or '').lower(), 'value': int(t.get('value', '0x0'), 16), 'a0': s128(W(d, 0)), 'a1': s128(W(d, 1)), 'sp': W(d, 2), 'L': W(d, 3), 'sel': (t.get('input') or '')[2:10]})
    elif sgn(W(d, 2)) < 0:
        pools[pid]['pulls'].append((bn, ti))
rows = []
for x in ours:
    pid = x['pid']; P = pools[pid]; L0 = launch.get(pid); sw = sorted(P['swaps'], key=lambda s: (s['bn'], s['ti'])); pull = min(P['pulls']) if P['pulls'] else None
    ob = next((s for s in sw if s['sender'].lower() == RELAY and s['a0'] < 0), None); os_ = next((s for s in sw if s['sender'].lower() == RELAY and s['a1'] < 0), None)
    behind = [s for s in sw if ob and (s['bn'], s['ti']) > (ob['bn'], ob['ti']) and s['a0'] < 0 and s['sender'].lower() != RELAY and (os_ is None or (s['bn'], s['ti']) < (os_['bn'], os_['ti']))]
    bots = [s for s in sw if s['to'] == BOT_ROUTER and s['a0'] < 0]
    bot1 = bots[0] if bots else None
    ahead = [s for s in sw if ob and (s['bn'], s['ti']) < (ob['bn'], ob['ti']) and s['a0'] < 0]
    row = {'time': x['time'], 'pid': pid[:10], 'stake': x['eth_in'], 'ret': x['ret'], 'launch': L0, 'buy_off': ob['bn'] - L0 if ob and L0 else None, 'sell_off': os_['bn'] - L0 if os_ and L0 else None,
           'bot_off': bot1['bn'] - L0 if bot1 and L0 else None, 'bot_eth': -bot1['a0'] / 1e18 if bot1 else None, 'bot_n': len(bots), 'bot_sizes': [round(-s['a0'] / 1e18, 5) for s in bots],
           'pull_off': pull[0] - L0 if pull and L0 else None, 'pull_minus_sell': (pull[0] - os_['bn']) if pull and os_ else None, 'pull_minus_bot': (pull[0] - bot1['bn']) if pull and bot1 else None,
           'pulled_first': bool(pull and os_ and pull < (os_['bn'], os_['ti'])) or (bool(pull) and os_ is None),
           'behind_before_sell': [(s['bn'] - L0, round(-s['a0'] / 1e18, 6), 'bot' if s['to'] == BOT_ROUTER else ('ur' if s['to'] == UR else s['to'][:8])) for s in behind],
           'ahead_of_us': [(s['bn'] - L0, round(-s['a0'] / 1e18, 6), 'bot' if s['to'] == BOT_ROUTER else s['to'][:8]) for s in ahead], 'fee': fee.get(pid)}
    rows.append(row)
json.dump(rows, open('full_audit.json', 'w'), indent=1)
n = len(rows)
C = collections.Counter
print('\ntrades', n)
print('our buy offset from launch:', sorted(C(r['buy_off'] for r in rows).items(), key=lambda kv: (kv[0] is None, kv[0])))
print("bot's first buy offset:", sorted(C(r['bot_off'] for r in rows).items(), key=lambda kv: (kv[0] is None, kv[0])))
print('pull offset from launch (binned):', sorted(C((r['pull_off'] // 5 * 5 if r['pull_off'] is not None else None) for r in rows).items(), key=lambda kv: (kv[0] is None, kv[0]))[:30])
print('pull minus our sell:', sorted(C(r['pull_minus_sell'] for r in rows).items(), key=lambda kv: (kv[0] is None, kv[0])))
print('pull minus bot buy:', sorted(C(r['pull_minus_bot'] for r in rows).items(), key=lambda kv: (kv[0] is None, kv[0])))
print('pulled before our sell:', sum(1 for r in rows if r['pulled_first']))
sizes = [r['bot_eth'] for r in rows if r['bot_eth'] is not None]
print('bot first-buy size: n', len(sizes), 'min %.5f p5 %.4f median %.4f p95 %.4f max %.4f' % (min(sizes), sorted(sizes)[len(sizes) // 20], st.median(sizes), sorted(sizes)[len(sizes) * 19 // 20], max(sizes)))
print('bot first buy under 0.04 ETH:', [(r['time'], r['bot_eth'], r['bot_off'], r['pull_off'], r['sell_off'], ('%+.1f%%' % (100 * r['ret'])) if r['ret'] is not None else 'LOSS') for r in rows if r['bot_eth'] is not None and r['bot_eth'] < 0.04])
print('no bot buy at all:', [(r['time'], r['pull_off'], r['sell_off'], ('%+.1f%%' % (100 * r['ret'])) if r['ret'] is not None else 'LOSS') for r in rows if r['bot_eth'] is None])
print('more than one bot buy before our sell:', sum(1 for r in rows if sum(1 for b in r['behind_before_sell'] if b[2] == 'bot') > 1))
print('anyone but decoys/bot ahead of us (buys before ours):', [(r['time'], r['ahead_of_us']) for r in rows if r['ahead_of_us']][:10], '... count', sum(1 for r in rows if r['ahead_of_us']))
print('non-bot, non-UR buys behind ours before our sell:', [(r['time'], b) for r in rows for b in r['behind_before_sell'] if b[2] not in ('bot', 'ur')][:10])
print('sell offset distribution (from launch):', sorted(C(r['sell_off'] for r in rows).items(), key=lambda kv: (kv[0] is None, kv[0])))
# by stake
for stk in sorted({round(r['stake'], 5) for r in rows}):
    rs = [r for r in rows if round(r['stake'], 5) == stk and r['ret'] is not None]
    print('stake %.5f: %d trades, mean %+.2f%%, min %+.2f%%, pulled first %d' % (stk, len(rs), 100 * st.mean(r['ret'] for r in rs), 100 * min(r['ret'] for r in rs), sum(1 for r in rows if round(r['stake'], 5) == stk and r['pulled_first'])))
# the trades sold at the deadline (sell_off - buy_off >= 18) and the negative ones
print('\nsold 18+ blocks after our buy or negative:')
for r in rows:
    if (r['sell_off'] is not None and r['buy_off'] is not None and r['sell_off'] - r['buy_off'] >= 18) or (r['ret'] is not None and r['ret'] < 0) or r['ret'] is None:
        print(' ', r['time'], r['pid'], 'buy +%s sell +%s bot +%s (%s ETH, n %d) pull +%s ret %s behind %s' % (r['buy_off'], r['sell_off'], r['bot_off'], r['bot_eth'], r['bot_n'], r['pull_off'], ('%+.2f%%' % (100 * r['ret'])) if r['ret'] is not None else 'LOSS', r['behind_before_sell'][:4]))
# counterfactual for the losers: sell in the block after the bot's small buy, priced at the chain state after that buy
print('\ncounterfactual for the two losers (sell at the bot buy + 1, chain state after the bot buy):')
for x in ours:
    if x['ret'] is None:
        P = pools[x['pid']]; sw = sorted(P['swaps'], key=lambda s: (s['bn'], s['ti'])); bot = next((s for s in sw if s['to'] == BOT_ROUTER and s['a0'] < 0), None)
        tokens = x['tokens']; f = fee[x['pid']]
        eth = v4math.sell_out_int(bot['sp'], bot['L'], tokens, f); gas = 2 * 104000 * 20_000_000
        print(' ', x['time'], 'tokens', tokens, 'sell after bot buy ->', eth / 1e18, 'ETH; ret %+.3f%% (after gas %+.3f%%)' % (100 * (eth - x['eth_in'] * 1e18) / (x['eth_in'] * 1e18), 100 * (eth - x['eth_in'] * 1e18 - gas) / (x['eth_in'] * 1e18)))
        # what take_profit computed at the bot's buy in the engine: ret vs 1%
