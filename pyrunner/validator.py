from dirname import *
import fileinput
from lxml import etree
import re
import subprocess
import sys
import time
import os

class AllValidator:
    def valid(self, command, benchmark, testcase, xml):
        return True
        
    def setDirname(self, dirname):
        pass

class ExitCodeValidator:
    def __init__(self, validExitCodes=[0]):
        self.validExitCodes = validExitCodes
        
    def valid(self, command, benchmark, testcase, xml):
        return xml.xpath("//stats/@status = 'complete'") and int(xml.xpath("//stats/@result")[0]) in self.validExitCodes

    def setDirname(self, dirname):
        pass

class AspCompetitionValidator:
    def __init__(self, path):
        self.path = path
        
    def valid(self, command, benchmark, testcase, xml):
        output_file = xml.xpath("//stats/@output")[0]
        try:
            lines = subprocess.check_output(["bash", "-c", "(cat %s; tail --lines=1 %s) | %s" % (testcase[0], output_file, self.path)])
            return lines.decode().strip() == "OK"
        except:
            return False

    def setDirname(self, dirname):
        self.path = self.path.replace("$DIRNAME", dirname)
