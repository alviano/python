def userFunction(pydecbench):
    pydecbench.createGroup("Stable marriage", "ls $DIRNAME/../pyrunner/Example/StableMarriage/*.asp")
    pydecbench.verbatim("""
        solver(dlv, "dlv -n=1").
        solver(clasp, pipe("gringo", "clasp")).
        limit(cpu, 10).
        run(dlv, "Stable marriage").
        run(clasp, "Stable marriage").
        limit(cpu, 30, dlv).
        limit(cpu, 20, "Stable marriage").
        limit(cpu, 40, dlv, "Stable marriage").
        limit(cpu, 40, clasp).
        limit(memory, 1024).
        
        parameter(dlv, "Stable marriage", "$DIRNAME/../pyrunner/Example/StableMarriage/encoding.lp").
        parameter(group(G),F) :- data(G,filename,F).
        
        requires(dlv, clasp).
        
        solver(yes, "yes").
        limit(cpu, 1, yes, "Stable marriage").
        run(yes, "Stable marriage").
        
        validator(group(G),limit).
    """)

