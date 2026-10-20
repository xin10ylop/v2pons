import sys; sys.path.insert(0,".")
from sim import sim, allowslot, h32, TOK, W, C
X="0xbd418ce6a83995971de9f1cf9f61f345e91aeadd"
MAX=(1<<256)-1
# Confirm direction: allowance[X][from] gates. slot = allowslot(owner=X, spender=from)
print("P1 US, zero allow[X][US]      :", sim(W, {TOK:{"stateDiff":{allowslot(X,W):h32(0)}}}), " (expect PASS)")
print("P2 CROWD, set allow[X][crowd]=MAX:", sim(C, {TOK:{"stateDiff":{allowslot(X,C):h32(MAX)}}}), " (expect REVERT)")
print("P3 CROWD, set allow[X][crowd]=1  :", sim(C, {TOK:{"stateDiff":{allowslot(X,C):h32(1)}}}), " (nonzero?)")
print("P4 CROWD, set allow[X][crowd]=2  :", sim(C, {TOK:{"stateDiff":{allowslot(X,C):h32(2)}}}))
print("P5 US, allow[X][US]=1            :", sim(W, {TOK:{"stateDiff":{allowslot(X,W):h32(1)}}}))
print("P6 US, allow[X][US]=MAX-1        :", sim(W, {TOK:{"stateDiff":{allowslot(X,W):h32(MAX-1)}}}))
# reverse direction sanity: allowance[from][X]
print("P7 US, allow[US][X]=MAX (reverse):", sim(W, {TOK:{"stateDiff":{allowslot(W,X):h32(MAX)}}}), " (expect still REVERT, irrelevant dir)")
