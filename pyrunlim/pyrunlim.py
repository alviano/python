#!/usr/bin/env python3.4

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

VERSION = "2.0"

import argparse
import psutil
import os
import re
import subprocess
import sys
import time
import threading

def parseArguments(process):
    global VERSION
    global GPL
    parser = argparse.ArgumentParser(description=GPL.split("\n")[1], epilog="Copyright (C) 2014  Mario Alviano (mario@alviano.net)")
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + VERSION, help='print version number')
    parser.add_argument('-t', '--time', metavar='<integer>', type=int, help='set time (user+sys) limit to <integer> seconds')
    parser.add_argument('-m', '--memory', metavar='<integer>', type=int, help='set memory (rss+swap) limit to <integer> MB')
    parser.add_argument('-r', '--realtime', metavar='<integer>', type=int, help='set real time limit to <integer> seconds')
    parser.add_argument('-s', '--swap', metavar='<integer>', type=int, help='set swap limit to <integer> MB')
    parser.add_argument('-f', '--frequency', metavar='<integer>', type=int, help='set report frequency to <integer> seconds')
    parser.add_argument('-a', '--affinity', metavar='<integers>', type=str, help='set cpu affinity to swap limit to <integers> (comma-separated list)')
    parser.add_argument('-n', '--nice', metavar='<integer>', type=int, help='set nice to <integer> (default 20)')
    parser.add_argument('-l', '--log', metavar='<filename>', type=str, help='save log to <filename> (default STDERR)')
    parser.add_argument('-o', '--output', metavar='<output>', type=str, choices=['text', 'xml'], default='text', help='output format (text or xml; default is text)')
    parser.add_argument('-R', '--redirect', metavar='<filename>', type=str, help='redirect output (and error) of the command (default is STDOUT)')
    parser.add_argument('-O', '--redirect-output', metavar='<filename>', type=str, help='redirect output of the command (incompatible with -R,--redirect)')
    parser.add_argument('-E', '--redirect-error', metavar='<filename>', type=str, help='redirect error of the command (incompatible with -R,--redirect)')
    parser.add_argument('--no-timestamp', action='store_true', help='do not timestamp output and error of the command')
    parser.add_argument('--regex', metavar='<regex>', type=str, action='append', help='extract data from output and error of the command according to the "named groups" in <regex> (this option can be used several times)')
    parser.add_argument('command', metavar="<command>", help="command to run (and limit)")
    parser.add_argument('args', metavar="...", nargs=argparse.REMAINDER, help="arguments for <command>, or escaped pipes, i.e., \|, followed by other commands and arguments")
    args = parser.parse_args()
    
    if args.time != None:
        process.timelimit = args.time
    if args.memory != None:
        process.memorylimit = args.memory
    if args.realtime != None:
        process.realtimelimit = args.realtime
    if args.swap != None:
        process.swaplimit = args.swap
    if args.frequency != None:
        process.reportFrequency = args.frequency
    if args.affinity != None:
        process.affinity = [int(a) for a in args.affinity.split(",")]
    if args.nice != None:
        process.nice = args.nice
    if args.log != None:
        process.log = open(args.log, 'w')
    if args.output != None:
        if args.output == 'text':
            process.output = TextOutput(process)
        elif args.output == 'xml':
            process.output = XmlOutput(process)
    if args.redirect != None:
        process.redirectOutput = args.redirect
        process.redirectError = args.redirect
    if args.redirect_output != None:
        process.redirectOutput = args.redirect_output
    if args.redirect_error != None:
        process.redirectError = args.redirect_error
    if args.no_timestamp:
        process.timestamp = False
    if args.regex:
        for regex in args.regex:
            process.regexes.append(re.compile(regex))
    process.args.append(args.command)
    process.args.extend(args.args)
    

