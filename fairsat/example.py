gamma = []
gamma.append("!x11 | !x21)")
gamma.append("!x12 | !x22)")
gamma.append("!x13 | !x23)")

agents = []
agents.append([
    ["x11 | (x12 & x13)", 3, 5],
    ["x11 & x12", 1, 2],
])
agents.append([
    ["x21", 1, 2],
    ["x22", 2, 5],
    ["x23", -2, 5]
])
