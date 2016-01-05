gamma = []
gamma.append("!(x11 & x21)")
gamma.append("!(x12 & x22)")
gamma.append("!(x13 & x23)")

agents = []
agents.append([
    ["x11 | (x12 & x13)", 3, 2],
    ["x11 & x12", 2],
])
agents.append([
    ["x21", 2],
    ["x22", 1],
    ["x23", 2],
])
