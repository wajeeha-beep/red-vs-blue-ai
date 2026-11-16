# csp.py
# The DEFENDER has a limited budget and must choose which nodes to defend.
# A defended node is blocked: the attacker cannot pass through it.
#
# This is a CSP (Constraint Satisfaction Problem):
#   Variables   : every node except Internet and Database
#   Domain      : 1 = defend this node, 0 = do not defend it
#   Constraints : 1) total defense cost must stay within the budget
#                 2) the "must defend" nodes (like Admin PC) must be defended
#                 3) the attacker must NOT be able to reach the Database
#
# Solvers in this file:
#   1. backtracking         (plain)
#   2. backtracking_smart   (MRV + degree + least constraining value + forward checking)
#   3. min_conflicts        (local search)

import time
import random
from network import (build_main_network, make_random_network, START, GOAL)

# How much it costs to defend each node (main network)
MAIN_COSTS = {
    "Firewall": 6, "Mail Server": 3, "WiFi": 4, "VPN": 3, "Web Server": 3,
    "Student Portal": 4, "Lab PCs": 2, "Printer": 1, "Staff PC": 3,
    "Admin PC": 5, "App Server": 5, "File Server": 3, "Backup Server": 3,
}


# ---------------------------------------------------------------
# Part 1: setting up the problem
# ---------------------------------------------------------------

def make_main_problem(budget=20):
    """The CSP for the main 15-node network."""
    return {"graph": build_main_network(), "start": START, "goal": GOAL,
            "costs": MAIN_COSTS, "budget": budget, "must": ["Admin PC"]}


def make_random_problem(size, seed=1):
    """The CSP for a random network (used for scaling tests).
    Budget = cost of defending every first step from the start,
    so a solution always exists."""
    graph, start, goal = make_random_network(size, seed)
    graph[start].pop(goal, None)          # no direct edge from start to goal
    random.seed(seed + 100)
    costs = {}
    for node in graph:
        if node != start and node != goal:
            costs[node] = random.randint(1, 5)
    budget = 0
    for node in graph[start]:
        budget = budget + costs[node]
    return {"graph": graph, "start": start, "goal": goal,
            "costs": costs, "budget": budget, "must": []}


def get_variables(p):
    """All nodes that can be defended."""
    return [n for n in p["graph"] if n != p["start"] and n != p["goal"]]


# ---------------------------------------------------------------
# Part 2: helper functions (used by all solvers)
# ---------------------------------------------------------------

def reach(graph, start, open_nodes):
    """Which nodes can the attacker reach from start, walking only through open_nodes?"""
    seen = {start}
    queue = [start]
    while len(queue) > 0:
        current = queue.pop(0)
        for nxt in graph[current]:
            if nxt not in seen and nxt in open_nodes:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def plan_cost(p, defended):
    """Total cost of a defense plan (a set of defended nodes)."""
    total = 0
    for node in defended:
        total = total + p["costs"][node]
    return total


def is_valid_plan(p, defended):
    """True if the plan satisfies ALL constraints."""
    if plan_cost(p, defended) > p["budget"]:
        return False
    for node in p["must"]:
        if node not in defended:
            return False
    open_nodes = set(p["graph"]) - set(defended)
    return p["goal"] not in reach(p["graph"], p["start"], open_nodes)


def exposed_nodes(p, defended):
    """Nodes that sit on some open attack path (start -> ... -> goal).
    If this is empty, the attacker is fully blocked."""
    graph = p["graph"]
    open_nodes = set(graph) - set(defended)
    forward = reach(graph, p["start"], open_nodes)

    # build the reversed graph to walk backwards from the goal
    reverse = {}
    for a in graph:
        reverse[a] = {}
    for a in graph:
        for b in graph[a]:
            reverse[b][a] = 1
    backward = reach(reverse, p["goal"], open_nodes)

    both = forward & backward
    both.discard(p["start"])
    both.discard(p["goal"])
    return both


