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

VERSION = "0.1"

import argparse
import re
import scc
import subprocess
import sys
import tempfile

def parseArguments():
    global VERSION
    global GPL
    parser = argparse.ArgumentParser(description=GPL.split("\n")[1], epilog="Copyright (C) 2015  Mario Alviano (mario@alviano.net)")
    parser.add_argument('--help-syntax', action='store_true', help='print syntax description and exit') 
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + VERSION, help='print version number')
    parser.add_argument('-g', '--grounder', metavar='<grounder>', type=str, help='path to the gringo 3 (default \'gringo\')', default='gringo')
    parser.add_argument('-s', '--solver', metavar='<solver>', type=str, help='path to the SMT solver (default \'z3\')', default='z3')
    parser.add_argument('--print-grounder-input', action='store_true', help='print the input of the grounder')
    parser.add_argument('--print-grounder-output', action='store_true', help='print the output of the grounder')
    parser.add_argument('--print-smt-input', action='store_true', help='print the input of the SMT solver')
    parser.add_argument('--print-smt-output', action='store_true', help='print the output of the SMT solver')
    parser.add_argument('args', metavar="...", nargs=argparse.REMAINDER, help="arguments for <grounder>")
    args = parser.parse_args()
    if args.help_syntax: helpSyntax()
    return args

def helpSyntax():
    print("""
TODO: explain how to encode FASP programs.
    """)
    sys.exit()

deps = {-1 : set()}
theory = []

def getPredicate(string):
    return string[:-1].split("(", 1)[0]

def getArgs(string):
    return split(string[:-1].split("(", 1)[1])
    
def split(args):
    res = [""]
    count = 0
    for i in range(0, len(args)):
        if args[i] == ',' and count == 0: 
            res.append("")
            continue
        if args[i] == '(': count = count + 1
        elif args[i] == ')': count = count - 1
        res[-1] = res[-1] + args[i]
    return res

def build(formula):
    if formula in ["0", "1"]: return Rational(int(formula), 1)
    predicate = getPredicate(formula)
    args = getArgs(formula)
    if predicate == "atom": return Atom(args[0])
    if predicate == "decimal": return Rational(args[0])
    if predicate == "fraction": return Rational(args[0], args[1])
    if predicate == "or": return Or(args)
    if predicate == "and": return And(args)
    if predicate == "min": return Min(args)
    if predicate == "max": return Max(args)
    if predicate == "neg": return Not(args[0])
    assert False


