#!/usr/bin/env python3

GPL = """
Instantiate ASP programs in order to compute G-stable models by means of ordinary ASP solvers.
Copyright (C) 2015  Mario Alviano (mario@alviano.net)

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

VERSION = "0.2"

import argparse
import scc
import subprocess
import sys
import tempfile

def parseArguments():
    global VERSION
    global GPL
    global dependencies
    global auxOf
    parser = argparse.ArgumentParser(description=GPL.split("\n")[1], epilog="Copyright (C) 2015  Mario Alviano (mario@alviano.net)")
    parser.add_argument('--help-syntax', action='store_true', help='print syntax description and exit') 
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + VERSION, help='print version number')
    parser.add_argument('-g', '--grounder', metavar='<grounder>', type=str, help='path to the gringo 3 (default \'gringo\')')
    parser.add_argument('-d', '--dependencies', action='store_true', help='handle positive dependencies')
    parser.add_argument('-a', '--smart-auxiliaries', action='store_true', help='reuse auxiliary atoms')
    parser.add_argument('args', metavar="...", nargs=argparse.REMAINDER, help="arguments for <grounder>")
    args = parser.parse_args()
    if args.help_syntax: helpSyntax()
    if not args.grounder: args.grounder = 'gringo'
    if args.dependencies: dependencies = {}
    if args.smart_auxiliaries: auxOf = {}
    return args

def helpSyntax():
    print("""
The syntax is almost conformant to ASP Core 2.0, with the exception of aggregates.
Moreover, predicates starting with the prefix 'f_' are reserved for internal use
and must not be used by the user. Remember also to not hide them!


Supported aggregates are COUNT, SUM, AVG, MIN, and MAX. Aggregate sets are
declared by means of predicate f_set/3, where:

- the first argument is the ID of an aggregate;

- the second argument is an integer;

- the third argument is an atom.

The second argument is optional, with default value 1.


A COUNT aggregate can be added in a rule body by using predicate f_count/3, where:

- the first argument is the ID of an aggregate;

- the second argument is a comparator among ">=", ">", "<=", "<", "=", "!=";

- the third argument is an integer.


Aggregates SUM, AVG, MIN, and MAX are similar, and use predicates f_sum/3, f_avg/3,
f_min/3, and f_max/3.


Remember that COUNT is applied on true atoms in the aggregate set, while SUM, AVG, 
MIN, and MAX are applied on the multiset of integers associated with true atoms in
the aggregate set.