def result(p, name, defended, tries, backtracks, start_time, gave_up=False):
    """Pack the answer into a dictionary."""
    ms = (time.perf_counter() - start_time) * 1000
    solved = defended is not None and is_valid_plan(p, defended)
    if defended is None:
        cost = None
        plan = None
    else:
        cost = plan_cost(p, defended)
        plan = sorted(defended)
    return {"name": name, "solved": solved, "defended": plan, "cost": cost,
            "tries": tries, "backtracks": backtracks,
            "time_ms": round(ms, 3), "gave_up": gave_up}


# ---------------------------------------------------------------
# Part 3: plain backtracking
# ---------------------------------------------------------------

def partial_ok(p, assignment):
    """Check a half-finished plan. Nodes not decided yet are counted as defended
    (best case). If the attacker can still get through, this plan is already bad."""
    open_nodes = {p["goal"]}
    for node in assignment:
        if assignment[node] == 0:
            open_nodes.add(node)
    return p["goal"] not in reach(p["graph"], p["start"], open_nodes)


def backtracking(p, max_tries=200000):
    """Plain backtracking: take nodes in a fixed order, try 0 then 1, undo if stuck."""
    t = time.perf_counter()
    variables = get_variables(p)
    count = {"tries": 0, "backtracks": 0}

    def solve(index, assignment, spent):
        if index == len(variables):
            return dict(assignment)
        var = variables[index]
        values = [0, 1]
        if var in p["must"]:
            values = [1]
        for value in values:
            if count["tries"] >= max_tries:
                return None
            count["tries"] = count["tries"] + 1
            new_spent = spent
            if value == 1:
                new_spent = spent + p["costs"][var]
            if new_spent > p["budget"]:
                continue                      # too expensive
            assignment[var] = value
            if partial_ok(p, assignment):
                answer = solve(index + 1, assignment, new_spent)
                if answer is not None:
                    return answer
            del assignment[var]               # undo (backtrack)
            count["backtracks"] = count["backtracks"] + 1
        return None

    answer = solve(0, {}, 0)
    gave_up = count["tries"] >= max_tries and answer is None
    defended = None
    if answer is not None:
        defended = set()
        for node in answer:
            if answer[node] == 1:
                defended.add(node)
    return result(p, "Backtracking", defended, count["tries"],
                  count["backtracks"], t, gave_up)


# ---------------------------------------------------------------
# Part 4: smart backtracking (MRV + degree + LCV + forward checking)
# ---------------------------------------------------------------

def forward_check(p, assignment, domains, spent):
    """Look ahead. Remove values that can no longer work from the domains
    of the nodes we have not decided yet. Return None if some domain becomes empty."""
    graph = p["graph"]
    new = {}
    for v in domains:
        new[v] = list(domains[v])
    left = p["budget"] - spent

    # Rule 1: if we cannot afford to defend a node, remove the value 1
    for v in new:
        if v not in assignment and p["costs"][v] > left and 1 in new[v]:
            new[v].remove(1)

    # Nodes that are surely open (assigned 0, or only value 0 is left)
    sure_open = {p["goal"]}
    for v in new:
        if (v in assignment and assignment[v] == 0) or \
           (v not in assignment and new[v] == [0]):
            sure_open.add(v)
    if p["goal"] in reach(graph, p["start"], sure_open):
        return None                      # an open path already exists

    # Rule 2: if leaving a node open lets the attacker through, it must be defended
    for v in new:
        if v not in assignment and 0 in new[v]:
            test_open = set(sure_open)
            test_open.add(v)
            if p["goal"] in reach(graph, p["start"], test_open):
                new[v].remove(0)

    for v in new:
        if v not in assignment and len(new[v]) == 0:
            return None
    return new


def pick_variable(p, unassigned, domains):
    """MRV: choose the node with the fewest values left.
    Tie-break with the degree heuristic: choose the node with the most connections."""
    best = None
    best_key = None
    for v in unassigned:
        degree = len(p["graph"][v])
        for a in p["graph"]:
            if v in p["graph"][a]:
                degree = degree + 1
        key = (len(domains[v]), -degree)
        if best_key is None or key < best_key:
            best_key = key
            best = v
    return best


