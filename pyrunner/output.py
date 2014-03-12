from dirname import *
import fileinput
from lxml import etree
import re
import subprocess
import sys
import time
import os

class TextOutput:
    def __init__(self, runner):
        self.runner = runner
    
    def print(self, msg):
        print("[%10.3f] %s" % (time.time() - self.runner.beginTime, msg), file=self.runner.log)
        self.runner.log.flush()
        
    def begin(self):
        self.print("Start")
    
    def end(self):
        self.print("All done!")
        
    def beginBenchmark(self, benchmark):
        self.print("    Processing benchmark %s" % benchmark.id)
        
    def endBenchmark(self, benchmark):
        self.print("    done")
    
    def beginTestcase(self, testcase):
        self.print("        Testing %s" % str(testcase))
        
    def endTestcase(self, testcase):
        self.print("        done")
        
    def beginCommand(self, command):
        self.print("            with %s" % command.id)
    
    def endCommand(self, command):
        self.print("            done")
        
    def report(self, xml):
        self.print("                status: %s" % xml.xpath("//stats/@status")[0])
        self.print("                time: %s" % xml.xpath("//stats/@time")[0])
        self.print("                memory: %s" % xml.xpath("//stats/@memory")[0])

    def skip(self):
        self.print("                skip")

    def onValidRun(self):
        self.print("                validator: yes")
    def onInvalidRun(self):
        self.print("                validator: no")
        
class XmlOutput:
    def __init__(self, runner):
        self.runner = runner
    
    def print(self, msg):
        print(msg, file=self.runner.log)
        self.runner.log.flush()
        
    def begin(self):
        self.print("<pyrunner>")
    
    def end(self):
        self.print("</pyrunner>")
        
    def beginBenchmark(self, benchmark):
        self.print("<benchmark id='%s'>" % benchmark.id)
        
    def endBenchmark(self, benchmark):
        self.print("</benchmark>")
    
    def beginTestcase(self, testcase):
        self.print("<testcase id=\"%s\">" % str(testcase))
        
    def endTestcase(self, testcase):
        self.print("</testcase>")
        
    def beginCommand(self, command):
        self.print("<command id='%s'>" % command.id)
    
    def endCommand(self, command):
        self.print("</command>")
        
    def report(self, xml, ):
        self.print(etree.tostring(xml).decode())
        
    def skip(self):
        self.print("<skip />")
    
    def onValidRun(self):
        self.print("<validator response='yes' />")
    def onInvalidRun(self):
        self.print("<validator response='no' />")

