import sys; sys.path.insert(0,".")
from sim import sim, allowslot, h32, mapslot, TOK, W, C
from rpc import URLS, _one
X="0xbd418ce6a83995971de9f1cf9f61f345e91aeadd"
def tv(v): return sim(C, {TOK:{"stateDiff":{allowslot(X,C):h32(v)}}})
print("odd/even bit test on allowance[X][crowd] (crowd, should revert iff odd):")
for v in [0,1,2,3,4,5,6,0xfe,0xff,2**255,2**255+1,(1<<256)-2,(1<<256)-1]:
    print(f"  v={v:>78} {'ODD ' if v&1 else 'EVEN'} ->", tv(v))
# time: does a far-future block/timestamp lift US freeze? (proper block override)
def sim_block(frm):
    call={"from":frm,"to":TOK,"data":"0xa9059cbb"+"000000000000000000000000000000000000dead"+hex(1000)[2:].rjust(64,'0')}
    body={"jsonrpc":"2.0","id":1,"method":"eth_simulateV1","params":[{"blockStateCalls":[
        {"blockOverrides":{"number":hex(127550490+5000000),"time":hex(3000000000)},"calls":[call]}],"validation":False},"latest"]}
    for U in URLS:
        try:
            r=_one(U,body)
            if "result" in r: c=r["result"][0]["calls"][0]; return f"status={c.get('status')} err={c.get('error')}"
            else: return "top-err "+str(r.get('error'))[:60]
        except Exception as e: return "exc "+str(e)[:50]
print("\nUS transfer at block L+5,000,000 / ts year2065:", sim_block(W), "(freeze is time-independent)")