class Atom:
    _instances = []
    _name2atom = {}
    
    def getInstances():
        return [Atom(Atom._instances[i].name) for i in range(0, len(Atom._instances))]
    
    class AtomData:
        def __init__(self, id, name):
            self.id = id
            self.name = name
            self.integer = False
            self.heads = []
            self.component = None
            assert self.id not in deps
            deps[self.id] = set()
            deps[self.id].add(-1)
            
    def __init__(self, name):
        if name not in Atom._name2atom:
            Atom._name2atom[name] = self.AtomData(len(Atom._instances), name)
            Atom._instances.append(Atom._name2atom[name])
        self._data = Atom._name2atom[name]

    def getId(self):
        return self._data.id
    
    def getName(self):
        return self._data.name

    def isInteger(self):
        return self._data.integer

    def setInteger(self):
        self._data.integer = True

    def getHeads(self):
        return self._data.heads
        
    def addDep(self, atom):
        assert self.getId() in deps
        assert atom.getId() in deps
        deps[self.getId()].add(atom.getId())
    
    def setComponent(self, idx):
        self._data.component = idx
    
    def getComponent(self):
        return self._data.component

    def notifyHeadAtoms(self, rule):
        self._data.heads.append(rule)
        rule.body.addDepTo(self)
        
    def addDepTo(self, atom):
        atom.addDep(self)

    def hasRecursiveOr(self, compIdx):
        return False
        
    def hasRecursiveAtom(self, compIdx):
        return self.getComponent() == compIdx

    def recursiveAtoms(self, compIdx):
        return [self] if self.getComponent() == compIdx else []

    def completion(self, headAtom=None, rule=None):
        if headAtom is not None:
            assert self.getId() == headAtom.getId()
            assert self.getId() == rule.head.getId()
            return rule.body.outer()
        
        heads = self.getHeads()
        if len(heads) == 0:
            theory.append("(assert (= %s 0))" % (self.outer(),))
        elif len(heads) == 1:
            theory.append("(assert (= %s %s))" % (self.outer(), heads[0].completion(self)))
        else:
            support = "(max2 %s %s)" % (heads[0].completion(self), heads[1].completion(self))
            for h in heads[2:]:
                support = "(max2 %s %s)" % (support, h.completion(self))
            theory.append("(assert (= %s %s))" % (self.outer(), support))

    def orderedCompletion(self):
        definitions = []
        for rule in self.getHeads():
            recAtoms = rule.body.recursiveAtoms(self.getComponent())
            if len(recAtoms) == 0: definitions.append(rule.completion(self))
            elif len(recAtoms) == 1:
                definitions.append("(ite (= %s (+ %s 1)) %s 0)" % (self.sp(), recAtoms[0].sp(), rule.completion(self)))
            else:
                source = "(max2 %s %s)" % (recAtoms[0].sp(), recAtoms[1].sp())
                for a in recAtoms[2:]:
                    source = "(max2 %s %s)" % (source, recAtoms[0].sp())
                definitions.append("(ite (= %s (+ %s 1)) %s 0)" % (source, recAtoms[0].sp(), rule.completion(self)))
                #definitions.append("(ite (and %s) %s 0)" % (" ".join(["(< %s %s)" % (s.sp(), self.sp()) for s in recAtoms]), rule.completion(self)))
            
        if len(definitions) == 0:
            theory.append("(assert (= %s 0))" % (self.outer(),))
        elif len(definitions) == 1:
            theory.append("(assert (= %s %s))" % (self.outer(), definitions[0]))
        else:
            support = "(max2 %s %s)" % (definitions[0], definitions[1])
            for d in definitions[2:]:
                support = "(max2 %s %s)" % (support, d)
            theory.append("(assert (= %s %s))" % (self.outer(), support))

    def outer(self):
        return "x%d" % (self.getId(),)

    def inner(self, compIdx):
        return "y%d" % (self.getId(),) if compIdx == self.getComponent() else self.outer()

    def sp(self):
        return "s%d" % (self.getId(),)

class Rational:
    heads = []
    _headIds = set()

    def __init__(self, num, den=None):
        num = int(num)
        self.num = num
        if den is None:
            self.den = 1
            while num > 0:
                num = int(num / 10)
                self.den = self.den * 10
        else:
            self.den = int(den)

    def notifyHeadAtoms(self, rule):
        if rule.id in Rational._headIds: return
        Rational._headIds.add(rule.id)
        Rational.heads.append(rule)

    def addDepTo(self, atom):
        pass

    def hasRecursiveOr(self, compIdx):
        return False

    def hasRecursiveAtom(self, compIdx):
        return False

    def recursiveAtoms(self, compIdx):
        return []

    def outer(self):
        return "(/ %d %d)" % (self.num, self.den)

    def inner(self, compIdx):
        return "(/ %d %d)" % (self.num, self.den)

class Or:
    def __init__(self, elements):
        self.elements = [build(e) for e in elements]
        
    def notifyHeadAtoms(self, rule):
        for e in self.elements:
            e.notifyHeadAtoms(rule)

    def addDepTo(self, atom):
        for e in self.elements:
            e.addDepTo(atom)

    def hasRecursiveOr(self, compIdx):
        for e in self.elements:
            if e.hasRecursiveAtom(compIdx): return True
        return False

    def hasRecursiveAtom(self, compIdx):
        for e in self.elements:
            if e.hasRecursiveAtom(compIdx): return True
        return False

    def recursiveAtoms(self, compIdx):
        ret = []
        for e in self.elements: ret.extend(e.recursiveAtoms(compIdx))
        return ret

    def outer(self):
        return "(min2 (+ %s) 1)" % (" ".join([e.outer() for e in self.elements]),)
        
    def inner(self, compIdx):
        return "(min2 (+ %s) 1)" % (" ".join([e.inner(compIdx) for e in self.elements]),)
        
    def completion(self, headAtom, rule):
        return "(max2 (- %s %s) 0)" % (rule.body.outer(), " ".join([e.outer() for e in self.elements if e.getId() != headAtom.getId()]))

