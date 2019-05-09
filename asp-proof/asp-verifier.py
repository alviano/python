#!/usr/bin/env python3

"""
A script to check proofs for normalized lparse programs.
It must be run as follows:
    $ ./asp-verifier.py program-file proof-file
"""

from collections import OrderedDict
from enum import Enum
import fileinput
import sys

class RuleType(Enum):
    NORMAL_RULE = 1
    CARDINALITY_RULE = 2
    CHOICE_RULE = 3
    WEIGHT_RULE = 5

class TruthValue(Enum):
    TRUE = 1
    FALSE = 2
    UNDEF = 3

definition = OrderedDict()
verbatim = []
next_var = 0

clauses = []
watched = {}

wc = []
in_wc = {}

assigned = {}
assigned_trail = [-1]
next_to_propagate = 0

box_derived = False

def isTrue(lit):
    if lit > 0: return assigned[lit] == TruthValue.TRUE
    return assigned[-lit] == TruthValue.FALSE

def isFalse(lit):
    if lit < 0: return assigned[-lit] == TruthValue.TRUE
    return assigned[lit] == TruthValue.FALSE

def isUndef(lit):
    return assigned[abs(lit)] == TruthValue.UNDEF

def normal_rule(x):
    global next_var
    for id in x[2:]: next_var = max(next_var, int(id)+1)
    return (RuleType.NORMAL_RULE, x)

def cardinality_rule(x):
    global next_var
    for id in x[3:]: next_var = max(next_var, int(id)+1)
    return (RuleType.CARDINALITY_RULE, x)

def choice_rule(x):
    global next_var
    for id in x[2:]: next_var = max(next_var, int(id)+1)
    return (RuleType.CHOICE_RULE, x)

def weight_rule(x):
    global next_var
    for id in x[3:3+int(x[1])]: next_var = max(next_var, int(id)+1)
    return (RuleType.WEIGHT_RULE, x)

def isUnit(x):
    return x[1][0] == '1'

def bodyToLits(x):
    lits = []
    for id in x[2:2+int(x[1])]: lits.append(-id)
    for id in x[2+int(x[1]):]: lits.append(id)
    return lits

def readProgram(line):
    if line[0] == '1':
        head = line[1]
        body = line[2:]
        if head not in definition: definition[head] = []
        definition[head].append(normal_rule(body))
    elif line[0] == '2':
        head = line[1]
        body = line[2:]
        if head not in definition: definition[head] = []
        definition[head].append(cardinality_rule(body))
    elif line[0] == '3':
        hsize = int(line[1])
        head = line[2 : 2 + hsize]
        body = line[2 + hsize :]
        for x in head:
            if x not in definition: definition[x] = []
            definition[x].append(choice_rule(body))
    elif line[0] == '5':
        head = line[1]
        body = line[2:]
        if head not in definition: definition[head] = []
        definition[head].append(weight_rule(body))
    elif line[0] == '6':
        exit("Minimize rules are not currently supported.")
    else:
        exit("Cannot handle rule {}".format(' '.join(line)))

def readVerbatim(line):
    verbatim.append(line)

def checkProgram():
    lastPart = 0
    for i in range(1, len(verbatim)):
        if verbatim[i] == ['0']:
            lastPart = i
            break
    if verbatim[lastPart:] != [['0'], ['B+'], ['0'], ['B-'], ['1'], ['0'], ['1']]:
        exit("Cannot process this program because I cannot understand the last part of the lparse program (this is a prototype tool and supports just a fragment of lparse format).")

    global next_var
    next_var = max(next_var, max([int(x) for x in definition]) + 1)

    for x in definition:
        if len(definition[x]) != 1:
            for d in definition[x]:
                if not isUnit(d):
                    exit("The program is not normalized!")

def propagate(assumptions=[]):
    global next_to_propagate
    global assigned
    global assigned_trail

    assigned_len = len(assigned_trail)
    assigned_trail.extend(assumptions)

    res = True

    while next_to_propagate < len(assigned_trail):
        lit = assigned_trail[next_to_propagate]

        if isTrue(lit): next_to_propagate += 1; continue
        if isFalse(lit): res = False; break
        if lit > 0: assigned[lit] = TruthValue.TRUE
        else: assigned[-lit] = TruthValue.FALSE

        lit_watched = watched[lit]
        watched[lit] = []
        for i in lit_watched:
            clause = clauses[i]
            if clause[0] == -lit: clause[0], clause[1] = clause[1], clause[0]
            if not isTrue(clause[0]):
                for j in range(2, len(clause)):
                    if not isFalse(clause[j]):
                        clause[1], clause[j] = clause[j], clause[1]
                        break
                if isFalse(clause[1]):
                    assigned_trail.append(clause[0])
            watched[-clause[1]].append(i)
        next_to_propagate += 1

    if len(assumptions) > 0:
        for x in assigned_trail[assigned_len:next_to_propagate]: assigned[abs(x)] = TruthValue.UNDEF
        assigned_trail = assigned_trail[:assigned_len]
        next_to_propagate = len(assigned_trail)

    return res

def add_definition(atom, body):
    global clauses
    lits = bodyToLits(body)
    clause = [atom]
    for x in lits:
        clauses.append([-atom, x])
        clause.append(-x)
    clauses.append(clause)

def add_implication(atom, body):
    global clauses
    lits = bodyToLits(body)
    for x in lits: clauses.append([-atom, x])

def add_cc(head, body):
    #lits = bodyToLits(body[:2,3:])
    pass

def add_wc(head, body):
    pass

def add_wc_(head, lits, weights, bound):
    pass