def backtracking_smart(p, max_tries=200000):
    """Backtracking with MRV, degree heuristic, least constraining value and forward checking."""
    t = time.perf_counter()
    variables = get_variables(p)
    count = {"tries": 0, "backtracks": 0}

    domains = {}
    for v in variables:
        domains[v] = [0, 1]
        if v in p["must"]:
            domains[v] = [1]

    def solve(assignment, domains, spent):
        unassigned = [v for v in variables if v not in assignment]
        if len(unassigned) == 0:
            return dict(assignment)
        var = pick_variable(p, unassigned, domains)

        # Least constraining value: try first the value that leaves the most options
        options = []
        for value in domains[var]:
            assignment[var] = value
            new_spent = spent
            if value == 1:
                new_spent = spent + p["costs"][var]
            fc = None
            if new_spent <= p["budget"]:
                fc = forward_check(p, assignment, domains, new_spent)
            del assignment[var]
            if fc is not None:
                size = 0
                for v in fc:
                    if v not in assignment and v != var:
                        size = size + len(fc[v])
                options.append((size, value, new_spent, fc))
        options.sort(key=lambda o: -o[0])

        for size, value, new_spent, fc in options:
            if count["tries"] >= max_tries:
                return None
            count["tries"] = count["tries"] + 1
            assignment[var] = value
            answer = solve(assignment, fc, new_spent)
            if answer is not None:
                return answer
            del assignment[var]
            count["backtracks"] = count["backtracks"] + 1
        return None

    start_domains = forward_check(p, {}, domains, 0)
    answer = None
    if start_domains is not None:
        answer = solve({}, start_domains, 0)
    gave_up = count["tries"] >= max_tries and answer is None
    defended = None
    if answer is not None:
        defended = set()
        for node in answer:
            if answer[node] == 1:
                defended.add(node)
    return result(p, "Backtracking + MRV + FC", defended, count["tries"],
                  count["backtracks"], t, gave_up)


# ---------------------------------------------------------------
# Part 5: Min-Conflicts (local search)
# ---------------------------------------------------------------

def count_conflicts(p, defended):
    """How bad is this plan? 0 means no conflicts (a valid plan)."""
    score = len(exposed_nodes(p, defended))        # nodes still on an attack path
    over = plan_cost(p, defended) - p["budget"]
    if over > 0:
        score = score + over                       # over budget
    for node in p["must"]:
        if node not in defended:
            score = score + 1                      # a must-defend node is missing
    return score


def min_conflicts(p, max_steps=3000, seed=1):
    """Start with a random plan, then keep fixing one conflicted node at a time."""
    t = time.perf_counter()
    random.seed(seed)
    variables = get_variables(p)

    defended = set()
    for v in variables:
        if random.random() < 0.5 or v in p["must"]:
            defended.add(v)

    steps = 0
    while steps < max_steps:
        current = count_conflicts(p, defended)
        if current == 0:
            break
        steps = steps + 1

        # choose a node that is part of the conflict
        if plan_cost(p, defended) > p["budget"]:
            candidates = [v for v in defended if v not in p["must"]]
        else:
            candidates = list(exposed_nodes(p, defended))
        if len(candidates) == 0:
            candidates = [v for v in variables if v not in p["must"]]
        v = random.choice(candidates)

        # flip it only if conflicts go down (sometimes flip anyway, to escape a dead end)
        flipped = set(defended)
        if v in flipped:
            flipped.remove(v)
        else:
            flipped.add(v)
        after = count_conflicts(p, flipped)
        if after < current or random.random() < 0.1:
            defended = flipped

    if count_conflicts(p, defended) == 0:
        return result(p, "Min-Conflicts", defended, steps, 0, t)
    return result(p, "Min-Conflicts", None, steps, 0, t, gave_up=True)


# Quick test: run  python csp.py
if __name__ == "__main__":
    p = make_main_problem(budget=20)
    print("Main network, budget =", p["budget"])
    for solver in [backtracking, backtracking_smart, min_conflicts]:
        r = solver(p)
        print("-" * 60)
        print(r["name"])
        print("  Solved   :", r["solved"])
        print("  Defended :", r["defended"])
        print("  Cost     :", r["cost"])
        print("  Tries    :", r["tries"], "| Backtracks:", r["backtracks"])
        print("  Time(ms) :", r["time_ms"])