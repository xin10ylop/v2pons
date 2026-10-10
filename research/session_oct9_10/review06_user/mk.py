"""make a scenario dir: results.py with its paths pointed into the dir"""
import sys, os, json, gzip, time, re
S = os.path.dirname(os.path.abspath(__file__))
def make(name, version, files, env=None, halt=None):
    d = os.path.join(S, "sc", name); os.makedirs(d, exist_ok=True)
    for f in os.listdir(d): os.remove(os.path.join(d, f))
    src = open(os.path.join(S, version)).read()
    src = src.replace("/var/log/flip/engine.jsonl", d + "/engine.jsonl").replace("/etc/flip/engine.env", d + "/engine.env").replace("/var/log/flip/HALTED", d + "/HALTED")
    open(os.path.join(d, "results.py"), "w").write(src)
    for fn, lines in files.items():
        data = "".join((l if isinstance(l, str) else json.dumps(l, separators=(",", ":"))) + "\n" for l in lines)
        if fn.endswith(".gz"):
            with gzip.open(os.path.join(d, fn), "wt") as f: f.write(data)
        else:
            open(os.path.join(d, fn), "w").write(data)
    if env is not None: open(os.path.join(d, "engine.env"), "w").write(env)
    if halt is not None: open(os.path.join(d, "HALTED"), "w").write(halt)
    return d
