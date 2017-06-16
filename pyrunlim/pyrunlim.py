#!/usr/bin/env python3

GPL = """
Run a command reporting statistics and possibly limiting usage of resources.
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

VERSION = "2.16"

import argparse
import psutil
import os
import re
import signal
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
    parser.add_argument('-a', '--affinity', metavar='<integers>', type=str, help='set cpu affinity of the command to <integers> (comma-separated list)')
    parser.add_argument('-A', '--pyrunlim-affinity', metavar='<integers>', type=str, help='set cpu affinity of pyrunlim to <integers> (comma-separated list)')
    parser.add_argument('-n', '--nice', metavar='<integer>', type=int, help='set nice to <integer> (default 20)')
    parser.add_argument('-l', '--log', metavar='<filename>', type=str, help='save log to <filename> (default STDERR)')
    parser.add_argument('-o', '--output', metavar='<output>', type=str, choices=['text', 'xml'], default='text', help='output format (text or xml; default is text)')
    parser.add_argument('-R', '--redirect', metavar='<filename>', type=str, help='redirect output (and error) of the command (default is STDOUT)')
    parser.add_argument('-O', '--redirect-output', metavar='<filename>', type=str, help='redirect output of the command (incompatible with -R,--redirect)')
    parser.add_argument('-E', '--redirect-error', metavar='<filename>', type=str, help='redirect error of the command (incompatible with -R,--redirect)')
    parser.add_argument('--no-timestamp', action='store_true', help='do not timestamp output and error of the command')
    parser.add_argument('--regex', metavar='<regex>', type=str, action='append', help='extract data from output and error of the command according to the "named groups" in <regex> (this option can be used several times). For example, --regex "real\\s(?P<minutes>\\d+)m(?P<seconds>\\d+.\\d+)" extracts minutes and seconds from the output of time in bash')
    parser.add_argument('--no-last-sample', action='store_true', help='do not print <last-sample> element when wrapping streams')
    parser.add_argument('--no-print-line', action='store_true', help='do not print <line> element when wrapping streams')
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
    if args.pyrunlim_affinity != None:
        process.setPyrunlimAffinity([int(a) for a in args.pyrunlim_affinity.split(",")])
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
    if args.no_last_sample:
        process.printLastSample = False
    if args.no_print_line:
        process.printLine = False
    if args.regex:
        for regex in args.regex:
            process.regexes.append(re.compile(regex))
    process.args.append(args.command)
    for arg in args.args:
        arg = arg.replace('"', '\\"')
        if ' ' in arg:
            arg = '"%s"' % arg
        process.args.append(arg)
    

class OutputBuilder:
    def __init__(self, process):
        self.process = process
        self.lock = threading.Lock()
        
    def report(self):
        self.lock.acquire()
        self._report()
        self.lock.release()
    
    def reportOutputStream(self, real, line, resources):
        self.lock.acquire()
        
        if self.process.timestamp:
            print("[o%10.3f] %s" % (real, line), file=self.process.stdoutFile)
        else:
            print(line, file=self.process.stdoutFile)
        self.process.stdoutFile.flush()
        
        self._reportOutputStreamBegin(real, line, resources)
        for regex in self.process.regexes:
            match = regex.match(line)
            if match:
                self._reportExtract(regex.pattern, match.groupdict())
        self._reportOutputStreamEnd()
                
        self.lock.release()
    
    def reportErrorStream(self, real, line, resources):
        self.lock.acquire()
        
        if self.process.timestamp:
            print("[e%10.3f] %s" % (real, line), file=self.process.stderrFile)
        else:
            print(line, file=self.process.stderrFile)
        self.process.stderrFile.flush()
        
        self._reportErrorStreamBegin(real, line, resources)
        for regex in self.process.regexes:
            match = regex.match(line)
            if match:
                self._reportExtract(regex.pattern, match.groupdict())
        self._reportErrorStreamEnd()
                
        self.lock.release()
    
    def begin(self):
        self.lock.acquire()
        self._begin()
        self.lock.release()

    def end(self):
        self.lock.acquire()
        self._end()
        self.lock.release()

class TextOutput(OutputBuilder):
    def __init__(self, process):
        OutputBuilder.__init__(self, process)
        
    def print(self, msg):
        print("[pyrunlim] %s" % msg, file=self.process.log)
        self.process.log.flush()
        
    def _report(self):
        self.print("sample:\t\t%10.3f\t%10.3f\t%10.3f\t%10.1f\t%10.1f\t%10.1f" % (self.process.real, self.process.user, self.process.system, self.process.max_memory, self.process.rss, self.process.swap))

    def _reportOutputStreamBegin(self, real, line, resources):
        pass

    def _reportOutputStreamEnd(self):
        pass

    def _reportErrorStreamBegin(self, real, line, resources):
        pass

    def _reportErrorStreamEnd(self):
        pass

    def _reportExtract(self, regex, dict):
        print("[regex %s] " % regex, end="", file=self.process.log)
        print("\t".join(["%s=%s" % (key, dict[key]) for key in dict.keys()]), file=self.process.log)
        self.process.log.flush()

    def _begin(self):
        self.print("version:\t\t%s" % VERSION)
        self.print("time limit:\t\t%d seconds" % self.process.timelimit)
        self.print("memory limit:\t%d MB" % self.process.memorylimit)
        self.print("real time limit:\t%d seconds" % self.process.realtimelimit)
        self.print("swap limit:\t\t%d MB" % self.process.swaplimit)
        self.print("pyrunlim cpu affin.:\t[%s]" % ", ".join([str(a) for a in psutil.Process(os.getpid()).cpu_affinity()]))
        self.print("cpu affinity:\t[%s]" % ", ".join([str(a) for a in self.process.affinity]))
        self.print("nice:\t\t%d" % self.process.nice)
        self.print("running:\t\tbash -c \"%s\"" % " ".join(self.process.args).replace('"', '\\"'))
        self.print("start:\t\t%s" % time.strftime("%c"))
        self.print("columns:\t\treal (s)\tuser (s)\tsys (s)  \tmax memory (MB)\trss (MB)   \tswap (MB)")

    def _end(self):
        self.print("end:  \t\t%s" % time.strftime("%c"))
        self.print("status:\t\t%s" % self.process.status)
        self.print("result:\t\t%s" % str(self.process.result))
        self.print("output:\t\t%s" % str(self.process.redirectOutput))
        self.print("error:\t\t%s" % str(self.process.redirectError))
        self.print("children:\t\t%d" % len(self.process.subprocesses))
        self.print("real:\t\t%.3f seconds" % self.process.real)
        self.print("time:\t\t%.3f seconds" % (self.process.system + self.process.user))
        self.print("user:\t\t%.3f seconds" % self.process.user)
        self.print("system:\t\t%.3f seconds" % self.process.system)
        self.print("memory:\t\t%.1f MB" % self.process.max_memory)
        self.print("samples:\t\t%d" % self.process.samplings)

class XmlOutput(OutputBuilder):
    def __init__(self, process):
        OutputBuilder.__init__(self, process)
        
    def print(self, msg):
        print(msg, file=self.process.log, end="")

    def println(self, msg):
        print(msg, file=self.process.log)
        self.process.log.flush()

    def cdata(self, data):
        LIMIT = 10000
        for i in range(0, len(data), LIMIT):
            if len(data) > LIMIT: self.print("<long-text>")
            self.print("<![CDATA[%s]]>" % (data[i:i+LIMIT].replace("]]>", "]]]]><![CDATA[>"),))
            if len(data) > LIMIT: self.print("</long-text>\n")
            
    def _report(self):
        self.println("<sample real='%.3f' user='%.3f' sys='%.3f' max-memory='%.1f' rss='%.1f' swap='%.1f' />" % (self.process.real, self.process.user, self.process.system, self.process.max_memory, self.process.rss, self.process.swap))
    
    def _reportOutputStreamBegin(self, real, line, resources):
        self.print("<stream type='stdout' real='%.3f'>" % real)
        if self.process.printLastSample:
            self.print("<last-sample real='%.3f' user='%.3f' sys='%.3f' max-memory='%.1f' rss='%.1f' swap='%.1f' />" % resources)
        if self.process.printLine:
            self.print("<line>")
            self.cdata(line)
            self.print("</line>")

    def _reportOutputStreamEnd(self):
        self.println("</stream>")

    def _reportErrorStreamBegin(self, real, line, resources):
        self.print("<stream type='stderr' real='%.3f'>" % real)
        if self.process.printLastSample:
            self.print("<last-sample real='%.3f' user='%.3f' sys='%.3f' max-memory='%.1f' rss='%.1f' swap='%.1f' />" % resources)
        if self.process.printLine:
            self.print("<line>")
            self.cdata(line)
            self.print("</line>")
        
    def _reportErrorStreamEnd(self):
        self.println("</stream>")

    def _reportExtract(self, regex, dict):
        self.print("<match>")
        self.print("<regex>")
        self.cdata(regex)
        self.print("</regex>")
        for key in dict.keys():
            self.print("<group name='%s'>" % (key,))
            if dict[key].isdecimal(): self.print(dict[key])
            else: self.cdata(dict[key])
            self.print("</group>")
        self.print("</match>")

    def _begin(self):
        self.print("<pyrunlim version='%s'" % VERSION)
        self.print(" time-limit='%d'" % self.process.timelimit)
        self.print(" memory-limit='%d'" % self.process.memorylimit)
        self.print(" real-time-limit='%d'" % self.process.realtimelimit)
        self.print(" swap-limit='%d'" % self.process.swaplimit)
        self.print(" cpu-affinity='%s'" % ", ".join([str(a) for a in self.process.affinity]))
        self.print(" pyrunlim-cpu-affinity='%s'" % ", ".join([str(a) for a in psutil.Process(os.getpid()).cpu_affinity()]))
        self.print(" nice='%d'" % self.process.nice)
        self.print(" running='bash -c \"%s\"'" % " ".join(self.process.args).replace("'", "&apos;").replace('"', '\\"'))
        self.print(" start='%s'" % time.strftime("%c"))
        self.println(">")

    def _end(self):
        self.print("<stats")
        self.print(" end='%s'" % time.strftime("%c"))
        self.print(" status='%s'" % self.process.status)
        self.print(" result='%s'" % str(self.process.result))
        self.print(" output='%s'" % str(self.process.redirectOutput))
        self.print(" error='%s'" % str(self.process.redirectError))
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
        
        self.rss = memory_info.rss
        self.swap = 0
        for m in memory_maps:
            self.swap = self.swap + m.swap

class Process:
    def __init__(self):
        self.output = TextOutput(self)
        
        self.args = []
        self.realtimelimit = 10**100
        self.timelimit = 10**100
        self.memorylimit = 10**100
        self.swaplimit = 10**100
        self.log = sys.stderr
        self.redirectOutput = "/dev/stdout"
        self.redirectError = "/dev/stdout"
        self.stdoutFile = sys.stdout
        self.stderrFile = sys.stdout
        self.timestamp = True
        self.printLastSample = True
        self.printLine = True
        self.regexes = []
        
        self.affinity = psutil.Process(os.getpid()).cpu_affinity()
        self.nice = 20
        
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
    
    def setPyrunlimAffinity(self, value):
        psutil.Process(os.getpid()).cpu_affinity(value)
    
    def _readOutputStream(self):
        while True:
            line = self.process.stdout.readline().decode()
            if not line:
                break
            real = time.time() - self.begin
            self.output.reportOutputStream(real, line if line[-1] != '\n' else line[:-1], (self.real, self.user, self.system, self.max_memory, self.rss, self.swap))

    def _readErrorStream(self):
        while True:
            line = self.process.stderr.readline().decode()
            if not line:
                break
            real = time.time() - self.begin
            self.output.reportErrorStream(real, line if line[-1] != '\n' else line[:-1], (self.real, self.user, self.system, self.max_memory, self.rss, self.swap))

    def run(self):
        self.output.begin()
        self.begin = time.time()
        
        if self.redirectOutput != "/dev/stdout":
            if self.redirectOutput == "/dev/stderr":
                self.stdoutFile == sys.stderr
            else:
                self.stdoutFile = open(self.redirectOutput, "w")
        if self.redirectError != "/dev/stdout":
            if self.redirectOutput == "/dev/stderr":
                self.stderrFile = sys.stderr
            elif self.redirectError != self.redirectOutput:
                self.stderrFile = open(self.redirectError, "w")
            else:
                self.stderrFile = self.stdoutFile

        self.process = psutil.Popen(["bash", "-c", "trap '' SIGINT SIGTERM; (%s)" % (" ".join(self.args),)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.process.nice(self.nice)
        self.process.cpu_affinity(self.affinity)
        
        stdoutReader = threading.Thread(target=self._readOutputStream)
        stderrReader = threading.Thread(target=self._readErrorStream)
        stdoutReader.start()
        stderrReader.start()
        
        waiter = threading.Thread(target=self._wait)
        waiter.start()
        count = 0
        while waiter.is_alive():
            count = count + 1
            if count < 10:
                time.sleep(.1)
            elif count < 30:
                time.sleep(.2)
            elif count < 60:
                time.sleep(.5)
            else:
                time.sleep(1)
            self._sampler()
        waiter.join()

        if self.exit_code == None:
            self.status = "complete"
            self.exit_code = 0
        
        stdoutReader.join()
        stderrReader.join()
        
        self.output.end()

        if self.stdoutFile != sys.stdout and self.stdoutFile != sys.stderr:
            self.stdoutFile.close()
        if self.stderrFile != sys.stdout and self.stderrFile != sys.stderr and self.redirectError != self.redirectOutput:
            self.stderrFile.close()
        if self.log != sys.stdout and self.log != sys.stderr:
            self.log.close()
            
    def _wait(self):
        self.result = self.process.wait()
        
    def kill(self):
        try:
            subprocesses = self.process.children(recursive=True)
        except psutil.NoSuchProcess:
            subprocesses = []
        subprocesses = [p for p in subprocesses if p.cmdline != self.process.cmdline]

        for p in subprocesses:
            try:
                p.terminate()
            except psutil.NoSuchProcess:
                pass

        gone, alive = psutil.wait_procs(subprocesses, timeout=1)
        for p in alive:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass

    def _updateResourceUsage(self):
        subprocesses = [self.process]
        try:
            subprocesses.extend(self.process.children(recursive=True))
        except psutil.NoSuchProcess:
            pass
        
        rss = 0
        swap = 0
        for p in subprocesses:
            if p.pid not in self.subprocesses:
                self.subprocesses[p.pid] = Subprocess()
                    
            try:
                self.subprocesses[p.pid].update(p.cpu_times(), p.memory_info(), p.memory_maps())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            rss = rss + self.subprocesses[p.pid].rss
            swap = swap + self.subprocesses[p.pid].swap

        self.rss = rss / 1024 / 1024
        self.swap = swap / 1024 / 1024

        if self.rss + self.swap > self.max_memory:
            self.max_memory = self.rss + self.swap

        self.real = time.time() - self.begin
        self.user = 0
        self.system = 0
        for p in self.subprocesses:
            self.user = self.user + self.subprocesses[p].user
            self.system = self.system + self.subprocesses[p].system

    def _sampler(self):
        self._updateResourceUsage()
        
        self.samplings = self.samplings + 1
        if int(self.real / self.reportFrequency) > self.numberOfReports:
            self.numberOfReports = self.numberOfReports + 1
            self.output.report()
        
        self._checkLimit()
    
    def _checkLimit(self):
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
            
if __name__ == "__main__":
    process = Process()
    parseArguments(process)
    
    def signal_handler(signal, frame):
        process.kill()
    signal.signal(signal.SIGINT, signal_handler)
    
    process.run()
    
    sys.exit(process.exit_code)
