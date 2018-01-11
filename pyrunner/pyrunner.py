#!/usr/bin/env python3

GPL = """
Run benchmarks.
Copyright (C) 2014-2015  Mario Alviano (mario@alviano.net)

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

VERSION = "1.5"

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

dirname = os.path.dirname(__file__)

def parseArguments(runner):
    global VERSION
    global GPL
    parser = argparse.ArgumentParser(description=GPL.split("\n")[1], epilog="Copyright (C) 2014-2015  Mario Alviano (mario@alviano.net)")
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + VERSION, help='print version number')
    parser.add_argument('-r', '--run', metavar='<filename>', action='append', help='python code defining benchmarks and commands (use this flag for each file to be run)')
    parser.add_argument('-l', '--log', metavar='<filename>', type=str, help='save log to <filename> (default STDERR)')
    parser.add_argument('-o', '--output', metavar='<output>', type=str, choices=['text', 'xml'], default='text', help='output format (text or xml; default is text)')
    parser.add_argument('-d', '--output-directory', metavar='<output-directory>', type=str, default='.', help='directory for storing output files (default is .)')
    parser.add_argument('-f', '--fix-xml', metavar='<filename>', type=str, help="fix unclosed tags in xml file (and exit)")
    parser.add_argument('-s', '--split-xml', metavar='<filename,count>', type=str, help="split the passed file into blocks of 'count' elements (and exit)")
    args = parser.parse_args()
    
    if args.run != None:
        runner.runfiles = args.run
    if args.log != None:
        runner.log = open(args.log, 'w')
    if args.output != None:
        if args.output == 'text':
            runner.output = TextOutput(runner)
        elif args.output == 'xml':
            runner.output = XmlOutput(runner)
    if args.output_directory != None:
        runner.outputDirectory = args.output_directory
    if args.fix_xml != None:
        runner.fixXml(args.fix_xml)
    if args.split_xml != None:
        arg = args.split_xml.split(',')
        if len(arg) != 2: sys.exit("Please, provide extactly two (comma separated) arguments to --split-xml.")
        try:
            arg[1] = int(arg[1])
        except ValueError:
            sys.exit("Second argument of --split-xml must be an integer: %s" % (arg[1],))
        runner.splitXml(arg[0], arg[1])
        
    if args.output_directory == None:
        print("pyrunner.py: error:  the following arguments are required: -r/--run (or use -f/--fix-xml)")

        
class Command:
    def __init__(self, id, command, dependencies=set(), validator=AllValidator()):
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
        self.testcases = []
        for testcase in testcases:
            item = []
            for i in range(0, len(testcase)):
                item.append(testcase[i].replace("$DIRNAME", dirname))
            self.testcases.append(tuple(item))
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
        self.setPyrunlim(pyrunlim)
        self.runfiles = []
        self.commands = {}
        self.commandsOrder = []
        self.benchmarks = {}
        self.benchmarksOrder = []
        self.log = sys.stderr
        self.output = XmlOutput(self)
        self.outputDirectory = '.'
        
    def setPyrunlim(self, value):
        self.pyrunlim = [s.replace("$DIRNAME", dirname) for s in value]

    def getFiles(self, directory, nameSchema="*"):
        files = subprocess.check_output(["find", directory, "-name", nameSchema])
        return sorted(files.decode().strip().split("\n"))

    def executeAndSplit(self, command):
        global dirname
        lines = subprocess.check_output(["bash", "-c", "PYTHONHASHSEED=0 " + command.replace("$DIRNAME", dirname)])
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
        
    def _replaceDirname(self):
        global dirname
        for file in self.runfiles:
            if not os.path.exists(file):
                sys.exit("File not found: %s" % (file,))
            if os.path.isabs(file[0]):
                dirname =  os.path.dirname(file)
            else:
                dirname = "%s/%s" % (os.getcwd(),  os.path.dirname(file))
            exec(open(file).read())
        for benchmark in self.benchmarks:
            self.benchmarks[benchmark].validator.setDirname(dirname)
        for command in self.commands:
            self.commands[command].validator.setDirname(dirname)
        
    def run(self):
        if not os.path.exists(self.outputDirectory):
            os.makedirs(self.outputDirectory)

        self._replaceDirname()
        self.output.begin()
        time_str = time.strftime(".%Y-%m-%d_%H-%M-%S", time.gmtime(self.beginTime))
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
                        args.append("--redirect-output=%s/%s_%05d_OUT_%s" % (self.outputDirectory, time_str, counter, command.id))
                        args.append("--redirect-error=%s/%s_%05d_ERR_%s" % (self.outputDirectory, time_str, counter, command.id))
                        args.append(completeCommand)
                        proc = subprocess.Popen(args, stderr=subprocess.PIPE)
                        (out, err) = proc.communicate()
                        xml = etree.XML(err.decode())

                        self.output.report(xml)
                        if  xml.xpath("//stats/@status != 'complete'"):
                            benchmark.onInvalidRun(testcase, command)
                            command.onInvalidRun(benchmark, testcase)
                            self.output.onIncompleteRun()
                        elif command.validator.valid(command, benchmark, testcase, xml) and benchmark.validator.valid(command, benchmark, testcase, xml):
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
            elif line[-2:] != "/>" and not line.endswith("</%s>" % (tag,)):
                tags.append(tag)

        while tags:
            print("</%s>" % tags.pop())    
            
        exit(0)

    def splitXml(self, filename, count):
        c = 0
        n = 0
        f = None
        b = None

        tags = []
        for line in fileinput.input(filename):
            if line.startswith('<pyrunner>'): pass
            elif line.startswith('</pyrunner>'):
                f.write('</benchmark>\n')
                f.write('</pyrunner>\n')
                f.close()
                f = None
            elif line.startswith('<benchmark '): b = line
            elif line.startswith('</benchmark>'): b = None
            elif line.startswith('<testcase '):
                if f is None:
                    n += 1
                    f = open('%s.split.%d.xml' % (filename, n), 'w')
                    f.write('<pyrunner>\n')
                    assert b is not None
                    f.write(b)
                f.write(line)
                c += 1
            elif line.startswith('</testcase>'):
                assert f is not None
                f.write(line)
                if c == count:
                    f.write('</benchmark>\n')
                    f.write('</pyrunner>\n')
                    f.close()
                    f = None
                    c = 0
            else:
                assert f is not None
                f.write(line)
        assert f is None
        exit(0)

if __name__ == "__main__":
    runner = Runner()
    parseArguments(runner)

    runner.run()