def computeCompletion():
    global next_var

    for x in range(1, next_var):
        x = str(x)
        if x not in definition or len(definition[x]) == 0:
            assigned_trail.append(-x)
        elif len(definition[x]) == 1:
            if definition[x][0][0] == RuleType.NORMAL_RULE:
                add_definition(int(x), [int(x) for x in definition[x][0][1]])
            elif definition[x][0][0] == RuleType.CHOICE_RULE:
                add_implication(int(x), [int(x) for x in definition[x][0][1]])
            elif definition[x][0][0] == RuleType.CARDINALITY_RULE:
                add_cc(int(x), [int(x) for x in definition[x][0][1]])
            elif definition[x][0][0] == RuleType.WEIGHT_RULE:
                add_wc(int(x), [int(x) for x in definition[x][0][1]])
        else:
            supp = [-int(x)]
            for d in definition[x]:
                if d[0] == RuleType.NORMAL_RULE:
                    lits = bodyToLits([int(a) for a in d[1]])
                    assert len(lits) == 1
                    supp.append(lits[0])
                    clauses.append([int(x), -lits[0]])
                elif d[0] == RuleType.CHOICE_RULE:
                    lits = bodyToLits([int(a) for a in d[1]])
                    assert len(lits) == 1
                    supp.append(lits[0])
                else:
                    assert False
            clauses.append(supp)

def attachClauses():
    global watched
    for i in range(1, next_var):
        watched[i] = []
        watched[-i] = []
        in_wc[i] = []
        in_wc[-i] = []
    for i in range(len(clauses)):
        clause = clauses[i]
        assert len(clause) > 0
        if len(clause) == 1:
            assigned_trail.append(clause[0])
        else:
            watched[-clause[0]].append(i)
            watched[-clause[1]].append(i)
    for i in range(len(wc)):
        w = wc[i]
        #TODO

def addAndAttachClause(lits):
    global box_derived

    # already satisfied?
    if [x for x in lits if isTrue(x)]: return

    # simplify
    lits = [x for x in lits if isUndef(x)]

    # is it the box?
    if len(lits) == 0: box_derived = True; return

    # is it unit?
    if len(lits) == 1:
        if not isTrue(lits[0]):
            assigned_trail.append(lits[0])
            propagate()
        return

    # add to watched lists
    watched[-lits[0]].append(len(clauses))
    watched[-lits[1]].append(len(clauses))
    clauses.append(lits)

def checkAddition(nogood):
    if propagate(nogood): exit("Error with 'a {} 0': is not unit entailed".format(' '.join([str(x) for x in nogood])))
    addAndAttachClause([-x for x in nogood])

def checkExtension(atom, lits):
    global next_var
    if atom < next_var: exit("Fail because atom {} is already defined".format(atom))
    next_var = atom + 1
    assigned[atom] = TruthValue.UNDEF
    watched[atom] = []
    watched[-atom] = []
    in_wc[atom] = []
    in_wc[-atom] = []

    if [x for x in lits if isFalse(x)]:
        assigned_trail.append(-atom)
        propagate()
        return

    lits = [x for x in lits if isUndef(x)]
    if len(lits) == 0:
        assigned_trail.append(atom)
        propagate()
        return

    clauses_len = len(clauses)
    add_definition(atom, lits)
    for i in range(clauses_len, len(clauses)):
        watched[-clause[i][0]].append(i)
        watched[-clause[i][1]].append(i)

def checkDeletion(nogood):
    print("Deltions are ignored for now")

def getExternal(body, loop):
    if body[0] == RuleType.NORMAL_RULE or body[0] == RuleType.CHOICE_RULE:
        lits = [int(x) for x in bodyToLits(body[1])]
        for x in lits:
            if x > 0 and x in loop: return None
        return lits
    elif body[0] == RuleType.CARDINALITY_RULE:
        exit("Recursive aggregates are not supported")
    elif body[0] == RuleType.WEIGHT_RULE:
        exit("Recursive aggregates are not supported")
    else:
        assert False

def checkLoop(atoms):
    loop = set(atoms)
    clause = [-atoms[0]]
    if len(definition[str(atoms[0])]) > 1:
        for d in definition[str(atoms[0])]:
            ext = getExternal(d, loop)
            if ext:
                assert len(ext) == 1
                clause.append(ext[0])
    else:
        assert len(definition[str(atoms[0])]) == 1
        ext = getExternal(definition[str(atoms[0])][0], loop)
        if ext:
            assert len(ext) == 1
            clause.extend(ext)
    addAndAttachClause(clause)

def checkProof(line):
    print("Checking", ' '.join(line))
    if line[0] == 'a':
        nogood = [int(x) for x in line[1:-1]]
        checkAddition(nogood)
    elif line[0] == 'e':
        atom = int(line[1])
        lits = [int(x) for x in line[2:-1]]
        checkExtension(atom, lits)
    elif line[0] == 'd':
        nogood = [int(x) for x in line[1:-1]]
        checkDeletion(nogood)
    elif line[0] == 'l':
        atoms = [int(x) for x in line[1:-1]]
        checkLoop(atoms)

if __name__ == "__main__":
    if len(sys.argv) != 3: exit("Please, provide the paths to a program file and a proof file.")
    #TODO: check if the files exist

    callback = readProgram
    for line in fileinput.input(sys.argv[1]):
        line = line.strip()
        if line == '0':
            callback = readVerbatim
        callback(line.split())

    checkProgram()
    computeCompletion()
    attachClauses()
    for i in range(1, next_var): assigned[i] = TruthValue.UNDEF
    propagate()

    for line in fileinput.input(sys.argv[2]):
        line = line.strip()
        checkProof(line.split())

    if box_derived:
        print("PROOF VERIFIED")
