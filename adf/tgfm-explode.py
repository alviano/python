#!/usr/bin/env python3

from collections import OrderedDict
import fileinput
import sys

arg = [None]
argToIdx = {}
att = OrderedDict()

dynAtt = OrderedDict()
dynAttList = []
def parseTGF(filename):
    sharp = False
    for line in fileinput.input(filename):
        line = line.strip()
        if not line: continue
        if line == '#':
            sharp = True
        elif not sharp:
            name = line
            if name not in argToIdx:
                argToIdx[name] = len(arg)
                arg.append(name)
        else:
            (a, b) = line.split()
            att[(a,b)] = None

def parseTGFM(filename):
    i = 0
    for line in fileinput.input(filename):
        i += 1
        line = line.strip()
        if not line: continue
        sign = line[0] == '+'
        (a, b) = line[1:].split()

        if sign: att[(a,b)] = None
        else: del att[(a,b)]

        printTGF(filename, i)

def printTGF(filename, count):
    filename = "{}.{}.tgf".format(filename,count)
    print("Create file {}".format(filename))
    file = open(filename, "w")
    for a in arg[1:]: file.write("{}\n".format(a))
    file.write("#\n")
    for (a,b) in att: file.write("{} {}\n".format(a, b))
    file.close()

if len(sys.argv) != 3: sys.exit("Please, provide TGF and TGFM files.")
parseTGF(sys.argv[1])
printTGF(sys.argv[2], 0)
parseTGFM(sys.argv[2])
