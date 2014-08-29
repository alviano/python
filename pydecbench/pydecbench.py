#!/usr/bin/env python3

GPL = """
Run a command reporting statistics and possibly limiting usage of resources.
Copyright (C) 2014  Mario Alviano (mario@alviano.net)

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

VERSION = "1.0"

import argparse
import psutil
import subprocess
import sys
import os

dirname = os.path.dirname(__file__)

def parseArguments(instance):
    global VERSION
    global GPL
    parser = argparse.ArgumentParser(description=GPL.split("\n")[1], epilog="Copyright (C) 2014  Mario Alviano (mario@alviano.net)")
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + VERSION, help='aspModel.append version number')
    parser.add_argument('userFunction', metavar='<userFunction>', help='file defining userFunction()')
    args = parser.parse_args()

    if not os.path.exists(args.userFunction):
        sys.exit("File not found: %s" % (args.userFunction,))
    exec(open(args.userFunction).read())
    if 'userFunction' not in locals():
        sys.exit("File %s does not provide userFunction()" % (args.userFunction,))
    instance.userFunction = args.userFunction

class Target:
    def __init__(self, pdb_target):
        self.id = pdb_target[1:]
        self.requisites = []
        self.predecessors = []
        self.limits = {}
        self.parameters = {}
    
    def addLimit(self, pdb_limit):
        if pdb_limit[2] != 'unbounded':
            self.limits[pdb_limit[1]] = int(pdb_limit[2])
    
    def addParameter(self, pdb_parameter):
        key = int(pdb_parameter[4])
        if key not in self.parameters:
            self.parameters[key] = []
        self.parameters[key].append(pdb_parameter[3])
        
    def addRequisite(self, pdb_requires):
        self.requisites.append(self.targetId(pdb_requires[3:]))
    
    def addPredecessor(self, pdb_follows):
        self.predecessors.append(self.targetId(pdb_follows[3:]))
    
    def targetId(self, id=None):
        if id is None:
            id = self.id
        return str(id).replace("(","_").replace(")","_").replace(" ","_").replace("'","_").replace('"',"_").replace(",","_").replace("/","_").replace(".","_")
        
    def command(self):
        ret = []
        for key in sorted(self.parameters.keys()):
            ret.extend(self.parameters[key])
        return " ".join(ret)
    
    def print(self):
        id = self.targetId()
        print(".pydecbench.%s.log: %s %s" %  (id, " ".join([".pydecbench.%s.log" % r for r in self.requisites]), " ".join([".pydecbench.%s.log" % p for p in self.predecessors])))
        print("\t-", end="")
        if self.requisites:
            print("\tif %s; then \\" % " && ".join(["[ -f .pydecbench.%s.log ]" % r for r in self.requisites]))
        print("\tpyrunlim.py --output xml %s %s %s \"%s\" ;\\" % (
            "" if "memory" not in self.limits else "--memory %d" % self.limits["memory"],
            "" if "cpu" not in self.limits else "--time %d" % self.limits["cpu"],
            "--log=.pydecbench.%s.logtmp --redirect-output=.pydecbench.%s.stdout --redirect-error=.pydecbench.%s.stderr" % (id, id, id),
            self.command(),
        ))
        print("\tmv .pydecbench.%s.logtmp .pydecbench.%s.log" % (id, id), end="")
        if self.requisites:
            print(";\\\n\telse echo \"Skip\";\\\n\tfi", end="") 
        print("\n")
    
class DecBench:
    def __init__(self):
        self.aspModel = []
        self.atoms = {}

    def runAsp(self):
        gringo = psutil.Popen(["gringo4"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = ""
        for line in self.aspModel:
            data = "%s%s\n" % (data, line)
        (out, err) = gringo.communicate(data.encode())
        out = out.decode().split('\n')

        atoms = []
        count = 0
        for line in out:
            if line == '0':
                count = count + 1
            elif count == 1:
                def parse(predicate, terms):
                    args = [predicate]
                    last = 0
                    i = 0
                    while i < len(terms):
                        if terms[i] == '(':
                            (inArgs, lastIn) = parse(terms[last:i], terms[i+1:])
                            args.append(inArgs)
                            i = i + lastIn + 1
                            last = i + 1
                        elif terms[i] == ')':
                            if last != i:
                                args.append(terms[last:i])
                            i = i + 1
                            break
                        elif terms[i] == ',':
                            args.append(terms[last:i])
                            last = i + 1
                        elif terms[i] == '"' or terms[i] == "'":
                            i = i + 1 + terms[i+1:].find(terms[i])
                            args.append(terms[last+1:i])
                            i = i + 1
                            if terms[i] == ')':
                                i = i + 1
                                break
                            last = i + 1
                        i = i + 1
                    return (tuple(args), i)
                    
                atom = line[line.find(' ')+1:]
                args = parse(atom[:atom.find('(')], atom[atom.find('(')+1:])[0]
                if args[0] not in self.atoms:
                    self.atoms[args[0]] = []
                self.atoms[args[0]].append(args)

    def createMakefile(self):
        targets = {}
        for target in self.atoms["pdb_target"]:
            target = Target(target)
            targets[target.id] = target
        if "pdb_limit" in self.atoms:
            for limit in self.atoms["pdb_limit"]:
                if limit[3:] in targets:
                    target = targets[limit[3:]]
                    target.addLimit(limit)
        if "pdb_parameter" in self.atoms:
            for parameter in self.atoms["pdb_parameter"]:
                if parameter[1:3] in targets:
                    target = targets[parameter[1:3]]
                    target.addParameter(parameter)
        if "pdb_requires" in self.atoms:
            for requires in self.atoms["pdb_requires"]:
                if requires[1:3] in targets:
                    target = targets[requires[1:3]]
                    target.addRequisite(requires)
        if "pdb_follows" in self.atoms:
            for follows in self.atoms["pdb_follows"]:
                if follows[1:3] in targets:
                    target = targets[follows[1:3]]
                    target.addPredecessor(requires)
        
        print("all: %s\n" % " ".join([".pydecbench.%s.log" % targets[target].targetId() for target in targets.keys()]))
        #print(".SILENT: %s\n" % " ".join([".pydecbench.%s.output" % targets[target].targetId() for target in targets.keys()]))
        print(".PHONY: all clean\n")
        print("clean:\n\trm -f .pydecbench.*\n")
        
        for target in targets:
            targets[target].print()

    def verbatim(self, text):
        global dirname
        self.aspModel.append(text.replace("$DIRNAME", dirname))

    def createGroup(self, id, command, parameters=[]):
        files = sorted([file for file in self.executeAndSplit(command)])
        self.aspModel.append("group(\"%s\")." % id)
        for parameter in parameters:
            self.aspModel.append("""parameter("group(%s)", %s)""" % (id, parameter))
        for file in files:
            self.aspModel.append("group(id(\"%s\",\"%s\"))." % (id, file))
            self.aspModel.append("testcase(id(\"%s\",\"%s\"))." % (id, file))
            self.aspModel.append("parentOf(\"%s\", id(\"%s\",\"%s\"))." % (id, id, file))
            self.aspModel.append("data(id(\"%s\",\"%s\"), filename, \"%s\")." % (id, file, file))

    def executeAndSplit(self, command):
        global dirname
        lines = subprocess.check_output(["bash", "-c", command.replace("$DIRNAME", dirname)])
        return lines.decode().strip().split("\n")
        
    def logicModel(self):
        self.aspModel.append("""
            pdb_parentOf(nil,G) :- group(G), #count{G1 : parentOf(G1,G)} = 0.
            pdb_parentOf(X,Y) :- parentOf(X,Y).
            
            pdb_run(S,G) :- run(S,G).
            pdb_run(S,G1) :- pdb_run(S,G), parentOf(G,G1).
            
            pdb_resource(cpu).
            pdb_resource(memory).
            
            pdb_limit(R,V,S,nil) :- limit(R,V,S), solver(S,_).
            pdb_limit(R,V,S,nil) :- limit(R,V), solver(S,_), #count{V1 : limit(R,V1,S)} = 0.
            pdb_limit(R,unbounded,S,nil) :- pdb_resource(R), solver(S,_), #count{V1 : limit(R,V1,S)} = 0, #count{V1 : limit(R,V1)} = 0.
            pdb_limit(R,V,S,G) :- pdb_run(S,G), limit(R,V,S,G).
            pdb_limit(R,V,S,G) :- pdb_run(S,G), limit(R,V,G), #count{V1 : limit(R,V1,S,G)} = 0.
            pdb_limit(R,V,S,G1) :- pdb_limit(R,V,S,G), pdb_parentOf(G,G1), pdb_run(S,G1), #count{V1 : limit(R,V1,G1)} = 0, #count{V1 : limit(R,V1,S,G1)} = 0.
            
            pdb_data(I,K,V) :- data(I,K,V).
            pdb_data(I1,K,V) :- pdb_data(I,K,V), pdb_parentOf(I,I1), #count{V1 : data(I1,K,V1)} = 0.

            parameter(S,G,V) :- pdb_run(S,G), parameter(solver(S),V).
            parameter(S,G,V,P) :- pdb_run(S,G), parameter(solver(S),V,P).
            parameter(S,G,V) :- pdb_run(S,G), parameter(group(G),V).
            parameter(S,G,V,P) :- pdb_run(S,G), parameter(group(G),V,P).
            pdb_parameter(S,G,V,0) :- solver(S,V), pdb_run(S,G), not pdb_pipe(V). pdb_pipe(pipe(A,B)) :- solver(_, pipe(A,B)). pdb_pipe(pipe(A,B,C)) :- solver(_, pipe(A,B,C)). pdb_pipe(pipe(A,B,C,D)) :- solver(_, pipe(A,B,C,D)). pdb_pipe(pipe(A,B,C,D,E)) :- solver(_, pipe(A,B,C,D,E)).
            pdb_parameter(S,G,A,0) :- solver(S,pipe(A,B)), pdb_run(S,G). pdb_parameter(S,G,"|",999999) :- solver(S,pipe(A,B)), pdb_run(S,G). pdb_parameter(S,G,B,999999+1) :- solver(S,pipe(A,B)), pdb_run(S,G).
            pdb_parameter(S,G,A,0) :- solver(S,pipe(A,B,C)), pdb_run(S,G). pdb_parameter(S,G,"|",999999) :- solver(S,pipe(A,B,C)), pdb_run(S,G). pdb_parameter(S,G,B,999999+1) :- solver(S,pipe(A,B,C)), pdb_run(S,G). pdb_parameter(S,G,"|",2*999999) :- solver(S,pipe(A,B,C)), pdb_run(S,G). pdb_parameter(S,G,C,2*999999+1) :- solver(S,pipe(A,B,C)), pdb_run(S,G).
            %4
            %5
            pdb_parameter(S,G,V,999999-2) :- parameter(S,G,V), not pdb_pipe(S). pdb_pipe(pipe(S,N)) :- parameter(pipe(S,N),G,V).
            pdb_parameter(S,G,V,(N+1)*999999-2) :- parameter(pipe(S,N),G,V).
            pdb_parameter(S,G,V,P) :- parameter(S,G,V,priority(P)), not pdb_pipe(S). pdb_pipe(pipe(S,N)) :- parameter(pipe(S,N),G,V,P).
            pdb_parameter(S,G,V,P+(N+1)*999999-2) :- parameter(pipe(S,N),G,V,priority(P)).
            pdb_parameter(S,G,key_value(K,V),999999-2) :- parameter(S,G,K,V), not pdb_priority(V), not pdb_pipe(S).  pdb_priority(priority(P)) :- parameter(S,G,V,priority(P)).
            pdb_parameter(S,G,key_value(K,V),(N+1)*999999-2) :- parameter(pipe(S,N),G,K,V), not pdb_priority(V).
            pdb_parameter(S,G,key_value(K,V),P) :- parameter(S,G,K,V,priority(P)), not pdb_pipe(S). pdb_pipe(pipe(S,N)) :- parameter(pipe(S,N),G,K,V,P).
            pdb_parameter(S,G,key_value(K,V),P+(N+1)*999999-2) :- parameter(pipe(S,N),G,K,V,priority(P)).
            pdb_parameter(S,G1,V,P) :- pdb_parameter(S,G,V,P), pdb_parentOf(G,G1), not pdb_pipe(S).
            pdb_parameter(S,G1,V,P+(N+1)*999999-2) :- pdb_parameter(pipe(S,N),G,V,P), pdb_parentOf(G,G1).
            
            pdb_target(S,G) :- pdb_run(S,G), testcase(G).
            
            pdb_requires(S1,G1,S2,G2) :- requires(S1,G1,S2,G2).
            pdb_requires(S1,G,S2,G) :- requires(S1,S2), not pdb_solver(S1), not pdb_solver(S2), not pdb_group(S1), not pdb_group(S2), pdb_run(S1,G), pdb_run(S2,G). pdb_solver(solver(S)) :- requires(solver(S),_). pdb_solver(solver(S)) :- requires(_,solver(S)). pdb_group(group(G)) :- requires(group(G),_). pdb_group(group(G)) :- requires(_,group(G)).
            pdb_requires(S1,G,S2,G) :- requires(solver(S1),solver(S2)), pdb_run(S1,G), pdb_run(S2,G).
            pdb_requires(S,G1,S,G2) :- requires(group(G1),group(G2)), pdb_run(S,G1), pdb_run(S,G2).

            pdb_follows(S1,G1,S2,G2) :- follows(S1,G1,S2,G2).
            pdb_follows(S1,G,S2,G) :- follows(S1,S2), not pdb_solver(S1), not pdb_solver(S2), not pdb_group(S1), not pdb_group(S2), pdb_run(S1,G), pdb_run(S2,G). pdb_solver(solver(S)) :- follows(solver(S),_). pdb_solver(solver(S)) :- follows(_,solver(S)). pdb_group(group(G)) :- follows(group(G),_). pdb_group(group(G)) :- follows(_,group(G)).
            pdb_follows(S1,G,S2,G) :- follows(solver(S1),solver(S2)), pdb_run(S1,G), pdb_run(S2,G).
            pdb_follows(S,G1,S,G2) :- follows(group(G1),group(G2)), pdb_run(S,G1), pdb_run(S,G2).
            
            pdb_validator(S,G,V,nil) :- validator(group(G),V), pdb_run(S,G).
            
            #show pdb_target/2.
            #show pdb_limit/4.
            #show pdb_parameter/4.
            #show pdb_requires/4.
            #show pdb_follows/4.
            #show pdb_validator/4.
        """)

if __name__ == "__main__":
    instance = DecBench()
    parseArguments(instance)

    exec(open(instance.userFunction).read())
    userFunction(instance)
    instance.logicModel()
    instance.runAsp()
    instance.createMakefile()
