"""Family definitions for analyst C (V2/V3). fam_pools(R) -> {name: [rows sorted by launch block]} (V2/V3 rows only unless noted)."""
import pickle, os
OUT = os.path.dirname(os.path.abspath(__file__))
FAMS = [
    ("tok:0f34e3b5", lambda r: r["fam"]["tok"].startswith("0f34e3b5")),
    ("lc:0a493d1a|13ead562", lambda r: (r["fam"]["lc"] or "").startswith("0a493d1a") and r["fam"]["lc"].endswith("|13ead562")),
    ("lc:89885b75|d27d1e00", lambda r: (r["fam"]["lc"] or "").startswith("89885b75") and r["fam"]["lc"].endswith("|d27d1e00")),
    ("tok:97c7ba1b", lambda r: r["fam"]["tok"].startswith("97c7ba1b")),
    ("lc:0a493d1a|ac9650d8", lambda r: (r["fam"]["lc"] or "").startswith("0a493d1a") and r["fam"]["lc"].endswith("|ac9650d8")),
    ("lc:bd55ea26|f305d719", lambda r: (r["fam"]["lc"] or "").startswith("bd55ea26") and r["fam"]["lc"].endswith("|f305d719")),
    ("tok:70adce63", lambda r: r["fam"]["tok"].startswith("70adce63")),
    ("tok:d4e7eae4", lambda r: r["fam"]["tok"].startswith("d4e7eae4")),
    ("lc:cecb292d|8cb5772c", lambda r: (r["fam"]["lc"] or "").startswith("cecb292d") and r["fam"]["lc"].endswith("|8cb5772c")),
    ("tok:2be340ff", lambda r: r["fam"]["tok"].startswith("2be340ff")),
    ("tok:fbe37854", lambda r: r["fam"]["tok"].startswith("fbe37854")),
    ("tok:ad9da489", lambda r: r["fam"]["tok"].startswith("ad9da489")),
    ("tok:884da06b", lambda r: r["fam"]["tok"].startswith("884da06b")),
    ("tok:02b73fb7", lambda r: r["fam"]["tok"].startswith("02b73fb7")),
    ("tok:0a600ad0", lambda r: r["fam"]["tok"].startswith("0a600ad0")),
    ("tok:1d7cd90a", lambda r: r["fam"]["tok"].startswith("1d7cd90a")),
    ("tok:c40bd4ef", lambda r: r["fam"]["tok"].startswith("c40bd4ef")),
    ("tok:516ca2d6", lambda r: r["fam"]["tok"].startswith("516ca2d6")),
    ("tok:cb79985d", lambda r: r["fam"]["tok"].startswith("cb79985d")),
    ("tok:a8dbcb39", lambda r: r["fam"]["tok"].startswith("a8dbcb39")),
    ("lc:b09ef517|e9ae5c53", lambda r: (r["fam"]["lc"] or "").startswith("b09ef517")),
    ("launchpad-frb:fa4982d5", lambda r: r["fam"]["tok"].startswith("fa4982d5") and r["frb"] is not None),
    ("lc:cecb292d|2e2fdbd9", lambda r: (r["fam"]["lc"] or "").startswith("cecb292d") and r["fam"]["lc"].endswith("|2e2fdbd9")),
]
def load_rows():
    return pickle.load(open(os.path.join(OUT, "v23.pkl"), "rb"))
def fam_pools(R, v23_only=True):
    out = {}
    for name, f in FAMS:
        rs = [r for r in R.values() if (not v23_only or r["dex"] != "v4") and not r["quote_pair"] and f(r)]
        out[name] = sorted(rs, key=lambda r: (r["launch_block"], r["launch_ti"] or 0))
    return out
