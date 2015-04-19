#!/usr/bin/env python3

GPL = """
Instantiate ASP programs in order to compute G-stable models by means of ordinary ASP solvers.
Copyright (C) 2015  XXX YYY (EMAIL)

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
import subprocess
import sys
import tempfile

def parseArguments():
    global VERSION
    global GPL
    parser = argparse.ArgumentParser(description=GPL.split("\n")[1], epilog="Copyright (C) 2015  XXX YYY (EMAIL)")
    parser.add_argument('--help-syntax', action='store_true', help='print syntax description and exit') 
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + VERSION, help='print version number')
    parser.add_argument('-g', '--grounder', metavar='<grounder>', type=str, help='path to the gringo 3 (default \'gringo\')')
    parser.add_argument('args', metavar="...", nargs=argparse.REMAINDER, help="arguments for <grounder>")
    args = parser.parse_args()
    if args.help_syntax: helpSyntax()
    if not args.grounder: args.grounder = 'gringo'
    return args

def helpSyntax():
    print("""
The syntax is almost conformant to ASP Core 2.0, with the exception of aggregates.
Moreover, predicates starting with the prefix 'gz_' are reserved for internal use
and must not be used by the user. Remember also to not hide them!


Supported aggregates are COUNT, SUM, MIN, MAX, EVEN, and ODD. Aggregate sets are
declared by means of predicate gz_set/3, where:

- the first argument is the ID of an aggregate;

- the second argument is an integer;

- the third argument is an atom.

The second argument is optional, with default value 1.


A COUNT aggregate can be added in a rule body by using predicate gz_count/3, where:

- the first argument is the ID of an aggregate;

- the second argument is a comparator among ">=", ">", "<=", "<", "=", "!=";

- the third argument is an integer.


Aggregates SUM, MIN, and MAX are similar, and use predicates gz_sum/3, gz_min/3,
and gz_max/3.


An EVEN aggregate can be added in a rule body by using predicate gz_even/1, where
the argument is the ID of an aggregate. Aggregate ODD is similar, and uses
predicate gz_odd/1.


Remember that COUNT, EVEN, and ODD are applied on true atoms in the aggregate set,
while SUM, MIN, and MAX are applied on the multiset of integers associated with
true atoms in the aggregate set.


