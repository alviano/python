#!/usr/bin/env python3.4

import fileinput

rules = []
names = {}

def readProgram(line):
    if line[0] == '1':
        if line[1] not in names:
            names[line[1]] = line[1]
        head = []
        if line[1] != '1':
            head.append(line[1])
        pos = []
        neg = []
        for i in range(4,4+int(line[3])):
            neg.append(line[i])
            if line[i] not in names:
                names[line[i]] = line[i]
        for i in range(4+int(line[3]),len(line)):
            pos.append(line[i])
            if line[i] not in names:
                names[line[i]] = line[i]
        rules.append((head, pos, neg))
    
def readNames(line):
    names[line[0]] = line[1]
    
def printProgram():
    for rule in rules:
        print("%s%s%s%s%s%s%s." % (" | ".join([names[a] for a in rule[0]]), " " if rule[0] else "", ":- " if rule[1] or rule[2] else "", ", ".join([names[a] for a in rule[1]]), ", " if len(rule[1]) > 0 and len(rule[2]) > 0 else "", "not " if len(rule[2]) > 0 else "", ", not ".join([names[a] for a in rule[2]])))

callback = [readProgram, readNames]
state = 0
for line in fileinput.input('-'):
    line = line.strip()
    if line == '0':
        state = state + 1
        if state >= 2:
            break
    else:
        callback[state](line.split())
        
printProgram()
