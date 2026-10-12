"""Judge 2 helpers (C-1 short-exit dispute). Reuses ../../common.py and the paced ../../rpc.py unchanged (one POST >= 0.5 s apart, read
methods only, back-off on 429); only its log is redirected here. Read-only: no key, no transaction, public RPC only.
Caches used as DATA: ../s02_pools.json (swaps, pulls), ../../c03_txs.jsonl + ../s01_txs_new.jsonl (router calldata), ../../c04_ours.json."""
import os, sys, json
_ME = os.path.dirname(os.path.abspath(__file__)); _SHORT = os.path.dirname(_ME); _C1 = os.path.dirname(_SHORT)
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_C1))), "src")
sys.path.insert(0, _C1); sys.dont_write_bytecode = True
from common import *          # noqa: F401,F403
import rpc
rpc.LOG = os.path.join(_ME, "rpc_log.jsonl")
JD = lambda n: os.path.join(_ME, n)          # judge 2 outputs
SH = lambda n: os.path.join(_SHORT, n)       # the analyst's caches (data only)
sys.path.insert(0, _SRC)
import v4math                                # the engine's own swap math (src/v4math.py)
