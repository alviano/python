#!/usr/bin/env python3

"""
A script to normalize lparse programs so that completion can be computed without the introduction of auxiliary atoms.
An lparse program is read from STDIN, and the normalized lparse program is printed on STDOUT.

"""

from collections import OrderedDict
from enum import Enum
import fileinput

class RuleType(Enum):
    NORMAL_RULE = 1
    CARDINALITY_RULE = 2
    CHOICE_RULE = 3
    WEIGHT_RULE = 5

definition = OrderedDict()
minimize_rules = []
verbatim = []
next_var = 0

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

def minimize_rule(x):
    global next_var
    for id in x[2:2+int(x[0])]: next_var = max(next_var, int(id)+1)
    return x

def isUnit(x):
    return x[1][0] == '1' or x[1][0] == '0'

def print_definition(head, body):
    if body[0] == RuleType.NORMAL_RULE:
        print(1, head, ' '.join(body[1]))
    elif body[0] == RuleType.CARDINALITY_RULE:
        print(2, head, ' '.join(body[1]))
    elif body[0] == RuleType.CHOICE_RULE:
        print(3, 1, head, ' '.join(body[1]))
    elif body[0] == RuleType.WEIGHT_RULE:
        print(5, head, ' '.join(body[1]))
    else:
        exit("Unexpcted body of type {}".format(body[0]))

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
        minimize_rules.append(minimize_rule(line[2:]))
    else:
        exit("Cannot handle rule {}".format(' '.join(line)))

def readVerbatim(line):
    verbatim.append(line)

def printProgram():
    global next_var
    next_var = max(next_var, max([int(x) for x in definition]) + 1)

    for x in definition:
        if len(definition[x]) == 1:
            print_definition(x, definition[x][0])
        else:
            for d in definition[x]:
                if isUnit(d):
                    print_definition(x, d)
                else:
                    print_definition(str(next_var), d)
                    print(1, x, 1, 0, next_var)
                    next_var += 1
    for x in minimize_rules: print(6, 0, ' '.join(x))
    for x in verbatim: print(' '.join(x))

if __name__ == "__main__":
    callback = readProgram
    for line in fileinput.input('-'):
        line = line.strip()
        if line == '0':
            callback = readVerbatim
        callback(line.split())

    printProgram()
