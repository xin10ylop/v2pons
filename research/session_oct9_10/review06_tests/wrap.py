import sys, runpy
sys.setswitchinterval(float(sys.argv[1]))
runpy.run_path(sys.argv[2], run_name="__main__")
