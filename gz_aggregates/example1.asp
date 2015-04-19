{p(X) : X = 1..2}.
p(3) | p(4) :- gz_sum(s1,">=",3).

gz_set(s1,X,p(X)) :- p(X), X <= 3.
