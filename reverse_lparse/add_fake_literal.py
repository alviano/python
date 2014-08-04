#!/usr/bin/env python3.3

import fileinput

rules = []
names = []
max = 0

def readProgram(line):
    global max
    line = line.split()
    if line[0] == '1':
        if int(line[1]) > max:
            max = int(line[1])
        head = []
        head.append(line[1])
        pos = []
        neg = []
        for i in range(4,4+int(line[3])):
            neg.append(line[i])
            if int(line[i]) > max:
                max = int(line[i])
        for i in range(4+int(line[3]),len(line)):
            pos.append(line[i])
            if int(line[i]) > max:
                max = int(line[i])
        rules.append((head, pos, neg))
    
def readNames(line):
    names.append(line)
    
def printProgram():
    global rules
    for rule in rules:
        rule[2].append(str(max+1))
        rule[1].append(str(max+2))
        print("1 %s %d %d %s %s" % (rule[0][0], len(rule[1]) + len(rule[2]), len(rule[2]), " ".join(rule[2]), " ".join(rule[1]) ))
    rules = []
    rules.append(([str(max+1)], [], [str(max+2)]))
    rules.append(([str(max+2)], [], [str(max+1)]))
    for rule in rules:
        print("1 %s %d %d %s %s" % (rule[0][0], len(rule[1]) + len(rule[2]), len(rule[2]), " ".join(rule[2]), " ".join(rule[1]) ))
    print(0)
    for name in names:
        print(name)
    print("0\nB+\n0\nB-\n1\n0\n1")


callback = [readProgram, readNames]
state = 0
for line in fileinput.input('-'):
    line = line.strip()
    if line == '0':
        state = state + 1
        if state >= 2:
            break
    else:
        callback[state](line)
        
printProgram()
