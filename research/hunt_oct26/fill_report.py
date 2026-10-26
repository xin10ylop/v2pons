#!/usr/bin/env python3
"""fill_report.py: refresh the generated blocks of REPORT_HUNT.md (coverage, the two line tables) from out/, and write the quoted outputs
(*.out) beside the scripts. Run after the sweeps, verdicts.py and summarize.py."""
import os, re, subprocess

here = os.path.dirname(os.path.abspath(__file__))
run = lambda *a: subprocess.run(["python3", *a], cwd=here, capture_output=True, text=True).stdout
cov = run("coverage.py")
rows = ["| chain | days | native pools created | pulled within 2 h | round trips (entered within 20 s) | line-days tested |", "|---|---|---|---|---|---|"]
for line in cov.splitlines():
    m = re.match(r"(\w+): (\d+) days \((\d+)\.\.(\d+)\), ([\d,]+) native pools created, ([\d,]+) pulled within 2 h, ([\d,]+) round trips \(([\d,]+) entered within 20 s\), (\d+) line-days", line)
    if m:
        ch, n, a, b, cr, pu, rt, ea, ld = m.groups()
        rows.append(f"| {'Robinhood' if ch == 'rh' else 'Base'} | {n} ({a[4:6]}/{a[6:8]} - {b[4:6]}/{b[6:8]}) | {cr} | {pu} | {rt} ({ea}) | {ld} |")
blocks = {"COVERAGE": "\n".join(rows), "TABLE_RH": run("tables.py", "rh").strip(), "TABLE_BASE": run("tables.py", "base").strip()}
p = os.path.join(here, "REPORT_HUNT.md"); s = open(p).read()
for k, v in blocks.items():
    s = re.sub(rf"<!-- {k} -->.*?<!-- /{k} -->", lambda _: f"<!-- {k} -->\n{v}\n<!-- /{k} -->", s, flags=re.S)
open(p, "w").write(s)
for name, args in (("coverage.out", ["coverage.py"]), ("verdicts_rh.out", ["verdicts.py", "rh"]), ("verdicts_base.out", ["verdicts.py", "base"]),
                   ("summarize_rh.out", ["summarize.py", "rh"]), ("summarize_base.out", ["summarize.py", "base"])):
    open(os.path.join(here, name), "w").write(run(*args))
print(blocks["COVERAGE"])
