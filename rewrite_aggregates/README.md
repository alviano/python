The following tools are required:

- python 3: https://www.python.org/downloads/

- gringo 3: http://sourceforge.net/projects/potassco/files/gringo/3.0.5/

- clasp 3: http://sourceforge.net/projects/potassco/files/clasp/3.1.1/


To compute all F-stable models of program example1.asp, use the following command-line:

<pre>
$ ./f-aggregates.py example1.asp | clasp 0
</pre>

If everything is OK, you should see the following output:

<pre>
clasp version 3.1.1
Reading from stdin
Solving...
Answer: 1
var(exists,x1,1) var(exists,x2,2) var(forall,y1,2) var(forall,y2,3) int(5) unequal true(forall,y2,3) true(forall,y1,2) true(exists,x1,1)
SATISFIABLE

Models       : 1     
Calls        : 1
Time         : 0.001s (Solving: 0.00s 1st Model: 0.00s Unsat: 0.00s)
CPU Time     : 0.000s
</pre>

If command 'gringo' is not in the PATH, use the -g flag:

<pre>
$ ./f-aggregates.py -g /path/to/gringo example1.asp
</pre>

Flags for gringo can also be specified (at the end of the command line).