class And:
    def __init__(self, elements):
        self.elements = [build(e) for e in elements]

    def notifyHeadAtoms(self, rule):
        for e in self.elements:
            e.notifyHeadAtoms(rule)

    def addDepTo(self, atom):
        for e in self.elements:
            e.addDepTo(atom)

    def hasRecursiveOr(self, compIdx):
        for e in self.elements:
            if e.hasRecursiveOr(compIdx): return True
        return False

    def hasRecursiveAtom(self, compIdx):
        for e in self.elements:
            if e.hasRecursiveAtom(compIdx): return True
        return False

    def recursiveAtoms(self, compIdx):
        ret = []
        for e in self.elements: ret.extend(e.recursiveAtoms(compIdx))
        return ret

    def outer(self):
        return "(max2 (+ %s -%d) 0)" % (" ".join([e.outer() for e in self.elements]), len(self.elements)-1)
        
    def inner(self, compIdx):
        return "(max2 (+ %s -%d) 0)" % (" ".join([e.inner(compIdx) for e in self.elements]), len(self.elements)-1)

    def completion(self, headAtom, rule):
        skip = None
        for i in range(len(self.elements)):
            if self.elements[i].getId() == headAtom.getId():
                skip = i
                break
        return "(ite (> %s 0) (max2 (- %s %s -%d) 0) 0)" % (rule.body.outer(), rule.body.outer(), " ".join([self.elements[i].outer() for i in range(len(self.elements)) if i != skip]), len(self.elements)-1)

class Min:
    def __init__(self, elements):
        self.elements = [build(e) for e in elements]

    def notifyHeadAtoms(self, rule):
        for e in self.elements:
            e.notifyHeadAtoms(rule)

    def addDepTo(self, atom):
        for e in self.elements:
            e.addDepTo(atom)

    def hasRecursiveOr(self, compIdx):
        for e in self.elements:
            if e.hasRecursiveOr(compIdx): return True
        return False

    def hasRecursiveAtom(self, compIdx):
        for e in self.elements:
            if e.hasRecursiveAtom(compIdx): return True
        return False

    def recursiveAtoms(self, compIdx):
        ret = []
        for e in self.elements: ret.extend(e.recursiveAtoms(compIdx))
        return ret

    def outer(self):
        res = "(min2 %s %s)" % (self.elements[0].outer(), self.elements[1].outer())
        for e in self.elements[2:]:
            res = "(min2 %s %s)" % (res, e.outer())
        return res
        
    def inner(self, compIdx):
        res = "(min2 %s %s)" % (self.elements[0].inner(compIdx), self.elements[1].inner(compIdx))
        for e in self.elements[2:]:
            res = "(min2 %s %s)" % (res, e.inner(compIdx))
        return res

    def completion(self, headAtom, rule):
        return rule.body.outer()

class Max:
    def __init__(self, elements):
        self.elements = [build(e) for e in elements]

    def notifyHeadAtoms(self, rule):
        for e in self.elements:
            e.notifyHeadAtoms(rule)

    def addDepTo(self, atom):
        for e in self.elements:
            e.addDepTo(atom)

    def hasRecursiveOr(self, compIdx):
        for e in self.elements:
            if e.hasRecursiveOr(compIdx): return True
        return False

    def hasRecursiveAtom(self, compIdx):
        for e in self.elements:
            if e.hasRecursiveAtom(compIdx): return True
        return False

    def recursiveAtoms(self, compIdx):
        ret = []
        for e in self.elements: ret.extend(e.recursiveAtoms(compIdx))
        return ret

    def outer(self):
        res = "(max2 %s %s)" % (self.elements[0].outer(), self.elements[1].outer())
        for e in self.elements[2:]:
            res = "(max2 %s %s)" % (res, e.outer())
        return res
        
    def inner(self, compIdx):
        res = "(max2 %s %s)" % (self.elements[0].inner(compIdx), self.elements[1].inner(compIdx))
        for e in self.elements[2:]:
            res = "(max2 %s %s)" % (res, e.inner(compIdx))
        return res

    def completion(self, headAtom, rule):
        body = rule.body.outer()
        return "(ite (or %s) 0 %s)" % (" ".join(["(>= %s %s)" % (e.outer(), body) for e in self.elements if e.getId() != headAtom.getId()]), body)

