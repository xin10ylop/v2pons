import sys, json, datetime, collections
sys.path.insert(0, '/home/user/v2pons/research/session_oct9_10')
from chain import rpc, logs, PM, T_SWAP, T_ML, W, sgn
UTC = datetime.timezone.utc
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
ops = json.load(open('opA_day.json'))['ops']; head = int(rpc('eth_blockNumber', []), 16)
lg = logs({'address': PM, 'topics': [[T_SWAP, T_ML], [o['pid'] for o in ops]]}, ops[0]['bn'], head)
ev = collections.defaultdict(list)
for l in lg:
    d = l['data']; bn = int(l['blockNumber'], 16)
    ev[l['topics'][1]].append(('swap', bn, s128(W(d, 0)), '0x' + l['topics'][2][-40:]) if l['topics'][0] == T_SWAP else ('ml', bn, sgn(W(d, 2)), None))
RELAY = '0x2abb5653352f6b2f3b4f4261877cd02d9e05a957'
for o in ops:
    e = sorted(ev[o['pid']], key=lambda x: x[1]); b0 = o['bn']
    buys = [(x[1] - b0, round(-x[2] / 1e18, 5), 'US' if x[3].lower() == RELAY else '') for x in e if x[0] == 'swap' and x[2] < 0]
    sells = [(x[1] - b0, round(x[2] / 1e18, 5), 'US' if x[3].lower() == RELAY else '') for x in e if x[0] == 'swap' and x[2] > 0]
    first = next((bo for bo, v, _ in buys if v >= 0.0002), None); pull = next((x[1] - b0 for x in e if x[0] == 'ml' and x[2] < 0), None)
    ours = [b for b in buys if b[2] == 'US']
    print(f"{datetime.datetime.fromtimestamp(o['t'], UTC).strftime('%H:%M:%S')} {o['kind']} fee {o['fee'] / 1e4:.3f}% ts {o['ts']} hooks {o['hooks']} | first real buy +{first}, {len(buys)} buys {sum(v for _, v, _ in buys):.4f} ETH, pull +{pull} | our buy {ours} our sell {[s for s in sells if s[2] == 'US']}")
    print('   buys (offset, eth):', buys[:14])