Variables can be used taking into account the previous description.
    """)
    sys.exit()

id2name = {}
name2id = {}

program = []
aggregateSets = {}
sums = {}
mins = {}
maxs = {}
odds = {}
evens = {}

aux = {}
maxId = 0

def readProgram(line):
    global maxId
    num = [int(a) for a in line]
    maxId = max(maxId, max(num))
    program.append(num)
    
def readNames(line):
    line[0] = int(line[0])
    
    if not line[1].startswith("gz_"):
        id2name[line[0]] = line[1]
        name2id[line[1]] = line[0]
        return
    line[1] = line[1][3:]
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
    def ge(id, aggregate, bound):
        neg = []
        pos = []
        wpos = []
        wneg = []
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] >= 0:
                pos.append(aggregate[0][i])
                wpos.append(aggregate[1][i])
            else:
                neg.append(aggregate[0][i])
                wneg.append(-aggregate[1][i])
                bound = bound -aggregate[1][i]
                
        rule = [5, id, bound, len(aggregate[0]), len(neg)]
        rule.extend(neg)
        rule.extend(pos)
        rule.extend(wneg)
        rule.extend(wpos)
        print(" ".join([str(a) for a in rule]))
    
    def gt(id, aggregate, bound):
        ge(id, aggregate, bound + 1)
        
    def le(id, aggregate, bound):
        ge(id, (aggregate[0], [-w for w in aggregate[1]]), -bound)
        
    def lt(id, aggregate, bound):
        le(id, aggregate, bound-1)
        
    def eq(id, aggregate, bound):
        global maxId
        ge(maxId + 1, aggregate, bound)
        le(maxId + 2, aggregate, bound)
        print(1, id, 2, 0, maxId+1, maxId+2)
        maxId = maxId + 2
        
    def diff(id, aggregate, bound):
        global maxId
        gt(maxId + 1, aggregate, bound)
        lt(maxId + 2, aggregate, bound)
        print(1, id, 1, 0, maxId+1)
        print(1, id, 1, 0, maxId+2)
        maxId = maxId + 2        
        
    callback = {'>=': ge, '>': gt, '<=': le, '<': lt, '=': eq, '!=': diff}
    for id in sums:
        (name, comp, bound) = sums[id]
        callback[comp[1:-1]](id, aggregateSets[name], bound)

def rewriteMins():
    def le(id, aggregate, bound):
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] <= bound:
                print(1, id, 1, 0, aggregate[0][i])
    
    def lt(id, aggregate, bound):
        le(id, aggregate, bound - 1)
        
    def ge(id, aggregate, bound):
        global maxId
        maxId = maxId + 1
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] < bound:
                print(1, maxId, 1, 0, aggregate[0][i])
            else:
                print(1, id, 2, 1, maxId, aggregate[0][i])
        
    def gt(id, aggregate, bound):
        ge(id, aggregate, bound + 1)
        
    def eq(id, aggregate, bound):
        global maxId
        maxId = maxId + 1
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] < bound:
                print(1, maxId, 1, 0, aggregate[0][i])
            elif aggregate[1][i] == bound:
                print(1, id, 2, 1, maxId, aggregate[0][i])

    def diff(id, aggregate, bound):
        global maxId
        maxId = maxId + 1
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] < bound:
                print(1, id, 1, 0, aggregate[0][i])
            elif aggregate[1][i] == bound:
                print(1, maxId, 1, 0, aggregate[0][i])
            else:
                print(1, id, 2, 1, maxId, aggregate[0][i])

    callback = {'>=': ge, '>': gt, '<=': le, '<': lt, '=': eq, '!=': diff}
    for id in mins:
        (name, comp, bound) = mins[id]
        callback[comp[1:-1]](id, aggregateSets[name], bound)

def rewriteMaxs():
    def ge(id, aggregate, bound):
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] >= bound:
                print(1, id, 1, 0, aggregate[0][i])
    
    def gt(id, aggregate, bound):
        ge(id, aggregate, bound + 1)
        
    def le(id, aggregate, bound):
        global maxId
        maxId = maxId + 1
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] > bound:
                print(1, maxId, 1, 0, aggregate[0][i])
            else:
                print(1, id, 2, 1, maxId, aggregate[0][i])
        
    def lt(id, aggregate, bound):
        le(id, aggregate, bound-1)
        
    def eq(id, aggregate, bound):
        global maxId
        maxId = maxId + 1
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] > bound:
                print(1, maxId, 1, 0, aggregate[0][i])
            elif aggregate[1][i] == bound:
                print(1, id, 2, 1, maxId, aggregate[0][i])

    def diff(id, aggregate, bound):
        global maxId
        maxId = maxId + 1
        for i in range(0, len(aggregate[0])):
            if aggregate[1][i] > bound:
                print(1, id, 1, 0, aggregate[0][i])
            elif aggregate[1][i] == bound:
                print(1, maxId, 1, 0, aggregate[0][i])
            else:
                print(1, id, 2, 1, maxId, aggregate[0][i])

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
            print(1, id, 1, 0, aggr[0])
            return
        for i in range(0, len(aggr)-1):
            if i == 0:
                print(1, maxId+1, 1, 0, aggr[i])
            else:
                print(1, maxId+1, 2, 1, maxId, aggr[i])
                print(1, maxId+1, 2, 1, aggr[i], maxId)
            maxId = maxId + 1
        print(1, id, 2, 1, maxId, aggr[-1])
        print(1, id, 2, 1, aggr[-1], maxId)

def rewriteEvens():                        
    for id in evens:
        global maxId
        (name,) = evens[id]
        aggr = aggregateSets[name][0]
        if len(aggr) == 0:
            print(1, id, 0, 0)
            return
        if len(aggr) == 1:
            print(1, id, 1, 1, aggr[0])
            return
        for i in range(0, len(aggr)-1):
            if i == 0:
                print(1, maxId+1, 1, 1, aggr[i])
            else:
                print(1, maxId+1, 2, 1, maxId, aggr[i])
                print(1, maxId+1, 2, 1, aggr[i], maxId)
            maxId = maxId + 1
        print(1, id, 2, 1, maxId, aggr[-1])
        print(1, id, 2, 1, aggr[-1], maxId)
                        
def addAuxRules():
    for a in aux:
        print("1 %d 1 1 %d" % (aux[a][0], name2id[a]))
        print("1 %d 1 0 %d" % (aux[a][0], name2id[a]))
        print("3 1 %d 0 0" % (aux[a][1],))
        print("1 1 2 1 %d %d" % (aux[a][1], name2id[a]))
        print("1 1 2 1 %d %d" % (name2id[a], aux[a][1]))

def gelfondize():
    def rewrite(rule, neg, pos):
        def addDomain(aggr, newpos):
            global maxId
            (atoms, weights) = aggregateSets[aggr[0]]
            for idx in range(0,len(atoms)):
                if atoms[idx] not in aux:
                    aux[atoms[idx]] = (maxId + 1, maxId + 2)
                    maxId = maxId + 2
                newpos.append(aux[atoms[idx]][0])
                atoms[idx] = aux[atoms[idx]][1]

        newpos = []
        for a in pos:
            newpos.append(a)
            if a in sums: addDomain(sums[a], newpos)
            elif a in mins: addDomain(mins[a], newpos)
            elif a in maxs: addDomain(maxs[a], newpos)
            elif a in odds: addDomain(odds[a], newpos)
            elif a in evens: addDomain(evens[a], newpos)
        rule.append(len(neg) + len(newpos))
        rule.append(len(neg))
        rule.extend(neg)
        rule.extend(newpos)
        print(" ".join([str(a) for a in rule]))

    def normal(args):
        rule = [1, args[0]]
        nsize = args[2]
        neg = args[3:3+nsize]
        pos = args[3+nsize:]
        rewrite(rule, neg, pos)
    
    def choice(args):
        hsize = args[0]
        rule = [3, hsize]
        rule.extend(args[1:1+hsize])
        nsize = args[2+hsize]
        neg = args[3+hsize:3+hsize+nsize]
        pos = args[3+hsize+nsize:]
        rewrite(rule, neg, pos)
    
    def disjunctive(args):
        hsize = args[0]
        rule = [8, hsize]
        rule.extend(args[1:1+hsize])
        nsize = args[2+hsize]
        neg = args[3+hsize:3+hsize+nsize]
        pos = args[3+hsize+nsize:]
        rewrite(rule, neg, pos)
        
        
    callback = {1: normal, 3: choice, 8: disjunctive}
    for rule in program:
        callback[rule[0]](rule[1:])
    
    rewriteSums()
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
        gz_set(ID,1,ATOM) :- gz_set(ID,ATOM).
        
        #hide gz_set/2.
        
        #external gz_count/3.
        #external gz_sum/3.
        #external gz_min/3.
        #external gz_max/3.
        #external gz_odd/1.
        #external gz_even/1.
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

    gelfondize()