class Not:
    def __init__(self, element):
        self.element = build(element)

    def notifyHeadAtoms(self, rule):
        assert False
        #self.elements.notifyHeadAtoms(rule)

    def addDepTo(self, atom):
        pass
        
    def hasRecursiveOr(self, compIdx):
        return False

    def hasRecursiveAtom(self, compIdx):
        return False

    def recursiveAtoms(self, compIdx):
        return []

    def outer(self):
        return "(- 1 %s)" % (self.element.outer(),)

    def inner(self, compIdx):
        return "(- 1 %s)" % (self.element.outer(),)
        
class Rule:
    instances = []

    def __init__(self, head, body):
        self.id = len(Rule.instances)
        self.head = build(head)
        self.body = build(body)
        Rule.instances.append(self)

    def notifyHeadAtoms(self):
        self.head.notifyHeadAtoms(self)

    def outer(self):
        theory.append("(assert (>= %s %s))" % (self.head.outer(), self.body.outer()))
        
    def inner(self, compIdx):
        return "(>= %s %s)" % (self.head.inner(compIdx), self.body.inner(compIdx))
        
    def completion(self, headAtom):
        return self.head.completion(headAtom, self)
    
def readNames(line):
    line[0] = int(line[0])
    line[1] = line[1][:-1].split("(", 1)
    (typ, args) = (line[1][0], line[1][1])
    args = split(args)
    if typ == "rule":
        assert len(args) == 2
        Rule(args[0], args[1])
    elif typ == "integer":
        assert len(args) == 1
        atom = build(args[0])
        atom.setInteger()
    else:
        assert False

def computeComponents():
    sccs = scc.strongly_connected_components_iterative(list(deps.keys()), deps)
    atoms = Atom.getInstances()
    
    res = []
    for c in sccs:
        if -1 in c:
            assert len(c) == 1
            continue
        res.append(([atoms[i] for i in c], set()))
        for atom in res[-1][0]:
            atom.setComponent(len(res)-1)
            for rule in atom.getHeads(): res[-1][1].add(rule)
    return res

def encodeReduct(compIdx, atoms, rules):
    vars = " ".join(["(%s %s)" % (atom.inner(compIdx), "Int" if atom.isInteger() else "Real") for atom in atoms])
    zero = " ".join(["(>= %s 0)" % (atom.inner(compIdx),) for atom in atoms])
    subset = " ".join(["(<= %s %s)" % (atom.inner(compIdx),atom.outer()) for atom in atoms])
    eq = " ".join(["(= %s %s)" % (atom.inner(compIdx),atom.outer()) for atom in atoms])
    reduct = " ".join(["%s" % (rule.inner(compIdx),) for rule in rules])
    theory.append("(assert (forall (%s) (=> (and %s %s %s) (and %s))))" % (vars, zero, subset, reduct, eq))

def processComponent(compIdx, atoms, rules):
    if len(atoms) == 1 and atoms[0].getId() not in deps[atoms[0].getId()]:
        atoms[0].completion()
        return
        
    for rule in rules:
        if rule.body.hasRecursiveOr(compIdx):
            for atom in atoms: atom.completion()
            encodeReduct(compIdx, atoms, rules)
            return
    
    for atom in atoms: theory.append("(declare-const %s Int) (assert (>= %s 0)) (assert (<= %s %d))" % (atom.sp(), atom.sp(), atom.sp(), len(atoms)))
    for atom in atoms: atom.orderedCompletion()

def normalize():
    theory.append("(define-fun min2 ((x1 Real) (x2 Real)) Real (ite (<= x1 x2) x1 x2))")
    theory.append("(define-fun max2 ((x1 Real) (x2 Real)) Real (ite (>= x1 x2) x1 x2))")

    for atom in Atom.getInstances():
        id = atom.getId()
        if atom.isInteger():
            theory.append("(declare-const x%d Int) (assert (or (= x%d 0) (= x%d 1)))" % (id,id,id))
        else:
            theory.append("(declare-const x%d Real) (assert (>= x%d 0)) (assert (<= x%d 1))" % (id,id,id))
        #print(id, atom.getName(), file=sys.stderr)

    for rule in Rule.instances:
        rule.notifyHeadAtoms()
        
    for rule in Rational.heads:
        rule.outer()
    
    components = computeComponents()
    for i in range(0, len(components)):
        processComponent(i, components[i][0], components[i][1])

    theory.append("(check-sat-using (then qe smt))")
    theory.append("(get-model)")
    
