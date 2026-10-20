"""Judge 1 helpers (session_oct12/c1/short/judge1). Reuses ../../common.py and the paced ../../rpc.py unchanged (one POST >= 0.5 s apart,
read methods only, back-off on 429, public RPC only); only its log is redirected here. Read-only; no key, no transaction."""
import os, sys, json
_ME = os.path.dirname(os.path.abspath(__file__)); _SHORT = os.path.dirname(_ME); _C1 = os.path.dirname(_SHORT)
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_C1))), "src")
sys.path.insert(0, _C1); sys.dont_write_bytecode = True
from common import *          # noqa: F401,F403
import rpc
rpc.LOG = os.path.join(_ME, "rpc_log.jsonl")
JD = lambda n: os.path.join(_ME, n)          # judge 1 outputs
SH = lambda n: os.path.join(_SHORT, n)      # the analyst's caches (data only)
sys.path.insert(0, _SRC)
import v4math                               # the engine's own swap math (src/v4math.py)
