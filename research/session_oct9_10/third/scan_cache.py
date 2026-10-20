"""one pass over cached blocks [lo,hi]: creation txs (created addr), txs of relayer 37bd8ddc / to bbd947c3 / to e33e9e47"""
from lib3 import *
import lib2; import bc
lo, hi = int(sys.argv[1]), int(sys.argv[2])
REL = '0x37bd8ddc5d977ce42a8180366ebe48bdd6d13a75'; EX = '0xbbd947c36904eb5f28aeaa5593fbcb5a228551ad'; RT = '0xe33e9e479df8802cb0866d5d05258bec4cf62948'
cre = []; rel = []; rt = []
for bn, ts, t in bc.txs(lo, hi):
    if t[2] == '':
        cre.append([bn, ts, t[0], t[1], t[4], caddr(t[1], t[4]), t[6]])
    if t[1] == REL or t[2] == EX: rel.append([bn, ts] + t)
    if t[2] == RT: rt.append([bn, ts] + t)
json.dump({'cre': cre, 'rel': rel, 'rt': rt}, open('cache_%d_%d.json' % (lo, hi), 'w'))
print(len(cre), len(rel), len(rt))