if __name__ == "__main__":
    args = parseArguments()

    rules = []
    rules.append("expression(X) :- rule(X,Y).")
    rules.append("expression(Y) :- rule(X,Y).")
    rules.append("atom(X) :- expression(atom(X)).")
    
    rules.append("expression(X) :- expression(neg(X)).")
    for i in range(2,11):
        vars = ",X".join([str(j) for j in range(1,i+1)])
        rules.append("integer(atom(X)) :- rule(atom(X), or(%s))." % (",".join(["atom(X)" for j in range(1,i+1)]),))
        rules.append("delete(atom(X), or(%s)) :- rule(atom(X), or(%s))." % (",".join(["atom(X)" for j in range(1,i+1)]), ",".join(["atom(X)" for j in range(1,i+1)])))
        rules.append("integer(atom(X)) :- rule(and(%s), atom(X))." % (",".join(["atom(X)" for j in range(1,i+1)]),))
        rules.append("delete(and(%s), atom(X)) :- rule(and(%s), atom(X))." % (",".join(["atom(X)" for j in range(1,i+1)]), ",".join(["atom(X)" for j in range(1,i+1)])))
        for conn in ["min", "max", "and", "or"]:
            for j in range(1,i+1):
                rules.append("expression(X%d) :- expression(%s(X%s))." % (j, conn, vars))
    
    rules.append("#hide.")
    rules.append("#show rule(X,Y) : not delete(X,Y).")
    rules.append("#show integer/1.")

    if args.print_grounder_input: 
        print("<grounder-input>")
        print("\n".join(rules))
        print("</grounder-input>")
    tmpFile = tempfile.NamedTemporaryFile()
    tmpFile.write("\n".join(rules).encode())
    tmpFile.flush()

    cmd = [args.grounder]
    cmd.extend(args.args)
    cmd.append(tmpFile.name)
    gringo = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    [stdout, stderr] = gringo.communicate()
    tmpFile.close()
    if args.print_grounder_output:
        print("<grounder-output>")
        print(stdout.decode(), end="")
        print("</grounder-output>")
        print("<grounder-error>")
        print(stderr.decode(), end="")
        print("</grounder-error>")
    stdout = stdout.decode().split("\n")
    
    state = 0
    for line in stdout:
        line = line.strip()
        if line == '0':
            state = state + 1
            if state >= 2:
                break
        elif state == 1:
            readNames(line.split())

    normalize()
    
    if args.print_smt_input:
        print("<smt-input>")
        print("\n".join(theory))
        print("</smt-input>")
    tmpFile = tempfile.NamedTemporaryFile()
    tmpFile.write("\n".join(theory).encode())
    tmpFile.flush()

    solver = subprocess.Popen([args.solver, tmpFile.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    [stdout, stderr] = solver.communicate()
    tmpFile.close()
    if args.print_smt_output:
        print("<smt-input>")
        print(stdout.decode(), end="")
        print("</smt-output>")
        print("<smt-error>")
        print(stderr.decode(), end="")
        print("</smt-error>")
    stdout = stdout.decode().split("\n")
    
    assert len(stdout) > 0
    if stdout[0] == "unsat":
        print("INCOHERENT")
    elif stdout[0] == "unknown":
        print("UNKNOWN")
    else:
        assert stdout[0] == "sat"
        assert stdout[1] == "(model "
        atoms = Atom.getInstances()
        regexId = re.compile(".* x(\\d+) .*")
        regexReal = re.compile("\\s*(\\d+(?:\\.\\d+)?)\)\\s*")
        regexFrac = re.compile("\\s*\\(/\\s+(\\d+\\.\\d+)\\s+(\\d+\\.\\d+)\\)\\)\\s*")
        print("Answer 1:")
        for i in range(2, len(stdout), 2):
            match = regexId.match(stdout[i])
            if match:
                matchReal = regexReal.match(stdout[i+1])
                if matchReal:
                    degree = "%s\t\t(%s)" % (matchReal.group(1), matchReal.group(1))
                else:
                    matchFrac = regexFrac.match(stdout[i+1])
                    if matchFrac: degree = "%f\t(%s/%s)" % (float(matchFrac.group(1))/float(matchFrac.group(2)), matchFrac.group(1), matchFrac.group(2))
                    else:
                        print(stdout[i+1])
                        assert False
                
                print("\t%s\t%s" % (atoms[int(match.group(1))].getName(), degree))
                