class TextOutput:
    def __init__(self, process):
        self.process = process
        
    def print(self, msg):
        print("[pyrunlim] %s" % msg, file=self.process.log)
        self.process.log.flush()
        
    def report(self):
        self.print("sample:\t\t%10.3f\t%10.3f\t%10.3f\t%10.1f\t%10.1f\t%10.1f" % (self.process.real, self.process.user, self.process.system, self.process.max_memory, self.process.rss, self.process.swap))
    
    def reportExtract(self, time, dict):
        print("[r%10.3f] " % time, end="", file=self.process.log)
        print("\t".join(["%s=%s" % (key, dict[key]) for key in dict.keys()]), file=self.process.log)

    
    def begin(self):
        self.print("version:\t\t%s" % VERSION)
        self.print("time limit:\t\t%d seconds" % self.process.timelimit)
        self.print("memory limit:\t%d MB" % self.process.memorylimit)
        self.print("real time limit:\t%d seconds" % self.process.realtimelimit)
        self.print("swap limit:\t\t%d MB" % self.process.swaplimit)
        self.print("cpu affinity:\t[%s]" % ", ".join([str(a) for a in self.process.affinity]))
        self.print("nice:\t\t%d" % self.process.nice)
        self.print("running:\t\tbash -c \"%s\"" % " ".join(self.process.args))
        self.print("start:\t\t%s" % time.strftime("%c"))
        self.print("columns:\t\treal (s)\tuser (s)\tsys (s)  \tmax memory (MB)\trss (MB)   \tswap (MB)")

    def end(self):
        self.print("end:  \t\t%s" % time.strftime("%c"))
        self.print("status:\t\t%s" % self.process.status)
        self.print("result:\t\t%s" % str(self.process.result))
        if self.process.redirectOutput != self.process.redirectError:
            self.print("output:\t\t%s" % str(self.process.redirectOutput))
            self.print("error:\t\t%s" % str(self.process.redirectError))
        else:
            self.print("output+error:\t%s" % str(self.process.redirectOutput))
        self.print("children:\t\t%d" % len(self.process.subprocesses))
        self.print("real:\t\t%.3f seconds" % self.process.real)
        self.print("time:\t\t%.3f seconds" % (self.process.system + self.process.user))
        self.print("user:\t\t%.3f seconds" % self.process.user)
        self.print("system:\t\t%.3f seconds" % self.process.system)
        self.print("memory:\t\t%.1f MB" % self.process.max_memory)
        self.print("samples:\t\t%d" % self.process.samplings)

class XmlOutput:
    def __init__(self, process):
        self.process = process
        
    def print(self, msg):
        print(msg, file=self.process.log, end="")

    def println(self, msg):
        print(msg, file=self.process.log)
        self.process.log.flush()

    def report(self):
        self.println("<sample real='%.3f' user='%.3f' sys='%.3f' max-memory='%.1f' rss='%.1f' swap='%.1f' />" % (self.process.real, self.process.user, self.process.system, self.process.max_memory, self.process.rss, self.process.swap))
    
    def reportExtract(self, time, dict):
        self.print("<regex real='%.3f'>" % time)
        for key in dict.keys():
            self.print("<%s>%s</%s>" % (key, dict[key], key))
        self.println("</regex>")

    def begin(self):
        self.print("<pyrunlim version='%s'" % VERSION)
        self.print(" time-limit='%d'" % self.process.timelimit)
        self.print(" memory-limit='%d'" % self.process.memorylimit)
        self.print(" real-time-limit='%d'" % self.process.realtimelimit)
        self.print(" swap-limit='%d'" % self.process.swaplimit)
        self.print(" cpu-affinity='%s'" % ", ".join([str(a) for a in self.process.affinity]))
        self.print(" nice='%d'" % self.process.nice)
        self.print(" running='bash -c \"%s\"'" % " ".join(self.process.args).replace("'", "&apos;"))
        self.print(" start='%s'" % time.strftime("%c"))
        self.println(">")

    def end(self):
        self.print("<stats ")
        self.print(" end='%s'" % time.strftime("%c"))
        self.print(" status='%s'" % self.process.status)
        self.print(" result='%s'" % str(self.process.result))
        if self.process.redirectOutput != self.process.redirectError:
            self.print(" output='%s'" % str(self.process.redirectOutput))
            self.print(" error='%s'" % str(self.process.redirectError))
        else:
            self.print(" output-and-error='%s'" % str(self.process.redirectOutput))
        self.print(" children='%d'" % len(self.process.subprocesses))
        self.print(" real='%.3f'" % self.process.real)
        self.print(" time='%.3f'" % (self.process.system + self.process.user))
        self.print(" user='%.3f'" % self.process.user)
        self.print(" system='%.3f'" % self.process.system)
        self.print(" memory='%.1f'" % self.process.max_memory)
        self.print(" samples='%d'" % self.process.samplings)
        self.println("/>")
        self.println("</pyrunlim>")

