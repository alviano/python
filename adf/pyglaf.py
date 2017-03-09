#!/usr/bin/env python3

GPL = """
AF solver.
Copyright (C) 2017  Mario Alviano (mario@alviano.net)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

VERSION = "0.1"

import argparse
import fileinput
import re
import subprocess
import sys
import tempfile

arg = [None]
argName = {}
att = {}
attR = {}

def attacked(b):
    return len(arg)-1 + argName[b]

def inRange(b):
    return 2*(len(arg)-1) + argName[b]

def parseTGF(filename):
    sharp = False
    for line in fileinput.input(filename):
        line = line.strip()
        if line == '#':
            sharp = True
        elif not sharp:
            name = line
            if name not in argName:
                argName[name] = len(arg)
                arg.append(name)
        else:
            (a, b) = line.split()
            a = a
            b = b
            
            if a not in att: att[a] = set()
            att[a].add(b)
            
            if b not in attR: attR[b] = set()
            attR[b].add(a)

def parseAPX(filename):
    for line in fileinput.input(filename):
        res = parseAPX.re_atom.match(line)
        if not res: continue
        pred = res.group('predicate')
        if pred == 'arg':
            name = res.group('args')
            if name not in argName:
                argName[name] = len(arg)
                arg.append(name)
        elif pred == 'att':
            (a, b) = res.group('args').split(',')
            
            if a not in att: att[a] = set()
            att[a].add(b)
            
            if b not in attR: attR[b] = set()
            attR[b].add(a)
parseAPX.re_atom = re.compile('(?P<predicate>\w+)\((?P<args>[\w,]+)\)\.')

parseFunctions = {"tgf" : parseTGF, "apx" : parseAPX}

sol = '/home/malvi/workspaces/codelite/aspino/build/release/aspino'

def printModel(m):
    print('[', end='')
    print(','.join(m), end='')
    print(']', end='')
    sys.stdout.flush()

def DS(solver):
    while True:
        line = solver.stdout.readline()
        if not line: break
        line = line.decode().strip().split()
        if line[0] == 'v': print('NO')
        elif line[0] == 'UNSATISFIABLE': print('YES')

def DC(solver):
    while True:
        line = solver.stdout.readline()
        if not line: break
        line = line.decode().strip().split()
        if line[0] == 'v': print('YES')
        elif line[0] == 'UNSATISFIABLE': print('NO')

def SE(solver, end='\n'):
    while True:
        line = solver.stdout.readline()
        if not line: break
        line = line.decode().strip().split()
        if line[0] == 'v': printModel(line[1:])
        elif line[0] == 'UNSATISFIABLE': print('NO', end='')
    print(end=end)

def EE(solver, end='\n'):
    print('[', end='')
    count = 0
    while True:
        line = solver.stdout.readline()
        if not line: break
        line = line.decode().strip().split()
        if line[0] == 'v':
            if count != 0: print(',', end='')
            count += 1
            printModel(line[1:])
    print(']', end=end)

def DC_via_SE(solver, a):
    while True:
        line = solver.stdout.readline()
        if not line: break
        line = line.decode().strip().split()
        if line[0] == 'v':
            if a in line[1:]: print('YES')
            else: print('NO')

def DC_via_EE(solver, a):
    while True:
        line = solver.stdout.readline()
        if not line: break
        line = line.decode().strip().split()
        if line[0] == 'v':
            if a in line[1:]:
                print('YES')
                return
    print('NO')

def DS_via_EE(solver, a):
    while True:
        line = solver.stdout.readline()
        if not line: break
        line = line.decode().strip().split()
        if line[0] == 'v':
            if a not in line[1:]:
                print('NO')
                return
    print('YES')

def conflictFree(stream):
    for a in att:
        for b in att[a]:
            stream.write(("%d %d 0\n" % (-argName[a], -argName[b])).encode())

def buildAttacked(stream):
    for b in arg[1:]:
        cl = [str(-attacked(b))]
        if b in attR:
            for c in attR[b]:
                cl.append(str(argName[c]))
                stream.write(("%d %d 0\n" % (-argName[c], attacked(b))).encode())
        stream.write((' '.join(cl) + ' 0\n').encode())

def admissible(stream):
    for b in att:
        for a in att[b]:
            stream.write(("%d %d 0\n" % (-argName[a], attacked(b))).encode())

def complete(stream):
    for a in arg[1:]:
        cl = [str(argName[a])]
        if a in attR:
            for b in attR[a]:
                cl.append(str(-attacked(b)))
        stream.write((' '.join(cl) + ' 0\n').encode())

def stable(stream):
    for a in arg[1:]:
        cl = [str(argName[a])]
        if a in attR:
            for b in attR[a]:
                cl.append(str(argName[b]))
        stream.write((' '.join(cl) + ' 0\n').encode())

def buildRange(stream):
    for a in arg[1:]:
        cl = [str(-inRange(a)), str(argName[a])]
        if a in attR:
            for b in attR[a]:
                cl.append(str(argName[b]))
        stream.write((' '.join(cl) + ' 0\n').encode())

def credulous(stream, a):
    stream.write(("%d 0\n" % (argName[a],)).encode())

def skeptical(stream, a):
    stream.write(("-%d 0\n" % (argName[a],)).encode())

def nameTable(stream):
    for i in range(1, len(arg)):
        stream.write(('v %d %s\n' % (i, arg[i])).encode())

def CO(stream):
    stream.write('p ccnf -\n'.encode())
    stream.write('o 0\n'.encode())
    nameTable(stream)
    conflictFree(stream)
    buildAttacked(stream)
    admissible(stream)
    complete(stream)

def ST(stream):
    stream.write('p ccnf -\n'.encode())
    stream.write('o 0\n'.encode())
    nameTable(stream)
    conflictFree(stream)
    buildAttacked(stream)
    admissible(stream)
    complete(stream)
    stable(stream)

def PR(stream):
    stream.write('p ccnf +\n'.encode())
    stream.write(('o ' + ' '.join([str(i) for i in range(1, len(arg))]) + ' 0\n').encode())
    nameTable(stream)
    conflictFree(stream)
    buildAttacked(stream)
    admissible(stream)
    complete(stream)

def GR(stream):
    stream.write('p ccnf -\n'.encode())
    stream.write(('o ' + ' '.join([str(i) for i in range(1, len(arg))]) + ' 0\n').encode())
    nameTable(stream)
    conflictFree(stream)
    buildAttacked(stream)
    admissible(stream)
    complete(stream)

def SST(stream):
    stream.write('p ccnf +\n'.encode())
    stream.write(('o ' + ' '.join([str(inRange(i)) for i in arg[1:]]) + ' 0\n').encode())
    nameTable(stream)
    conflictFree(stream)
    buildAttacked(stream)
    admissible(stream)
    complete(stream)
    buildRange(stream)

def STG(stream):
    stream.write('p ccnf +\n'.encode())
    stream.write(('o ' + ' '.join([str(inRange(i)) for i in arg[1:]]) + ' 0\n').encode())
    nameTable(stream)
    conflictFree(stream)
    buildRange(stream)

def CAT(a):
    solver = subprocess.Popen(["cat"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    SST(solver.stdin)
    solver.stdin.close()
    
    while True:
        line = solver.stdout.readline()
        if not line: break
        print(line.decode(), end="")
    return

def DC_CO(a):
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=1', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    CO(solver.stdin)
    credulous(solver.stdin, a)
    solver.stdin.close()
    DC(solver)

def DS_CO(a):
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=1', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    CO(solver.stdin)
    skeptical(solver.stdin, a)
    solver.stdin.close()
    DS(solver)

def SE_CO():
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=1', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    CO(solver.stdin)
    solver.stdin.close()
    SE(solver)

def EE_CO():
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=0', '--circ-wit=0'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    CO(solver.stdin)
    solver.stdin.close()
    EE(solver)

def DC_PR(a):
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=1', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    PR(solver.stdin)
    credulous(solver.stdin, a)
    solver.stdin.close()
    DC(solver)

# The argument to be checked cannot be assumed false in counter-extensions, 
# so we are going to enumerate PR and check whether argument a is in all extensions
def DS_PR(a):
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=0', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    PR(solver.stdin)
    solver.stdin.close()
    DS_via_EE(solver, a)

def SE_PR():
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=1', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    PR(solver.stdin)
    solver.stdin.close()
    SE(solver)
    
def EE_PR(end='\n'):
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=0', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    PR(solver.stdin)
    solver.stdin.close()
    EE(solver, end=end)

def DC_ST(a):
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=1', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    ST(solver.stdin)
    credulous(solver.stdin, a)
    solver.stdin.close()
    DC(solver)

def DS_ST(a):
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=1', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    ST(solver.stdin)
    skeptical(solver.stdin, a)
    solver.stdin.close()
    DS(solver)

def SE_ST():
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=1', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    ST(solver.stdin)
    solver.stdin.close()
    SE(solver)

def EE_ST(end='\n'):
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=0', '--circ-wit=0'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    ST(solver.stdin)
    solver.stdin.close()
    EE(solver, end=end)

# The argument to be checked cannot be assumed true in counter-extensions, 
# so we are going to enumerate SST and check whether argument a is in some extension
def DC_SST(a):
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=0', '--circ-wit=0'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    SST(solver.stdin)
    solver.stdin.close()
    DC_via_EE(solver, a)

# The argument to be checked cannot be assumed false in counter-extensions, 
# so we are going to enumerate SST and check whether argument a is in all extensions
def DS_SST(a):
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=0', '--circ-wit=0'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    SST(solver.stdin)
    solver.stdin.close()
    DS_via_EE(solver, a)

def SE_SST():
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=1', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    SST(solver.stdin)
    solver.stdin.close()
    SE(solver)

def EE_SST():
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=0', '--circ-wit=0'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    SST(solver.stdin)
    solver.stdin.close()
    EE(solver)

# The argument to be checked cannot be assumed true in counter-extensions, 
# so we are going to enumerate STG and check whether argument a is in some extension
def DC_STG(a):
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=0', '--circ-wit=0'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    STG(solver.stdin)
    solver.stdin.close()
    DC_via_EE(solver, a)

# The argument to be checked cannot be assumed false in counter-extensions, 
# so we are going to enumerate STG and check whether argument a is in all extensions
def DS_STG(a):
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=0', '--circ-wit=0'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    STG(solver.stdin)
    solver.stdin.close()
    DS_via_EE(solver, a)

def SE_STG():
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=1', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    STG(solver.stdin)
    solver.stdin.close()
    SE(solver)

def EE_STG():
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=0', '--circ-wit=0'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    STG(solver.stdin)
    solver.stdin.close()
    EE(solver)

# Since GR is unique, let's compute it and check whether it contains argument a
def DC_GR(a):
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=1', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    GR(solver.stdin)
    solver.stdin.close()
    DC_via_SE(solver, a)

def SE_GR(end='\n'):
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=1', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    GR(solver.stdin)
    solver.stdin.close()
    SE(solver, end=end)

def DC_ID(a):
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=0', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    PR(solver.stdin)
    solver.stdin.close()

    target = a

    # compute the intersection of PR (naively)
    counter = {a : 0 for a in arg}
    count = 0
    while True:
        line = solver.stdout.readline()
        if not line: break
        line = line.decode().strip().split()
        if line[0] == 'v':
            count += 1
            for a in line[1:]: counter[a] += 1
            
            # check if target is still in PR
            if counter[target] != count:
                print('NO')
                return
    
    # force falsity of atoms not in PR and maximize over admissible extensions
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=1', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    solver.stdin.write('p ccnf +\n'.encode())
    solver.stdin.write(('o ' + ' '.join([str(i) for i in range(1, len(arg)) if counter[arg[i]] == count]) + ' 0\n').encode())
    nameTable(solver.stdin)
    conflictFree(solver.stdin)
    buildAttacked(solver.stdin)
    admissible(solver.stdin)
    for i in range(1, len(arg)):
        if counter[arg[i]] < count: solver.stdin.write((str(-i) + ' 0\n').encode())
    
    # we cannot add the target as false because we are maximizing; however, since ID is unique, we can force the truth of the target
    credulous(solver.stdin, target)
    solver.stdin.close()
    DC(solver)

def SE_ID():
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=0', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    PR(solver.stdin)
    solver.stdin.close()

    # compute the intersection of PR (naively)
    counter = {a : 0 for a in arg}
    count = 0
    while True:
        line = solver.stdout.readline()
        if not line: break
        line = line.decode().strip().split()
        if line[0] == 'v':
            count += 1
            for a in line[1:]: counter[a] += 1
    
    # force falsity of atoms not in PR and maximize over admissible extensions
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=1', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    solver.stdin.write('p ccnf +\n'.encode())
    solver.stdin.write(('o ' + ' '.join([str(i) for i in range(1, len(arg)) if counter[arg[i]] == count]) + ' 0\n').encode())
    nameTable(solver.stdin)
    conflictFree(solver.stdin)
    buildAttacked(solver.stdin)
    admissible(solver.stdin)
    for i in range(1, len(arg)):
        if counter[arg[i]] < count: solver.stdin.write((str(-i) + ' 0\n').encode())
    solver.stdin.close()
    SE(solver)

def isStable(e):
    for a in arg[1:]:
        if a in e: continue
        if a not in attR: continue
        ok = False
        for b in attR[a]:
            if b in e:
                ok = True
                break
        if not ok: return False
    return True

# GR is contained in the intersection of PR, and ST is a subset of PR.
# Hence, we first compute GR, then force truth of GR and enumerate PR.
# For each extension in PR, stability is checked.
def D3():
    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=1', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    GR(solver.stdin)
    solver.stdin.close()
    gr = None
    while True:
        line = solver.stdout.readline()
        if not line: break
        line = line.decode().strip().split()
        if line[0] == 'v': gr = line[1:]
    
    assert gr is not None
    print('[', end='')
    printModel(gr)
    print('],', end='')
    sys.stdout.flush()

    solver = subprocess.Popen([sol, '--mode=circumscription', '-n=0', '--circ-wit=1'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    PR(solver.stdin)
    for a in gr: solver.stdin.write((str(argName[a]) + ' 0\n').encode())
    solver.stdin.close()
    print('[', end='')
    count = 0
    pr = []
    while True:
        line = solver.stdout.readline()
        if not line: break
        line = line.decode().strip().split()
        if line[0] == 'v':
            pr.append(line[1:])
            if isStable(line[1:]):
                if count != 0: print(',', end='')
                count += 1
                printModel(line[1:])
    print('],', end='')
    sys.stdout.flush()
    
    print('[', end='')
    count = 0
    for m in pr:
        if count != 0: print(',', end='')
        count += 1
        print('[' + ','.join(m) + ']', end='')
    print(']')

problemFunctions = {
    "DC-CO" : DC_CO, "DS-CO" : DS_CO, "SE-CO" : SE_CO, "EE-CO" : EE_CO,
    "DC-PR" : DC_PR, "DS-PR" : DS_PR, "SE-PR" : SE_PR, "EE-PR" : EE_PR,
    "DC-ST" : DC_ST, "DS-ST" : DS_ST, "SE-ST" : SE_ST, "EE-ST" : EE_ST,
    "DC-SST" : DC_SST, "DS-SST" : DS_SST, "SE-SST" : SE_SST, "EE-SST" : EE_SST,
    "DC-STG" : DC_STG, "DS-STG" : DS_STG, "SE-STG" : SE_STG, "EE-STG" : EE_STG,
    "DC-GR" : DC_GR, "SE-GR" : SE_GR,
    "DC-ID" : DC_ID, "SE-ID" : SE_ID,
    "D3": D3  #, "CAT": CAT
}


def parseArguments():
    global VERSION
    global GPL
    parser = argparse.ArgumentParser(description=GPL.split("\n")[1], epilog="Copyright (C) 2017  Mario Alviano (mario@alviano.net)")
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + VERSION, help='print version number')
    parser.add_argument('--formats', action='store_true', help='print supported formats and exit')
    parser.add_argument('--problems', action='store_true', help='print supported computational problems and exit')
    parser.add_argument('-p', metavar='<task>', type=str, help='')
    parser.add_argument('-f', metavar='<file>', type=str, help='')
    parser.add_argument('-fo', metavar='<fileformat>', type=str, help='')
    parser.add_argument('-a', metavar='<additional_parameter>', type=str, help='')
    args = parser.parse_args()
    if args.formats: 
        print('[%s]' % ','.join(sorted(parseFunctions.keys())))
        sys.exit()
    if args.problems:
        print('[%s]' % ','.join(sorted(problemFunctions.keys())))
        sys.exit()
    return args


    

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("af.py", VERSION)
        print("Mario Alviano")
        sys.exit()
    args = parseArguments()
    
    if args.fo is None: sys.exit("Please, specify a format.")
    if args.p is None: sys.exit("Please, specify a problem.")
    if args.f is None: sys.exit("Please, specify an input file.")
    
    if not args.fo in parseFunctions: sys.exit("Unsopported format: " + args.fo)
    if not args.p in problemFunctions: sys.exit("Unsopported problem: " + args.p)

    parseFunctions[args.fo](args.f)
    if args.a:
        problemFunctions[args.p](args.a)
    else:
        problemFunctions[args.p]()
