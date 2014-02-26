#!/usr/bin/env python3.3

import argparse
import psutil
import os
import sys
import time
import threading

VERSION = "1.0"

def parseArguments(process):
    parser = argparse.ArgumentParser(description='Run a command reporting statistics and possibly limiting usage of resources.')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s %(VERSION)s', help='print version number')
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
        process.redirect = args.redirect
    if args.redirect_output != None:
        process.redirectOutput = args.redirect_output
    if args.redirect_error != None:
        process.redirectError = args.redirect_error
    process.args.append(args.command)
    process.args.extend(args.args)
    

class TextOutput:
    def __init__(self, process):
        self.process = process
        
    def report(self):
        print("[pyrunlim] sample:\t\t%10.3f\t%10.3f\t%10.3f\t%10.1f\t%10.1f\t%10.1f" % (self.process.real, self.process.user, self.process.system, self.process.max_memory, self.process.rss, self.process.swap), file=self.process.log)
    
    def begin(self):
        print("[pyrunlim] version:\t\t%s" % VERSION, file=self.process.log)
        print("[pyrunlim] time limit:\t\t%d seconds" % self.process.timelimit, file=self.process.log)
        print("[pyrunlim] memory limit:\t%d MB" % self.process.memorylimit, file=self.process.log)
        print("[pyrunlim] real time limit:\t%d seconds" % self.process.realtimelimit, file=self.process.log)
        print("[pyrunlim] swap limit:\t\t%d MB" % self.process.swaplimit, file=self.process.log)
        print("[pyrunlim] cpu affinity:\t[%s]" % ", ".join([str(a) for a in self.process.affinity]), file=self.process.log)
        print("[pyrunlim] nice:\t\t%d" % self.process.nice, file=self.process.log)
        print("[pyrunlim] running:\t\tbash -c \"%s\"" % " ".join(self.process.args), file=self.process.log)
        print("[pyrunlim] start:\t\t%s" % time.strftime("%c"), file=self.process.log)
        print("[pyrunlim] columns:\t\treal (s)\tuser (s)\tsys (s)  \tmax memory (MB)\trss (MB)   \tswap (MB)", file=self.process.log)

    def end(self):
        print("[pyrunlim] end:  \t\t%s" % time.strftime("%c"), file=self.process.log)
        print("[pyrunlim] status:\t\t%s" % self.process.status, file=self.process.log)
        print("[pyrunlim] result:\t\t%s" % str(self.process.result), file=self.process.log)
        if self.process.redirectOutput or self.process.redirectError:
            print("[pyrunlim] output:\t\t%s" % str(self.process.redirectOutput), file=self.process.log)
            print("[pyrunlim] error:\t\t%s" % str(self.process.redirectError), file=self.process.log)
        else:
            print("[pyrunlim] output+error:\t%s" % str(self.process.redirect), file=self.process.log)
        print("[pyrunlim] children:\t\t%d" % len(self.process.subprocesses), file=self.process.log)
        print("[pyrunlim] real:\t\t%.3f seconds" % self.process.real, file=self.process.log)
        print("[pyrunlim] time:\t\t%.3f seconds" % (self.process.system + self.process.user), file=self.process.log)
        print("[pyrunlim] user:\t\t%.3f seconds" % self.process.user, file=self.process.log)
        print("[pyrunlim] system:\t\t%.3f seconds" % self.process.system, file=self.process.log)
        print("[pyrunlim] memory:\t\t%.1f MB" % self.process.max_memory, file=self.process.log)
        print("[pyrunlim] samples:\t\t%d" % self.process.samplings, file=self.process.log)