Variables can be used taking into account the previous description.
    """)
    sys.exit()

dependencies = None
component = None

id2name = {}
name2id = {}

program = []
aggregateSets = {}
sums = {}
avgs = {}
mins = {}
maxs = {}
odds = {}
evens = {}

aux = []
maxId = 0
auxOf = None

def getAuxOf(a):
    global maxId
    if auxOf is None:
        maxId = maxId + 1
        return maxId
    if a not in auxOf:
        maxId = maxId + 1
        auxOf[a] = maxId
    return auxOf[a]

def addDependency(a, b):
    assert dependencies is not None
    if a not in dependencies: dependencies[a] = set()
    dependencies[a].add(b)

def addDependencies(a, b):
    assert dependencies is not None
    if a not in dependencies: dependencies[a] = set()
    dependencies[a] = dependencies[a].union(b)
    
def areRecursive(a, b):
    if dependencies is None: return True
    return component[a] == component[b]

def readProgram(line):
    global maxId
    num = [int(a) for a in line]
    maxId = max(maxId, max(num))
    program.append(num)
    
    if dependencies is not None:
        if num[0] == 1:
            if num[1] != 1:
                for i in num[4+num[3]:]:
                    addDependency(num[1], i)
        elif num[0] == 2:
            for i in num[5+num[3]:]:
                addDependency(num[1], i)
        elif num[0] == 5:
            for i in num[5+num[4]:5+num[3]]:
                addDependency(num[1], i)
        elif num[0] == 3 or num[0] == 8:
            s = set()
            for i in num[4+num[1]+num[3+num[1]]:]:
                s.add(i)
            for i in num[2:2+num[1]]:
                addDependencies(i, s)
    
def readNames(line):
    line[0] = int(line[0])
    
    if not line[1].startswith("f_"):
        id2name[line[0]] = line[1]
        name2id[line[1]] = line[0]
        return
    line[1] = line[1][2:]
    line[1] = line[1][:-1]
    line[1] = line[1].split("(",1)
    (typ, args) = (line[1][0], line[1][1].split(',', 2))
    if typ == "set":
        assert len(args) == 3
        if args[0] not in aggregateSets: aggregateSets[args[0]] = ([],[])
        aggregateSets[args[0]][0].append(args[2])
        aggregateSets[args[0]][1].append(int(args[1]))
    elif typ == "count":
        assert len(args) == 3
        sums[line[0]] = (args[0], args[1], int(args[2]))
    elif typ == "sum":
        assert len(args) == 3
        sums[line[0]] = (args[0], args[1], int(args[2]))
    elif typ == "avg":
        assert len(args) == 3
        avgs[line[0]] = (args[0], args[1], int(args[2]))
    elif typ == "min":
        assert len(args) == 3
        mins[line[0]] = (args[0], args[1], int(args[2]))
    elif typ == "max":
        assert len(args) == 3
        maxs[line[0]] = (args[0], args[1], int(args[2]))
    elif typ == "odd":
        assert len(args) == 1
        odds[line[0]] = (args[0],)
    elif typ == "even":
        assert len(args) == 1
        evens[line[0]] = (args[0],)

def rewriteSums():
    def ge(id, aggregate, bound, id_aux):
        global maxId
        lit = []
        w = []
        nlit = []
        nw = []
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] >= 0:
                lit.append(name2id[aggregate[0][i]])
                w.append(aggregate[1][i])
            elif not areRecursive(id, name2id[aggregate[0][i]]):
                nlit.append(name2id[aggregate[0][i]])
                nw.append(-aggregate[1][i])
                bound = bound -aggregate[1][i]
            else:
                auxId = getAuxOf(name2id[aggregate[0][i]])
                aux.append((auxId, name2id[aggregate[0][i]], id_aux))
                lit.append(auxId)
                w.append(-aggregate[1][i])
                bound = bound -aggregate[1][i]
                
        print(5, id, bound, len(aggregate[0]), len(nlit), " ".join([str(l) for l in nlit]), " ".join([str(l) for l in lit]), " ".join([str(c) for c in nw]), " ".join([str(c) for c in w]))
    
    def gt(id, aggregate, bound, id_aux):
        ge(id, aggregate, bound + 1, id_aux)
        
    def le(id, aggregate, bound, id_aux):
        ge(id, (aggregate[0], [-w for w in aggregate[1]]), -bound, id_aux)
        
    def lt(id, aggregate, bound, id_aux):
        le(id, aggregate, bound-1, id_aux)
        
    def eq(id, aggregate, bound, id_aux):
        global maxId
        aux_ge = maxId + 1
        aux_le = maxId + 2
        maxId = maxId + 2
        print(1, id, 2, 0, aux_ge, aux_le)
        ge(aux_ge, aggregate, bound, id)
        le(aux_le, aggregate, bound, id)
        
    def diff(id, aggregate, bound, id_aux):
        global maxId
        gt(id, aggregate, bound, id_aux)
        lt(id, aggregate, bound, id_aux)
        
    callback = {'>=': ge, '>': gt, '<=': le, '<': lt, '=': eq, '!=': diff}
    for id in sums:
        (name, comp, bound) = sums[id]
        callback[comp[1:-1]](id, aggregateSets[name], bound, id)

def rewriteAvgs():
    def ge(id, aggregate, bound, aux_id, count):
        global maxId
        lit = []
        w = []
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] >= 0:
                lit.append(name2id[aggregate[0][i]])
                w.append(aggregate[1][i])
            else:
                maxId = maxId + 1
                aux.append((maxId, name2id[aggregate[0][i]], aux_id))
                lit.append(maxId)
                w.append(-aggregate[1][i])
                bound = bound -aggregate[1][i]

        lit.append(count)
        tot = sum(w)
        w.append(tot+1)
        print(5, id, bound+tot+1, len(lit), 0, " ".join([str(l) for l in lit]), " ".join([str(c) for c in w]))
    
    def gt(id, aggregate, bound, aux_id, count):
        ge(id, aggregate, bound + 1, aux_id, count)
        
    def le(id, aggregate, bound, aux_id, count):
        ge(id, (aggregate[0], [-w for w in aggregate[1]]), -bound, aux_id, count)
        
    def lt(id, aggregate, bound, aux_id, count):
        le(id, aggregate, bound-1, aux_id, count)
        
    def eq(id, aggregate, bound, aux_id, count):
        global maxId
        aux_ge = maxId + 1
        aux_le = maxId + 2
        maxId = maxId + 2
        print(1, id, 2, 0, aux_ge, aux_le)
        ge(aux_ge, aggregate, bound, id, count)
        le(aux_le, aggregate, bound, id, count)
        
    def diff(id, aggregate, bound, aux_id, count):
        global maxId
        gt(id, aggregate, bound, aux_id, count)
        lt(id, aggregate, bound, aux_id, count)

    global maxId        
    callback = {'>=': ge, '>': gt, '<=': le, '<': lt, '=': eq, '!=': diff}
    for id in avgs:
        (name, comp, bound) = avgs[id]
        maxId = maxId + 1
        print(2, maxId, len(aggregateSets[name][0]), 0, 1, " ".join([str(name2id[a]) for a in aggregateSets[name][0]]))
        for i in range(0, len(aggregateSets[name][1])):
            aggregateSets[name][1][i] = aggregateSets[name][1][i] - bound
        callback[comp[1:-1]](id, aggregateSets[name], 0, id, maxId)


def rewriteMins():
    def le(id, aggregate, bound):
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] <= bound:
                print(1, id, 1, 0, name2id[aggregate[0][i]])
    
    def lt(id, aggregate, bound):
        le(id, aggregate, bound - 1)
        
    def ge(id, aggregate, bound):
        global maxId
        maxId = maxId + 1
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] < bound:
                print(1, maxId, 1, 0, name2id[aggregate[0][i]])
            else:
                print(1, id, 2, 1, maxId, name2id[aggregate[0][i]])
        
    def gt(id, aggregate, bound):
        ge(id, aggregate, bound + 1)
        
    def eq(id, aggregate, bound):
        global maxId
        maxId = maxId + 1
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] < bound:
                print(1, maxId, 1, 0, name2id[aggregate[0][i]])
            elif aggregate[1][i] == bound:
                print(1, id, 2, 1, maxId, name2id[aggregate[0][i]])

    def diff(id, aggregate, bound):
        global maxId
        equal = []
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] < bound:
                print(1, id, 1, 0, name2id[aggregate[0][i]])
            elif aggregate[1][i] == bound:
                print(1, maxId+1, 1, 0, name2id[aggregate[0][i]])
                equal.append(name2id[aggregate[0][i]])
            else:
                print(1, id, 2, 0, maxId+2, name2id[aggregate[0][i]])
        aux.append((maxId+2, maxId+1, id))
        if(len(equal) == 1): print(1, equal[0], 1, 0, maxId+1)
        elif(len(equal) >= 2): print(8, len(equal), " ".join([str(a) for a in equal]), 1, 0, maxId+1)
        maxId = maxId + 2

    callback = {'>=': ge, '>': gt, '<=': le, '<': lt, '=': eq, '!=': diff}
    for id in mins:
        (name, comp, bound) = mins[id]
        callback[comp[1:-1]](id, aggregateSets[name], bound)

def rewriteMaxs():
    def ge(id, aggregate, bound):
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] >= bound:
                print(1, id, 1, 0, name2id[aggregate[0][i]])
    
    def gt(id, aggregate, bound):
        ge(id, aggregate, bound + 1)
        
    def le(id, aggregate, bound):
        global maxId
        maxId = maxId + 1
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] > bound:
                print(1, maxId, 1, 0, name2id[aggregate[0][i]])
            else:
                print(1, id, 2, 1, maxId, name2id[aggregate[0][i]])
        
    def lt(id, aggregate, bound):
        le(id, aggregate, bound-1)
        
    def eq(id, aggregate, bound):
        global maxId
        maxId = maxId + 1
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] > bound:
                print(1, maxId, 1, 0, name2id[aggregate[0][i]])
            elif aggregate[1][i] == bound:
                print(1, id, 2, 1, maxId, name2id[aggregate[0][i]])

    def diff(id, aggregate, bound):
        global maxId
        equal = []
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] > bound:
                print(1, id, 1, 0, name2id[aggregate[0][i]])
            elif aggregate[1][i] == bound:
                print(1, maxId+1, 1, 0, name2id[aggregate[0][i]])
                equal.append(name2id[aggregate[0][i]])
            else:
                print(1, id, 2, 0, maxId+2, name2id[aggregate[0][i]])
        aux.append((maxId+2, maxId+1, id))
        if(len(equal) == 1): print(1, equal[0], 1, 0, maxId+1)
        elif(len(equal) >= 2): print(8, len(equal), " ".join([str(a) for a in equal]), 1, 0, maxId+1)
        maxId = maxId + 2

    callback = {'>=': ge, '>': gt, '<=': le, '<': lt, '=': eq, '!=': diff}
    for id in maxs:
        (name, comp, bound) = maxs[id]
        callback[comp[1:-1]](id, aggregateSets[name], bound)

def rewriteOdds():
    for id in odds:
        global maxId
        (name,) = odds[id]
        aggr = aggregateSets[name][0]
        if len(aggr) == 0: return
        if len(aggr) == 1:
            print(1, id, 1, 0, name2id[aggr[0]])
            return
        print(1, maxId+2, 0, 0)
        maxId = maxId + 2
        for i in range(0, len(aggr)):
            if i == len(aggr) - 1:
                print(1, id, 2, 0, maxId-1, maxId+1)
                print(1, id, 2, 0, name2id[aggr[i]], maxId)
                aux.append((maxId+1, name2id[aggr[i]], id))
                maxId = maxId + 1
            else:
                print(1, maxId+2, 2, 0, maxId-1, maxId+1)
                print(1, maxId+2, 2, 0, name2id[aggr[i]], maxId)
                print(1, maxId+3, 2, 0, maxId, maxId+1)
                print(1, maxId+3, 2, 0, name2id[aggr[i]], maxId-1)
                aux.append((maxId+1, name2id[aggr[i]], id))
                aux.append((maxId+3, maxId+2, id))
                maxId = maxId + 3

def rewriteEvens():     
    for id in evens:
        global maxId
        (name,) = evens[id]
        aggr = aggregateSets[name][0]
        if len(aggr) == 0:
            print(1, id, 1, 0, name2id[aggr[0]])
            return
        if len(aggr) == 1: return
        print(1, maxId+1, 0, 0)
        maxId = maxId + 2
        for i in range(0, len(aggr)):
            if i == len(aggr) - 1:
                print(1, id, 2, 0, maxId-1, maxId+1)
                print(1, id, 2, 0, name2id[aggr[i]], maxId)
                aux.append((maxId+1, name2id[aggr[i]], id))
                maxId = maxId + 1
            else:
                print(1, maxId+2, 2, 0, maxId-1, maxId+1)
                print(1, maxId+2, 2, 0, name2id[aggr[i]], maxId)
                print(1, maxId+3, 2, 0, maxId, maxId+1)
                print(1, maxId+3, 2, 0, name2id[aggr[i]], maxId-1)
                aux.append((maxId+1, name2id[aggr[i]], id))
                aux.append((maxId+3, maxId+2, id))
                maxId = maxId + 3
                        
def addAuxRules():
    global maxId
    comp = {}
    for a in aux:
        if a[2] not in comp:
            maxId = maxId + 1
            print("1 %d 1 1 %d" % (maxId, a[2]))
            comp[a[2]] = maxId
        print("1 %d 1 1 %d" % (a[0], a[1]))
        print("1 %d 1 0 %d" % (a[0], a[2]))
        print("8 2 %d %d 1 1 %d" % (a[1], a[0], comp[a[2]]))

def computeComponents():
    global component
    
    dependencies[-1] = set()
    for i in range(1,maxId): addDependency(i, -1)

    for id in sums:
        (name, comp, bound) = sums[id]
        lits, coeffs = aggregateSets[name]
        for i in range(0,len(lits)):
            if comp in ['">="','">"']:
                if coeffs[i] > 0: addDependency(id, name2id[lits[i]])
            if comp in ['"<="','"<"']:
                if coeffs[i] < 0: addDependency(id, name2id[lits[i]])
            elif comp in ['"!="','"="']:
                if coeffs[i] != 0: addDependency(id, name2id[lits[i]])
    
    sccs = scc.strongly_connected_components_iterative(list(dependencies.keys()), dependencies)
    component = {}
    idx = 0
    for c in sccs:
        if -1 in c:
            assert len(c) == 1
            continue
        idx = idx + 1
        for i in c: component[i] = idx

def normalize():
    for rule in program:
        print(" ".join([str(a) for a in rule]))
    
    if dependencies is not None: computeComponents()
    
    rewriteSums()
    rewriteAvgs()
    rewriteMins()
    rewriteMaxs()
    rewriteOdds()
    rewriteEvens()
    addAuxRules()
    
    print(0)
    for n in name2id:
        print(name2id[n], n)
    print("0\nB+\n0\nB-\n1\n0\n1")


if __name__ == "__main__":
    args = parseArguments()

    tmpFile = tempfile.NamedTemporaryFile()
    tmpFile.write("""
        % second argument is optional, with default value 1
        f_set(ID,1,ATOM) :- f_set(ID,ATOM).
        
        #hide f_set/2.
        
        #external f_count/3.
        #external f_sum/3.
        #external f_avg/3.
        #external f_min/3.
        #external f_max/3.
        #external f_odd/1.
        #external f_even/1.
    """.encode())
    tmpFile.flush()

    cmd = [args.grounder]
    cmd.extend(args.args)
    cmd.append(tmpFile.name)
    gringo = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    [stdout, stderr] = gringo.communicate()
    tmpFile.close()
    #print(stdout.decode())
    stdout = stdout.decode().split("\n")
    
    callback = [readProgram, readNames]
    state = 0
    for line in stdout:
        line = line.strip()
        if line == '0':
            state = state + 1
            if state >= 2:
                break
        else:
            callback[state](line.split())

    normalize()
