import sys; sys.path.insert(0,".")
from sim import sim, mapslot, allowslot, h32, xfer, TOK, DEAD, W, C, SLOT6
# fresh random addresses, give each a balance, transfer
import os
fresh=["0x"+os.urandom(20).hex() for _ in range(6)]
print("== fresh EOAs given a balance, then transfer(dead,1000) ==")
for z in fresh:
    r=sim(z, {TOK:{"stateDiff":{mapslot(z,0):h32(10**15)}}})
    print(" ",z, r)
print()
# crowd2..crowdN transfer baseline
for name,a in [("crowdL+120","0xb27ad6a5c4b1b71e04fda767b5ba2577e0950ffb"),
               ("crowdL+177","0x6addb9d2dafd3805f2b89bb436b622d6c1d25f8d"),
               ("crowdL+65 ","0x5339668e4dece6f25645b117265a465859672487")]:
    print(" ",name, a, sim(a))
print()
print("E6  US allow[W][slot6]=MAX :", sim(W, {TOK:{"stateDiff":{allowslot(W,SLOT6):h32((1<<256)-1)}}}))
print("E6c US allow[W][slot6]=1000:", sim(W, {TOK:{"stateDiff":{allowslot(W,SLOT6):h32(1000)}}}))
print("E9  US slot6:=randomAddr   :", sim(W, {TOK:{"stateDiff":{h32(6):"0x"+os.urandom(20).hex().rjust(64,'0')}}}))
print("E10 US slot6:=slot6 (noop) :", sim(W))
# give US a balance AND set allowance to slot6 max
print("E11 US bal+allow[W][s6]=MAX:", sim(W, {TOK:{"stateDiff":{mapslot(W,0):h32(10**15), allowslot(W,SLOT6):h32((1<<256)-1)}}}))
