self.setPyrunlim([
    "pyrunlim.py", 
    "--time=%d" % 600, 
    "--memory=%d" % (3 * 1024), 
    "--affinity=0",
    "--output=xml"
])

self.addCommand(Command("gringo+clasp", "gringo --shift $1 $2 | clasp"))

self.addBenchmark(Benchmark("StableMarriageASP", sharedOptions=["$DIRNAME/StableMarriage/encoding.lp"], testcases=sorted([(file,) for file in runner.executeAndSplit("ls $DIRNAME/StableMarriage/*.asp")]), validator=ExitCodeValidator([10, 20, 30])))

