"""Skeptic 1, step 9: the block rate (wall-clock length of the hold) and the cap variants the replay analyst quoted (their 'cap N' = the cap's
sell sent at + N, landing + 2), at 0.0058 ETH over their replay window. -> k09_extra.out"""
import json, os, statistics as st, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import k05_replay as K
D = json.load(open(os.path.join(HERE, 'k05_rows.json'))); rows = D['rows']
bps = (D['head'] - 84980908) / (D['t_head'] - 1791633600)
print(f"block rate {bps:.2f} blocks/s: the cap (+80) is {80 / bps:.1f} s after the launch; the earliest pull (+86) {86 / bps:.1f} s; 6 blocks = {6 / bps:.2f} s")
win = [r for r in rows if 1791633600 < r['ts'] <= 1791815412]
for send in (58, 60, 68, 70, 76, 78, 86, 88, 96, 98):
    rs = [K.trade(r['pool'], int(0.0058e18), 2, 2, CAP_SEND=send) for r in win]
    print(f"replay window, 0.0058, cap send +{send} (sell at +{send + 2}): mean {st.mean(x['ret'] for x in rs)*100:+.2f}%, pulled {sum(x['pulled'] for x in rs)}")
