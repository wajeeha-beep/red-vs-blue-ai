# network.py
# This file builds the computer network that the attacker will try to break into.
# The network is stored as a dictionary (a graph):
#   graph["Internet"] = {"Firewall": 5, "Mail Server": 3}
# means: from Internet you can go to Firewall (difficulty 5) or Mail Server (difficulty 3).
# A bigger number means the step is harder for the attacker.

import random

START = "Internet"      # where the attacker begins
GOAL = "Database"       # what the attacker wants to reach


def build_main_network():
    """Create the main university network (15 nodes)."""
    graph = {
        "Internet":       {"Firewall": 5, "Mail Server": 3, "WiFi": 4, "VPN": 6},
        "Firewall":       {"Web Server": 3, "Student Portal": 4},
        "Mail Server":    {"Staff PC": 2, "Admin PC": 6},
        "WiFi":           {"Lab PCs": 2, "Printer": 1},
        "VPN":            {"Staff PC": 4, "App Server": 7},
        "Web Server":     {"App Server": 3},
        "Student Portal": {"App Server": 4, "Database": 9},
        "Lab PCs":        {"File Server": 3},
        "Printer":        {"File Server": 4},
        "Staff PC":       {"File Server": 3, "Admin PC": 3},
        "Admin PC":       {"Database": 4, "Backup Server": 3},
        "App Server":     {"Database": 5},
        "File Server":    {"Backup Server": 2},
        "Backup Server":  {"Database": 6},
        "Database":       {},
    }
    return graph


def make_random_network(size, seed=1):
    """Create a random network with 'size' nodes (used for scaling tests).
    The same seed always gives the same network."""
    random.seed(seed)
    names = ["N" + str(i) for i in range(size)]
    graph = {}
    for name in names:
        graph[name] = {}

    # First make one simple chain so a path always exists: N0 -> N1 -> N2 ...
    for i in range(size - 1):
        graph[names[i]][names[i + 1]] = random.randint(1, 9)

    # Then add some extra random edges
    for i in range(size * 2):
        a = random.choice(names)
        b = random.choice(names)
        if a != b and b not in graph[a]:
            graph[a][b] = random.randint(1, 9)

    return graph, names[0], names[-1]


def get_neighbors(graph, node):
    """Return the list of nodes we can reach from 'node'."""
    return list(graph[node].keys())


def get_cost(graph, a, b):
    """Return the difficulty of the step from a to b."""
    return graph[a][b]


def make_heuristic(graph, goal):
    """Make a guess of how far each node is from the goal (used by A* and Best-First).
    Guess = (minimum number of steps to goal) x (cheapest edge in the graph).
    This guess is never bigger than the real cost, so A* stays correct."""
    # Find the cheapest edge in the whole graph
    cheapest = 999
    for a in graph:
        for b in graph[a]:
            if graph[a][b] < cheapest:
                cheapest = graph[a][b]

    # Count steps to the goal by walking backwards from the goal (BFS on reversed edges)
    steps = {goal: 0}
    queue = [goal]
    while len(queue) > 0:
        current = queue.pop(0)
        for a in graph:
            if current in graph[a] and a not in steps:
                steps[a] = steps[current] + 1
                queue.append(a)

    heuristic = {}
    for node in graph:
        if node in steps:
            heuristic[node] = steps[node] * cheapest
        else:
            heuristic[node] = 0
    return heuristic


# Quick test: run  python network.py  to check everything works
if __name__ == "__main__":
    graph = build_main_network()
    print("Nodes:", len(graph))
    print("Edges:", sum(len(graph[n]) for n in graph))
    print("From Internet we can go to:", get_neighbors(graph, "Internet"))
    print("Cost Mail Server -> Admin PC:", get_cost(graph, "Mail Server", "Admin PC"))

    h = make_heuristic(graph, GOAL)
    print("Heuristic for Internet:", h["Internet"])

    big, start, goal = make_random_network(20, seed=1)
    print("Random network:", len(big), "nodes, start =", start, ", goal =", goal)