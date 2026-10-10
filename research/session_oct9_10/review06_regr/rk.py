import json
src = open("../fe06.py").read()
s = src.index("def reply_kind"); e = src.index("SENDER = None")
ns = {}; exec(src[s:e], ns); rk = ns["reply_kind"]
for r in [{"error": "Too Many Requests"}, {"error": None}, {"error": {"code": 429, "message": "rate limited"}}, {"error": {"message": "send failed: x"}}, None, [], "x"]:
    try: print(repr(r), "->", rk(r))
    except Exception as ex: print(repr(r), "-> RAISES", type(ex).__name__, ex)
# what Sender produces from envoy's plain-text error bodies
for b in [b"local_rate_limited", b"no healthy upstream", b"upstream connect error or disconnect/reset before headers", b"", b"<html>429</html>"]:
    try: json.loads(b); print(b, "parses")
    except Exception as ex: print(b, "-> json error -> Sender returns error dict")
