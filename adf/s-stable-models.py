#!/usr/bin/env python3

GPL = """
Instantiate ASP programs in order to compute G-stable models by means of ordinary ASP solvers.
Copyright (C) 2015  Mario Alviano (mario@alviano.net)

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

VERSION = "0.1"

import argparse
import subprocess
import sys
import tempfile

def parseArguments():
    global VERSION
    global GPL
    parser = argparse.ArgumentParser(description=GPL.split("\n")[1], epilog="Copyright (C) 2015  Mario Alviano (mario@alviano.net)")
    parser.add_argument('--help-syntax', action='store_true', help='print syntax description and exit') 
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + VERSION, help='print version number')
    parser.add_argument('-g', '--grounder', metavar='<grounder>', type=str, help='path to the gringo 3 (default \'gringo\')')
    parser.add_argument('args', metavar="...", nargs=argparse.REMAINDER, help="arguments for <grounder>")
    args = parser.parse_args()
    if args.help_syntax: helpSyntax()
    if not args.grounder: args.grounder = 'gringo'
    return args

def helpSyntax():
    print("""
INPUT

- s(p)
   for each statement p.

- ac(p, AC)
   for each statement p, where AC is an accepting condition, 
   i.e., a well-formed formula according to the following grammar:
       AC := verum | falsum | p | not(AC) | and(AC,AC) | or(AC,AC)
   with p being any statement.
    """)
    sys.exit()

if __name__ == "__main__":
    args = parseArguments()

    tmpFile = tempfile.NamedTemporaryFile()
    tmpFile.write("""
% determine domains
d(X,Y) :- ac(X,Y).
d(X,Y) :- d(X,neg(Y)).
d(X,Y) :- d(X,and(Y,_)).
d(X,Y) :- d(X,and(_,Y)).
d(X,Y) :- d(X,or(Y,_)).
d(X,Y) :- d(X,or(_,Y)).
d(X,Y) :- d(X,imp(Y,_)).
d(X,Y) :- d(X,imp(_,Y)).
d(X,Y) :- d(X,iff(Y,_)).
d(X,Y) :- d(X,iff(_,Y)).
dom(X,Y) :- d(X,Y), s(Y).


% determine subformulas
sf(falsum).
sf(verum).
sf(X) :- s(X).
sf(X) :- d(_,X).


% guess I
{t(X)} :- s(X).
t(verum).


% interpret subformulas
f(X) :- sf(X), not t(X).
t(neg(X)) :- sf(neg(X)), f(X).
t(and(X,Y)) :- sf(and(X,Y)), t(X), t(Y).
t(or(X,Y)) :- sf(or(X,Y)), t(X).
t(or(X,Y)) :- sf(or(X,Y)), t(Y).
t(imp(X,Y)) :- sf(imp(X,Y)), f(X).
t(imp(X,Y)) :- sf(imp(X,Y)), t(Y).
t(iff(X,Y)) :- sf(iff(X,Y)), f(X), f(Y).
t(iff(X,Y)) :- sf(iff(X,Y)), t(X), t(Y).


% I is a model
:- ac(X,Y), t(Y), f(X).


% I is a minimal model of the S-reduct
:- s(X), not eq(X).
eq(X) :- s(X), f(X).
eq(X) :- ac(X,Y), t(Y), eq(Z) : dom(X,Z).


% just show true statements
true(X) :- t(X), s(X).
#hide.
#show true(X).
    """.encode())
    tmpFile.flush()

    cmd = [args.grounder]
    cmd.extend(args.args)
    cmd.append(tmpFile.name)
    gringo = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    [stdout, stderr] = gringo.communicate()
    tmpFile.close()
    print(stdout.decode())
    