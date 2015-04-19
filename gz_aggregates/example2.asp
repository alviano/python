xor(g1).
output(g1,out).
input(g1,in(X)) :- X = 1..3.

{value(in(X),1) : input(_,in(X))}.

value(X,0) :- input(_,X), not value(X,1).
value(X,0) :- output(_,X), not value(X,1).

value(O,1) :- xor(G), output(G,O), gz_odd(o1).
:- value(out,0).

gz_set(o1,value(I,1)) :- input(G,I), value(I,1).

#hide xor/1.
#hide output/2.
#hide input/2.
