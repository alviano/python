The following tools are required:

- python 3: https://www.python.org/downloads/

- gringo 3: http://sourceforge.net/projects/potassco/files/gringo/3.0.5/

- clasp 3: http://sourceforge.net/projects/potassco/files/clasp/3.1.1/


To compute all S-stable models of ADF example3.adf, use the following command-line:

<pre>
$ s-stable-models.fy example3.asp | clasp 0
</pre>

If everything is OK, you should see the following output:

<pre>
clasp version 3.1.1
Reading from stdin
Solving...
Answer: 1
true(p)
Answer: 2
true(a)
SATISFIABLE

Models       : 2     
Calls        : 1
Time         : 0.000s (Solving: 0.00s 1st Model: 0.00s Unsat: 0.00s)
CPU Time     : 0.000s
</pre>