class Subprocess:
    def __init__(self):
        self.user = 0
        self.system = 0
    
        self.rss = 0
        self.swap = 0
        
    def update(self, times, memory_info, memory_maps):
        if times.user > self.user:
            self.user = times.user
        if times.system > self.system:
            self.system = times.system
        
        self.rss = memory_info  .rss
        self.swap = 0
        for m in memory_maps:
            self.swap = self.swap + m.swap

class Reader(threading.Thread):
    def __init__(self, begin, input):
        threading.Thread.__init__(self)
        self.begin = begin
        self.input = input
        self.lines = []
        self.active = False

    def run(self):
        self.active = True
        while self.active:
            line = self.input.readline().decode()
            if not line:
                self.active = False
            else:
                self.lines.append((time.time() - self.begin, line if line[-1] != '\n' else line[:-1]))
            
    def stop(self):
        self.active = False
        
    def getLines(self):
        (res, self.lines) = (self.lines, [])
        return res

class Process(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        
        self.output = TextOutput(self)
        
        self.args = []
        self.realtimelimit = 10**100
        self.timelimit = 10**100
        self.memorylimit = 10**100
        self.swaplimit = 10**100
        self.log = sys.stderr
        self.redirectOutput = "/dev/stdout"
        self.redirectError = "/dev/stdout"
        self.stdoutReader = None
        self.stderrReader = None
        self.stdoutFile = sys.stdout
        self.stderrFile = sys.stdout
        self.timestamp = True
        self.regexes = []
        
        self.affinity = psutil.Process(os.getpid()).get_cpu_affinity()
        self.nice = 20
        
        self.done = False
        self.samplings = 0
        self.reportFrequency = 10
        self.numberOfReports = 0
        self.status = "interrupted"
        self.result = None
        self.exit_code = None
        
        self.real = 0
        self.user = 0
        self.system = 0
        
        self.rss = 0
        self.swap = 0
        self.max_memory = 0
        
        self.subprocesses = {}
    
    def run(self):
        self.output.begin()
        self.begin = time.time()
        
        if self.redirectOutput != "/dev/stdout":
            self.stdoutFile = open(self.redirectOutput, "w")
        if self.redirectError != "/dev/stdout":
            if self.redirectError != self.redirectOutput:
                self.stderrFile = open(self.redirectError, "w")
            else:
                self.stderrFile = self.stdoutFile

        self.process = psutil.Popen(["bash", "-c", "(%s)" % (" ".join(self.args),)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.stdoutReader = Reader(self.begin, self.process.stdout)
        self.stderrReader = Reader(self.begin, self.process.stderr)
        self.stdoutReader.run()
        self.stderrReader.run()
        
        self.process.set_nice(self.nice)
        self.process.set_cpu_affinity(self.affinity)
        self.result = self.process.wait()

        self.done = True
        self.stdoutReader.stop()
        self.stderrReader.stop()
        self.processStreams()
        if self.redirectOutput != "/dev/stdout":
            self.stdoutFile.close()
        if self.redirectError != "/dev/stdout" and self.redirectError != self.redirectOutput:
            self.stderrFile.close()
        
        if self.exit_code == None:
            self.status = "complete"
            self.exit_code = 0
        
    def kill(self):
        try:
            subprocesses = self.process.get_children(recursive=True)
        except psutil.NoSuchProcess:
            subprocesses = []
        subprocesses = [p for p in subprocesses if p.cmdline != self.process.cmdline]

        for p in subprocesses:
            try:
                p.terminate()
            except psutil.NoSuchProcess:
                pass
            
        elapsed = 0.0
        while True:
            time.sleep(0.1)
            elapsed = elapsed + 0.1

            running = False
            for p in subprocesses:
                if p.is_running():
                    running = True
            if not running:
                break
            if elapsed >= 1.0:
                for p in subprocesses:
                    try:
                        p.kill()
                    except psutil.NoSuchProcess:
                        pass
                break
    
    def pretty_print(self, prefix, time, line, file):
        if self.timestamp:
            print("[%s%10.3f] %s" % (prefix, time, line), file=file)
        else:
            print(line, file=file)
        
        for regex in self.regexes:
            match = regex.match(line)
            if match:
                self.output.reportExtract(time, match.groupdict())

    def processStreams(self):
        stdout = self.stdoutReader.getLines()
        stderr = self.stderrReader.getLines()
        if self.redirectOutput != self.redirectError:
            for line in stdout:
                self.pretty_print("o", line[0], line[1], self.stdoutFile)
            for line in stderr:
                self.pretty_print("e", line[0], line[1], self.stderrFile)
        else:
            i = 0
            j = 0
            while i < len(stdout) and j < len(stderr):
                if stdout[i][0] < stderr[j][0]:
                    self.pretty_print("o", stdout[i][0], stdout[i][1], self.stdoutFile)
                    i = i + 1
                else:
                    self.pretty_print("e", stderr[j][0], stderr[j][1], self.stderrFile)
                    j = i + 1
            while i < len(stdout):
                self.pretty_print("o", stdout[i][0], stdout[i][1], self.stdoutFile)
                i = i + 1
            while j < len(stderr):
                self.pretty_print("e", stderr[j][0], stderr[j][1], self.stderrFile)
                j = i + 1
        
    def sampler(self):
        if self.done:
            return

        self.processStreams()
        
        subprocesses = [self.process]
        try:
            subprocesses.extend(self.process.get_children(recursive=True))
        except psutil.NoSuchProcess:
            pass
        
        self.rss = 0
        self.swap = 0
        for p in subprocesses:
            if p.pid not in self.subprocesses:
                self.subprocesses[p.pid] = Subprocess()
                    
            try:
                self.subprocesses[p.pid].update(p.get_cpu_times(), p.get_memory_info(), p.get_memory_maps())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            self.rss = self.rss + self.subprocesses[p.pid].rss
            self.swap = self.swap + self.subprocesses[p.pid].swap

        self.rss = self.rss / 1024 / 1024
        self.swap = self.swap / 1024 / 1024

        if self.rss + self.swap > self.max_memory:
            self.max_memory = self.rss + self.swap

        self.real = time.time() - self.begin
        self.user = 0
        self.system = 0
        for p in self.subprocesses:
            self.user = self.user + self.subprocesses[p].user
            self.system = self.system + self.subprocesses[p].system
        
        self.samplings = self.samplings + 1
        if int(self.real / self.reportFrequency) > self.numberOfReports:
            self.numberOfReports = self.numberOfReports + 1
            self.output.report()
        
        self.checkLimit()
    
    def checkLimit(self):
        if self.real > self.realtimelimit:
            self.status = "out of time (real)"
            self.exit_code = 1
            self.kill()
        elif self.user + self.system > self.timelimit:
            self.status = "out of time"
            self.exit_code = 2
            self.kill()
        elif self.max_memory > self.memorylimit:
            self.status = "out of memory"
            self.exit_code = 3
            self.kill()
        elif self.swap > self.swaplimit:
            self.status = "out of memory (swap)"
            self.exit_code = 4
            self.kill()
            
    def end(self):
        self.output.end()
        if self.log != sys.stderr:
            self.log.close()
            
if __name__ == "__main__":
    process = Process()
    parseArguments(process)
    
    process.start()

    count = 0
    while not process.done:
        count = count + 1
        if count < 10:
            time.sleep(.1)
        elif count < 30:
            time.sleep(.2)
        elif count < 60:
            time.sleep(.5)
        else:
            time.sleep(1)
        process.sampler()
        
    process.end()
    
    sys.exit(process.exit_code)
