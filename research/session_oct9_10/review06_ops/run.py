import sys, runpy, time
sys.argv = ["results.py", "24"]
mod = {}
src = open(sys.argv[0] if False else "%s/results_c2d.py" % sys.path[0]).read()
src = src.replace('LOG = "/var/log/flip/engine.jsonl"; ENV = "/etc/flip/engine.env"', 'LOG = "%s/log/engine.jsonl"; ENV = "%s"' % (sys.path[0], sys.argv[1] if len(sys.argv)>1 else "/nonexistent"))
