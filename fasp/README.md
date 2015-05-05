fasp2smt
========

Fuzzy answer set programming solver based on satisfiability modulo theories.

Requirements:

- gringo 3: http://sourceforge.net/projects/potassco/files/gringo/3.0.5/

- z3: http://z3.codeplex.com/releases

Commands gringo and z3 are used by fasp2smt. The path to these tools can be specified by using the command-line options --grounder and --solver, respectively.


Example usage:

<pre>
$ ./fasp2smt.py example.fasp
Answer 1:
	c	0.600000	(3.0/5.0)
	b	0.400000	(2.0/5.0)
	a	0.600000	(3.0/5.0)
</pre>

where example.fasp contains

<pre>
a :- #0.6.
b :- #0.4.
c :- a, ~b.
</pre>

For details on the syntax of input programs, run

<pre>
$ ./fasp2smt.py --help-syntax
</pre>
