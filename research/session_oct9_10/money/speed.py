import time
from tr import *
t0 = time.time(); r = blocks(84140000, 84140299); print(len(r), "txs in 300 blocks", round(time.time() - t0, 1), "s")
