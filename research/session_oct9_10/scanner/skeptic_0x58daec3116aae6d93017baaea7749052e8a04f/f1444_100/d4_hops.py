# follow single hops: python d4_hops.py <addr> <from_block> <to_block>  -> every tx touching addr in the range
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from d1_scan import scan
a = sys.argv[1].lower(); A = int(sys.argv[2]); B = int(sys.argv[3])
for x in scan(A, B, [a], 'hop_' + a[:10]):
    print(x['bn'], x['frm'], '->', x['to'], round(x['value'] / 1e18, 6), 'n', x['nonce'], x['sel'], x['clen'], 'touch', [w[:10] for w in x['which']])
