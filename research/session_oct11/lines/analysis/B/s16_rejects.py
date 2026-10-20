"""Numbers for the rejected lines: the families with no or few first real buys (frb share), aggregated where one launcher selector covers
many small families (the 7fde822e launchpads), plus the big template families."""
from common import *
rows = load_rows()
def agg(name, f):
    rs = [r for r in rows if f(r)]
    if not rs: return
    fr = sum(1 for r in rs if r["frb"]); pl = sum(1 for r in rs if r["n_pulls"])
    print(f"{name}: launches {len(rs)} ({len(rs)/7:.0f}/d), first real buy in {fr} ({fr/len(rs):.1%}), pulled {pl} ({pl/len(rs):.0%})")
agg("selector 7fde822e launchpads (all lc)", lambda r: r["launch"]["selector"] == "7fde822e")
agg("tok:16afd61e (all launchers)", lambda r: r["fam"]["tok"].startswith("16afd61e"))
agg("tok:16afd61e via POSM multicall", lambda r: r["fam"]["tok"].startswith("16afd61e") and r["fam"]["lc"].startswith("c873e135") and r["fam"]["lc"].endswith("ac9650d8"))
agg("tok:58d59320 via EntryPoint handleOps (c93c806e|1fad948c)", lambda r: r["fam"]["tok"].startswith("58d59320") and r["fam"]["lc"].startswith("c93c806e"))
agg("tok:58d59320 via POSM multicall", lambda r: r["fam"]["tok"].startswith("58d59320") and r["fam"]["lc"].startswith("c873e135"))
agg("lc:cd37624e (hook 0xfcd18241, 6fe958d8/f8425a2f)", lambda r: r["fam"]["lc"].startswith("cd37624e"))
agg("lc:724433a2|7866fa39 (tok 695e20af)", lambda r: r["fam"]["lc"].startswith("724433a2"))
agg("tok:2dfcf583 (POSM initializePool)", lambda r: r["fam"]["tok"].startswith("2dfcf583"))
agg("tok:c0b7d400 via POSM multicall", lambda r: r["fam"]["tok"].startswith("c0b7d400") and r["fam"]["lc"].endswith("ac9650d8"))
agg("tok:97c7ba1b (v4 part)", lambda r: r["fam"]["tok"].startswith("97c7ba1b"))
agg("tok:cb79985d non-core (WETH/USDG/other fees)", lambda r: r["fam"]["tok"].startswith("cb79985d") and not (r["quote"] == "ETH" and r["fee"] == 100))
agg("C-2 template 4e451d1a via PM initialize, hookless core", lambda r: r["fam"]["tok"].startswith("4e451d1a") and r["fam"]["lc"].startswith("bd388118") and r["hooks"] == "0x" + "0" * 40 and r["fee"] == 500)
agg("every angle-B v4 pool", lambda r: True)
agg("angle-B lc#tok families with >= 10 launches and frb < 5%", lambda r: False)
