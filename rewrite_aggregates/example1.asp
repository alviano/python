{ true(exists,Label,Coeff) } :- var(exists,Label,Coeff).
true(forall,Label,Coeff) :- unequal, var(forall,Label,Coeff).
unequal :- int(Value), f_sum(s, "!=", Value).
f_set(s, Coeff, true(exists,Label,Coeff) ) :- true(exists,Label,Coeff).
f_set(s, Coeff, true(forall,Label,Coeff) ) :- true(forall,Label,Coeff).
:- not unequal.

var(exists,x1,1).
var(exists,x2,2).
var(forall,y1,2).
var(forall,y2,3).
int(5).

