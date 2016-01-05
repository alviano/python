#!/usr/bin/env python3

import sys
import os
from pyparsing import *
import fractions

encoding = []
objectFunctions = []

def getId(tokens):
    var = "".join(tokens)
    if var not in getId.idMap:
        getId.idMap[var] = len(getId.idVec)
        getId.idVec.append(var)
    return getId.idMap[var]
getId.idMap = {}
getId.idVec = [0]

def getIdUnary(v):
    global encoding
    #res = getId(["(!%d)" % v])
    res = getId(["(!%s)" % getId.idVec[v]])
    encoding.append("-%d -%d 0" % (res, v))
    encoding.append("%d %d 0" % (res, v))
    return res

def andClauses(x, l1, l2):
    global encoding
    encoding.append("-%d %d 0" % (x, l1))
    encoding.append("-%d %d 0" % (x, l2))
    encoding.append("%d -%d -%d 0" % (x, l1, l2))

def orClauses(x, l1, l2):
    global encoding
    encoding.append("-%d %d %d 0" % (x, l1, l2))
    encoding.append("%d -%d 0" % (x, l1))
    encoding.append("%d -%d 0" % (x, l2))

def implicationClauses(x, l1, l2):
    global encoding
    encoding.append("-%d -%d %d 0" % (x, l1, l2))
    encoding.append("%d %d 0" % (x, l1))
    encoding.append("%d -%d 0" % (x, l2))

def equivalentClauses(x, l1, l2):
    global encoding
    encoding.append("-%d -%d %d 0" % (x, l1, l2))
    encoding.append("-%d -%d %d 0" % (x, l2, l1))
    encoding.append("%d -%d -%d 0" % (x, l1, l2))
    encoding.append("%d %d %d 0" % (x, l1, l2))

def getIdBinary(l, op, r):
    #res = getId(["(%d%s%d)" % (l, op, r)])
    res = getId(["(%s%s%s)" % (getId.idVec[l], op, getId.idVec[r])])
    {
        "&" : andClauses,
        "|" : orClauses,
        "->" : implicationClauses,
        "<->" : equivalentClauses
    }[op](res, l, r)
    return res

def cnf(phi):
    if type(phi) is int:
        return phi
    if len(phi) == 1:
        return cnf(phi[0])
    if len(phi) == 2:
        return getIdUnary(cnf(phi[1]))
    if len(phi) == 3:
        return getIdBinary(cnf(phi[0]), phi[1], cnf(phi[2]))
    if len(phi) % 2 == 1:
        r = getIdBinary(cnf(phi[-3]), phi[-2], cnf(phi[-1]))
        phi = phi[0:-3]
        phi.append(r)
        return cnf(phi)
    else:
        print("Error producing cnf")
        #print(len(phi))
        #print(phi)
        exit(-1)

def buildObjectFunction(agent):
    ret = ([], [])
    for f in agent:
        var = wff.parseString(f[0])[0]
        ret[0].append(str(cnf(var)))
        ret[1].append(str(f[1]))
    return "%d %s %s 0" % (len(ret[0]), " ".join(ret[0]), " ".join(ret[1]))

wff = Forward()

variable = Word(alphas, alphanums+"_")
variable.setParseAction(getId)

atom = Group(Optional("!") + (variable | Suppress("(") + wff + Suppress(")")))

wff_and = Group(atom + ZeroOrMore("&" + atom))
wff_or = Group(wff_and + ZeroOrMore("|" + wff_and))
wff_imp = Group(wff_or + ZeroOrMore("->" + wff_or))
wff << (Group(wff_imp + ZeroOrMore("<->" + wff_imp)))

if __name__ == "__main__":
    if len(sys.argv) == 2:
        if not os.path.exists(sys.argv[1]):
            sys.exit("File not found: %s" % (sys.argv[1],))
        exec(open(sys.argv[1]).read())
        if 'gamma' not in locals():
            sys.exit("File %s does not provide theory gamma" % (sys.argv[1],))
        if 'agents' not in locals():
            sys.exit("File %s does not provide agents" % (sys.argv[1],))
            
        for f in gamma:
            phi = wff.parseString(f)[0]
            encoding.append("%d 0" % cnf(phi))

        n = 1
        d = None
        count = 0
        for agent in agents:
            for f in agent:
                if len(f) == 3 and f[2] != 1:
                    count = count + 1
                    n = n * f[2]
                    d = fractions.gcd(d, f[2]) if d is not None else f[2]
        if count >= 2: n = int(n/d)
        for agent in agents:
            for f in agent:
                if len(f) == 3:
                    f[1] = f[1] * int(n/f[2])
                    f[2] = 1
                else:
                    f[1] = f[1] * n
                        
        for agent in agents:
            objectFunctions.append(buildObjectFunction(agent))
        
        print("p fcnf %d %d %d" % (len(getId.idVec)-1, len(encoding), len(objectFunctions)))
        for i in range(1, len(getId.idVec)):
            print("c %d %s" % (i, getId.idVec[i]))
        for cl in encoding:
            print(cl)
        for f in objectFunctions:
            print(f)
        
    else:
        print("usage:")
        print("\t%s <theory file>" % sys.argv[0])
        print("where")
        print("\ttheory file\t\tis a file defining a set of wffs")
        exit(-1)
