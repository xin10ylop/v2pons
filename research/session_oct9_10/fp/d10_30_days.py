import sys, json, datetime
sys.path.insert(0, '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad')
from chain import *
A, B = 59391955, 77007489
ts = lambda n: int(rpc('eth_getBlockByNumber', [hex(n), False])['timestamp'], 16)
ta, tb = ts(A), ts(B)
print(A, datetime.datetime.utcfromtimestamp(ta), B, datetime.datetime.utcfromtimestamp(tb))
d = datetime.datetime.utcfromtimestamp(ta).date() + datetime.timedelta(days=1)
bounds = {}
while True:
    mid = int(datetime.datetime(d.year, d.month, d.day, tzinfo=datetime.timezone.utc).timestamp())
    if mid > tb: break
    lo, hi = A, B
    while lo < hi:
        m = (lo + hi) // 2
        if ts(m) < mid: lo = m + 1
        else: hi = m
    bounds[str(d)] = lo
    print(d, lo, ts(lo), ts(lo - 1), flush=True)
    d += datetime.timedelta(days=1)
json.dump({'A': A, 'B': B, 'tsA': ta, 'tsB': tb, 'first_block_of_day': bounds}, open('/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/fp/d10_30_days.json', 'w'), indent=1)
