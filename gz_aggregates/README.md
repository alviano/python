The following tools are required:

- python 3: https://www.python.org/downloads/

- gringo 3: http://sourceforge.net/projects/potassco/files/gringo/3.0.5/

- clasp 3: http://sourceforge.net/projects/potassco/files/clasp/3.1.1/

- wasp 2: https://github.com/alviano/wasp/


To compute all G-stable models of program example1.asp, use the following command-line:

<pre>
$ ./gelfondize.py example1.asp | clasp 0
</pre>

If everything is OK, you should see the following output:

<pre>
clasp version 3.1.1
Reading from stdin
Solving...
Answer: 1
p(1) p(2) p(4)
Answer: 2

Answer: 3
p(1)
Answer: 4
p(2)
SATISFIABLE

Models       : 4     
Calls        : 1
Time         : 0.001s (Solving: 0.00s 1st Model: 0.00s Unsat: 0.00s)
CPU Time     : 0.000s
</pre>

To use wasp as the back-end ASP solver, run the following:

<pre>
$ ./gelfondize.py example1.asp | wasp -n=0
WASP 2.0

{}
{p(2)}
{p(2), p(1), p(4)}
{p(1)}
</pre>

If command 'gringo' is not in the PATH, use the -g flag:

<pre>
$ ./gelfondize.py -g /path/to/gringo example1.asp
</pre>

Flags for gringo can also be specified (at the end of the command line).

