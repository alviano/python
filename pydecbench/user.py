def userFunction(pydecbench):
    pydecbench.createGroup("Stable marriage", "ls $DIRNAME/../pyrunner/Example/StableMarriage/*.asp")
    pydecbench.verbatim("""
        solver(dlv, "dlv -n=1").
        limit(cpu, 10).
        run(dlv, "Stable marriage").
        limit(cpu, 30, dlv).
        limit(cpu, 20, "Stable marriage").
        limit(cpu, 40, dlv, "Stable marriage").
        
        parameter(dlv, "Stable marriage", "$DIRNAME/../pyrunner/Example/StableMarriage/encoding.lp").
        parameter(group(G),F) :-data(G,filename,F).
    """)

