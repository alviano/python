#!/usr/bin/env python3.3

import argparse
import fileinput
from lxml import etree
import re
import subprocess
import sys
import time
import os

from output import *
from validator import *

VERSION = "1.0"

def parseArguments(runner):
    parser = argparse.ArgumentParser(description='Run benchmarks.')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s %(VERSION)s', help='print version number')
    parser.add_argument('-l', '--log', metavar='<filename>', type=str, help='save log to <filename> (default STDERR)')
    parser.add_argument('-o', '--output', metavar='<output>', type=str, choices=['text', 'xml'], default='text', help='output format (text or xml; default is text)')
    parser.add_argument('-f', '--fix-xml', metavar='<filename>', type=str, help="fix unclosed tags in xml file (and exit)")
    args = parser.parse_args()
    
    if args.log != None:
        runner.log = open(args.log, 'w')
    if args.output != None:
        if args.output == 'text':
            runner.output = TextOutput(runner)
        elif args.output == 'xml':
            runner.output = XmlOutput(runner)
    if args.fix_xml != None:
        runner.fixXml(args.fix_xml)

        
class Command:
    def __init__(self, id, command, dependencies=set(), validator=ExitCodeValidator()):
        global dirname
        
        self.runner = None
        self.id = id
        self.command = command.replace("$DIRNAME", dirname)
        self.validator = validator
        self.dependencies = dependencies
        self.complete = set()
        
    def onValidRun(self, benchmark, testcase):
        self.complete.add((benchmark.id, testcase))
    def onInvalidRun(self, benchmark, testcase):
        pass
        
    def hasToSkip(self, benchmark, testcase):
        for dependency in self.dependencies:
            if (benchmark.id, testcase) not in self.runner.commands[dependency].complete:
                return True
        return False

class Benchmark:
    def __init__(self, id, sharedOptions=[], testcases=[], validator=AllValidator(), stopAfterFirstFailure=False):
        global dirname
        self.runner = None
        self.id = id
        self.sharedOptions = [o.replace("$DIRNAME", dirname) for o in sharedOptions]
        self.testcases = testcases
        self.validator = validator
        self.stopped = set() if stopAfterFirstFailure else None
            
    def onValidRun(self, testcase, command):
        pass
    def onInvalidRun(self, testcase, command):
        if self.stopped is not None:
            self.stopped.add(command.id)
        
    def hasToSkip(self, command):
        return self.stopped is not None and command.id in self.stopped

class Runner:
    def __init__(self, pyrunlim=[]):
        global dirname
        self.beginTime = time.time()
        self.pyrunlim = [s.replace("$DIRNAME", dirname) for s in pyrunlim]
        self.commands = {}
        self.commandsOrder = []
        self.benchmarks = {}
        self.benchmarksOrder = []
        self.log = sys.stderr
        self.output = XmlOutput(self)

    def getFiles(self, directory, nameSchema="*"):
        files = subprocess.check_output(["find", directory, "-name", nameSchema])
        return sorted(files.decode().strip().split("\n"))

    def executeAndSplit(self, command):
        global dirname
        lines = subprocess.check_output(["bash", "-c", command.replace("$DIRNAME", dirname)])
        return lines.decode().strip().split("\n")

    def addCommand(self, command):
        assert(command.id not in self.commands)
        command.runner = self
        self.commands[command.id] = command
        self.commandsOrder.append(command)
        
    def addBenchmark(self, benchmark):
        assert(benchmark.id not in self.benchmarks)
        benchmark.runner = self
        self.benchmarks[benchmark.id] = benchmark
        self.benchmarksOrder.append(benchmark)
        
    def run(self):
        self.output.begin()
        time_str = time.strftime(".%Y-%m-%d_%H:%M:%S", time.gmtime(self.beginTime))
        counter = 0
        for benchmark in self.benchmarksOrder:
            self.output.beginBenchmark(benchmark)
            for testcase in benchmark.testcases:
                self.output.beginTestcase(testcase)
                for command in self.commandsOrder:
                    completeCommand = command.command
                    for i in range(len(testcase), 0, -1):
                        completeCommand = completeCommand.replace("$%d" % (len(benchmark.sharedOptions)+i), testcase[i-1])
                    for i in range(len(benchmark.sharedOptions), 0, -1):
                        completeCommand = completeCommand.replace("$%d" % i, benchmark.sharedOptions[i-1])
                    self.output.beginCommand(command)
                    
                    if benchmark.hasToSkip(command) or command.hasToSkip(benchmark, testcase):
                        self.output.skip()
                    else:
                        args = list(self.pyrunlim)
                        counter = counter + 1
                        args.append("--redirect-output=%s_%05d_OUT_%s" % (time_str, counter, command.id))
                        args.append("--redirect-error=%s_%05d_ERR_%s" % (time_str, counter, command.id))
                        args.append(completeCommand)
                        proc = subprocess.Popen(args, stderr=subprocess.PIPE)
                        (out, err) = proc.communicate()
                        xml = etree.XML(err.decode())

                        self.output.report(xml)
                        if command.validator.valid(command, benchmark, testcase, xml) and benchmark.validator.valid(command, benchmark, testcase, xml):
                            benchmark.onValidRun(testcase, command)
                            command.onValidRun(benchmark, testcase)
                            self.output.onValidRun()
                        else:
                            benchmark.onInvalidRun(testcase, command)
                            command.onInvalidRun(benchmark, testcase)
                            self.output.onInvalidRun()
                        
                    self.output.endCommand(command)
                self.output.endTestcase(testcase)
            self.output.endBenchmark(benchmark)

        self.output.end()
        if self.log != sys.stderr:
            self.log.close()
            
    def fixXml(self, filename):
        tags = []
        for line in fileinput.input(filename):
            line = line.strip()
            print(line)
            tag = line[1:].split()[0]
            if tag[-1] == ">":
                tag = tag[:-1]
            if tag[0] == "/":
                if tags.pop() != tag[1:]:
                    sys.exit("Can't fix this XML!")
            elif line[-2:] != "/>":
                tags.append(tag)

        while tags:
            print("</%s>" % tags.pop())    
            
        exit(0)

if __name__ == "__main__":
    """
        This is an example main.
        You should import this file and declare your own main function.
        In a nutshell, creare a Runner instance pointing to pyrunlim.
        Then, add commands to be tested and benchmarks to be run.
    """

    dirname = os.path.dirname(__file__)
    
    runner = Runner([
        "$DIRNAME/../pyrunlim/pyrunlim.py", 
        "--time=%d" % 600, 
        "--memory=%d" % (3 * 1024), 
        "--affinity=0",
        "--output=xml"
    ])
    parseArguments(runner)
    
    runner.addCommand(Command("gringo+clasp", "gringo --shift $1 $2 | clasp"))
    
    runner.addBenchmark(Benchmark("StableMarriageASP", sharedOptions=["$DIRNAME/StableMarriage/encoding.lp"], testcases=sorted([(file,) for file in runner.executeAndSplit("ls $DIRNAME/StableMarriage/*.asp")]), validator=ExitCodeValidator([10, 20, 30])))

    runner.run()
