#!/usr/bin/env python3

import fileinput
import sys
import os

if __name__ == "__main__":
    if len(sys.argv) != 3: sys.exit("error: usage: %s <maxsat-instance> <number-of-agents>" % (sys.argv[0],))
    if not os.path.exists(sys.argv[1]): sys.exit("File not found: %s" % (sys.argv[1],))
    
    nagents = int(sys.argv[2])
    agents = []
    for i in range(0,nagents): agents.append(([],[]))
    nextAgent = 0

    gamma = []
    vars, clauses, top = None, None, None
    for line in fileinput.input(sys.argv[1]):
        line = line.strip().split()
        if line[0] == 'p':
            assert(line[1] == 'wcnf')
            vars = int(line[2])
            clauses = int(line[3])
            top = int(line[4]) if len(line) > 4 else 2**63
        elif line[0] == 'c': continue
        elif line[0] == str(top):
            gamma.append(" ".join(line[1:]))
        else:
            assert(top is not None)
            if len(line) > 3:
                vars = vars + 1
                agents[nextAgent][0].append(str(vars))
                agents[nextAgent][1].append(line[0])
                line[0] = str(-vars)
                gamma.append(" ".join(line))
            else:
                agents[nextAgent][0].append(line[1])
                agents[nextAgent][1].append(line[0])
            nextAgent = (nextAgent + 1) % nagents
    
    print("p fcnf %s %s %s" % (vars, len(gamma), len(agents)))
    for f in gamma: print(f)
    for agent in agents:
        print("%d %s %s 0" % (len(agent[0]), " ".join(agent[0]), " ".join(agent[1])))