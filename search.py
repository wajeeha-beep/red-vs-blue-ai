
# search.py
# These are the search algorithms the ATTACKER uses to find a path
# from the Internet to the Database.
# Every function returns a small dictionary with:
#   name     : algorithm name
#   path     : list of nodes (or None if no path)
#   cost     : total difficulty of the path
#   expanded : how many nodes the algorithm opened (smaller = faster search)
#   time_ms  : time taken in milliseconds

import time
from network import (build_main_network, make_random_network,
                     make_heuristic, START, GOAL)


def path_cost(graph, path):
    """Add up the difficulty of every step in the path."""
    total = 0
    for i in range(len(path) - 1):
        total = total + graph[path[i]][path[i + 1]]
    return total


def make_result(name, graph, path, expanded, start_time):
    """Pack the answer into a dictionary."""
    ms = (time.perf_counter() - start_time) * 1000
    if path is None:
        cost = None
    else:
        cost = path_cost(graph, path)
    return {"name": name, "path": path, "cost": cost,
            "expanded": expanded, "time_ms": round(ms, 3)}


# 1. Breadth-First Search: explores level by level, finds the path with fewest steps.
def bfs(graph, start, goal):
    t = time.perf_counter()
    queue = [[start]]            # queue of paths
    visited = [start]
    expanded = 0
    while len(queue) > 0:
        path = queue.pop(0)      # take from the front
        node = path[-1]
        expanded = expanded + 1
        if node == goal:
            return make_result("BFS", graph, path, expanded, t)
        for nxt in graph[node]:
            if nxt not in visited:
                visited.append(nxt)
                queue.append(path + [nxt])
    return make_result("BFS", graph, None, expanded, t)


# 2. Depth-First Search: goes as deep as possible first, then backtracks.
def dfs(graph, start, goal):
    t = time.perf_counter()
    stack = [[start]]            # stack of paths
    visited = []
    expanded = 0
    while len(stack) > 0:
        path = stack.pop()       # take from the end
        node = path[-1]
        if node in visited:
            continue
        visited.append(node)
        expanded = expanded + 1
        if node == goal:
            return make_result("DFS", graph, path, expanded, t)
        # reversed so the first neighbour is tried first
        for nxt in reversed(list(graph[node])):
            if nxt not in visited:
                stack.append(path + [nxt])
    return make_result("DFS", graph, None, expanded, t)


# 3. Progressive Deepening: runs DFS with depth limit 1, then 2, then 3 ...
def depth_limited(graph, path, goal, limit, counter):
    """Helper: DFS that stops at a depth limit. counter[0] counts opened nodes."""
    node = path[-1]
    counter[0] = counter[0] + 1
    if node == goal:
        return path
    if len(path) - 1 >= limit:
        return None
    for nxt in graph[node]:
        if nxt not in path:      # do not go in circles
            found = depth_limited(graph, path + [nxt], goal, limit, counter)
            if found is not None:
                return found
    return None


def progressive_deepening(graph, start, goal):
    t = time.perf_counter()
    counter = [0]
    for limit in range(1, len(graph) + 1):
        found = depth_limited(graph, [start], goal, limit, counter)
        if found is not None:
            return make_result("Progressive Deepening", graph, found, counter[0], t)
    return make_result("Progressive Deepening", graph, None, counter[0], t)


# 4. Best-First Search: always opens the node that LOOKS closest to the goal (heuristic only).
def best_first(graph, start, goal, h):
    t = time.perf_counter()
    open_list = [(h[start], [start])]
    visited = []
    expanded = 0
    while len(open_list) > 0:
        best = open_list[0]
        for item in open_list:
            if item[0] < best[0]:
                best = item
        open_list.remove(best)
        path = best[1]
        node = path[-1]
        if node in visited:
            continue
        visited.append(node)
        expanded = expanded + 1
        if node == goal:
            return make_result("Best-First", graph, path, expanded, t)
        for nxt in graph[node]:
            if nxt not in visited:
                open_list.append((h[nxt], path + [nxt]))
    return make_result("Best-First", graph, None, expanded, t)


# 5. A* Search: picks the node with the smallest  f = cost so far + heuristic guess.
def a_star(graph, start, goal, h):
    t = time.perf_counter()
    open_list = [(h[start], 0, [start])]      # (f, cost so far, path)
    best_cost = {start: 0}
    expanded = 0
    while len(open_list) > 0:
        best = open_list[0]
        for item in open_list:
            if item[0] < best[0]:
                best = item
        open_list.remove(best)
        f, g, path = best
        node = path[-1]
        if g > best_cost[node]:
            continue                           # we already found a cheaper way here
        expanded = expanded + 1
        if node == goal:
            return make_result("A*", graph, path, expanded, t)
        for nxt in graph[node]:
            new_g = g + graph[node][nxt]
            if nxt not in best_cost or new_g < best_cost[nxt]:
                best_cost[nxt] = new_g
                open_list.append((new_g + h[nxt], new_g, path + [nxt]))
    return make_result("A*", graph, None, expanded, t)


# 6. Branch and Bound: always extends the cheapest partial path,
#    and throws away any path that is already costlier than the best full path found.
def branch_and_bound(graph, start, goal):
    t = time.perf_counter()
    open_list = [(0, [start])]                 # (cost so far, path)
    best_path = None
    best_total = 999999
    expanded = 0
    while len(open_list) > 0:
        best = open_list[0]
        for item in open_list:
            if item[0] < best[0]:
                best = item
        open_list.remove(best)
        cost, path = best
        if cost >= best_total:
            break                              # everything left is worse, stop
        node = path[-1]
        expanded = expanded + 1
        if node == goal:
            best_total = cost
            best_path = path
            continue
        for nxt in graph[node]:
            if nxt not in path:
                new_cost = cost + graph[node][nxt]
                if new_cost < best_total:      # bound: skip paths that are too costly
                    open_list.append((new_cost, path + [nxt]))
    return make_result("Branch and Bound", graph, best_path, expanded, t)


def run_all(graph, start, goal):
    """Run all 6 algorithms and return the list of results."""
    h = make_heuristic(graph, goal)
    results = []
    results.append(bfs(graph, start, goal))
    results.append(dfs(graph, start, goal))
    results.append(progressive_deepening(graph, start, goal))
    results.append(best_first(graph, start, goal, h))
    results.append(a_star(graph, start, goal, h))
    results.append(branch_and_bound(graph, start, goal))
    return results


# Quick test: run  python search.py
if __name__ == "__main__":
    graph = build_main_network()
    results = run_all(graph, START, GOAL)
    for r in results:
        print("-" * 60)
        print(r["name"])
        print("  Path    :", " -> ".join(r["path"]))
        print("  Cost    :", r["cost"])
        print("  Expanded:", r["expanded"])
        print("  Time(ms):", r["time_ms"])

    print()
    print("Test on a random network of 200 nodes:")
    big, s, g = make_random_network(200, seed=1)
    for r in run_all(big, s, g):
        print(" ", r["name"], "| cost:", r["cost"], "| expanded:", r["expanded"])