class XmlOutput:
    def __init__(self, process):
        self.process = process
        
    def report(self):
        print("<sample real='%.3f' user='%.3f' sys='%.3f' max-memory='%.1f' rss='%.1f' swap='%.1f' />" % (self.process.real, self.process.user, self.process.system, self.process.max_memory, self.process.rss, self.process.swap), file=self.process.log)
    
    def begin(self):
        print("<pyrunlim version='%s'" % VERSION, file=self.process.log, end="")
        print(" time-limit='%d'" % self.process.timelimit, file=self.process.log, end="")
        print(" memory-limit='%d'" % self.process.memorylimit, file=self.process.log, end="")
        print(" real-time-limit='%d'" % self.process.realtimelimit, file=self.process.log, end="")
        print(" swap-limit='%d'" % self.process.swaplimit, file=self.process.log, end="")
        print(" cpu-affinity='%s'" % ", ".join([str(a) for a in self.process.affinity]), file=self.process.log, end="")
        print(" nice='%d'" % self.process.nice, file=self.process.log, end="")
        print(" running='bash -c \"%s\"'" % " ".join(self.process.args).replace("'", "&apos;"), file=self.process.log, end="")
        print(" start='%s'" % time.strftime("%c"), file=self.process.log, end="")
        print(">", file=self.process.log)

    def end(self):
        print("<stats ", file=self.process.log, end="")
        print(" end='%s'" % time.strftime("%c"), file=self.process.log, end="")
        print(" status='%s'" % self.process.status, file=self.process.log, end="")
        print(" result='%s'" % str(self.process.result), file=self.process.log, end="")
        if self.process.redirectOutput or self.process.redirectError:
            print(" output='%s'" % str(self.process.redirectOutput), file=self.process.log, end="")
            print(" error='%s'" % str(self.process.redirectError), file=self.process.log, end="")
        else:
            print(" output-and-error='%s'" % str(self.process.redirect), file=self.process.log, end="")
        print(" children='%d'" % len(self.process.subprocesses), file=self.process.log, end="")
        print(" real='%.3f'" % self.process.real, file=self.process.log, end="")
        print(" time='%.3f'" % (self.process.system + self.process.user), file=self.process.log, end="")
        print(" user='%.3f'" % self.process.user, file=self.process.log, end="")
        print(" system='%.3f'" % self.process.system, file=self.process.log, end="")
        print(" memory='%.1f'" % self.process.max_memory, file=self.process.log, end="")
        print(" samples='%d'" % self.process.samplings, file=self.process.log, end="")
        print("/>", file=self.process.log)
        print("</pyrunlim>", file=self.process.log)

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
        self.redirect = "/dev/stdout"
        self.redirectOutput = None
        self.redirectError = None
        
        self.affinity = psutil.Process(os.getpid()).get_cpu_affinity()
        self.nice = 20
        
        self.done = False
        self.samplings = 0
        self.reportFrequency = 10
        self.numberOfReports = 0
        self.status = "interrupted"
        self.result = None
        self.exit_code = -1
        
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
        if self.redirectOutput or self.redirectError:
            if not self.redirectOutput:
                self.redirectOutput = "/dev/null"
            if not self.redirectError:
                self.redirectError = "/dev/null"
            self.process = psutil.Popen(["bash", "-c", "((%s) > %s 2> %s)" % (" ".join(self.args), self.redirectOutput, self.redirectError)])
        else:
            self.process = psutil.Popen(["bash", "-c", "((%s) &> %s)" % (" ".join(self.args), self.redirect)])
        self.process.set_nice(self.nice)
        self.process.set_cpu_affinity(self.affinity)
        self.result = self.process.wait()
        self.done = True
        if self.exit_code == -1:
            self.status = "complete"
            self.exit_code = 0
        
    def kill(self):
        try:
            subprocesses = self.process.get_children(recursive=True)
        except psutil.NoSuchProcess:
            subprocesses = []
        
        for p in subprocesses:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass
            
        try:
            self.process.kill()
        except psutil.NoSuchProcess:
            pass

    def sampler(self):
        if self.done:
            return

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
            except psutil.NoSuchProcess:
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
            self.kill()
            self.status = "out of time (real)"
            self.exit_code = 1
        elif self.user + self.system > self.timelimit:
            self.kill()
            self.status = "out of time"
            self.exit_code = 2
        elif self.max_memory > self.memorylimit:
            self.kill()
            self.status = "out of memory"
            self.exit_code = 3
        elif self.swap > self.swaplimit:
            self.kill()
            self.status = "out of memory (swap)"
            self.exit_code = 4
            
    def end(self):
        self.output.end()
        if self.log != sys.stderr:
            self.log.close()
            
if __name__ == "__main__":
    process = Process()
    parseArguments(process)
    
    process.start()

    while not process.done:
        time.sleep(0.1)
        process.sampler()
        
    process.end()
    
    sys.exit(process.exit_code)
