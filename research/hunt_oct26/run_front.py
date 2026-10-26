#!/usr/bin/env python3
"""run_front.py CHAIN [PARALLEL]: front.py on every census day in out/ that has no front_ output yet (out/front_CHAIN_YYYYMMDD_HH.json/.txt)."""
import sys, os, glob, subprocess, concurrent.futures as cf

ch = sys.argv[1]; par = int(sys.argv[2]) if len(sys.argv) > 2 else 2
here = os.path.dirname(os.path.abspath(__file__))
todo = [f for f in sorted(glob.glob(os.path.join(here, f"out/{ch}_2*.json")))
        if not os.path.exists(f.replace(f"/{ch}_", f"/front_{ch}_"))]


def one(f):
    out = f.replace(f"/{ch}_", f"/front_{ch}_")
    p = subprocess.run(["python3", "front.py", f, out], cwd=here, capture_output=True, text=True, timeout=7200,
                       env=dict(os.environ, SKIP_KNOWN=os.environ.get("SKIP_KNOWN", "")))
    open(out[:-5] + ".txt", "w").write(p.stdout + p.stderr[-2000:])
    return os.path.basename(f), p.returncode


with cf.ThreadPoolExecutor(par) as ex:
    for name, rc in ex.map(one, todo):
        print(name, "ok" if rc == 0 else f"rc {rc}", flush=True)
