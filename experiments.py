# experiments.py
# Runs every algorithm on the same problems and builds comparison tables.
# This is the "testing and analysis" part of the project.
# Every function returns a list of rows (dictionaries). Each row is one line of a table.
# The Streamlit app (frontend) will show these tables and draw charts from them.

import os
import copy
import pandas as pd

from network import build_main_network, make_random_network, START, GOAL
from search import run_all
from csp import (make_main_problem, make_random_problem, backtracking,
                 backtracking_smart, min_conflicts, is_valid_plan)
from local_search import hill_climbing, beam_search, genetic_algorithm
from game import play_game, alpha_beta, compare_depths

CSP_METHODS = [backtracking, backtracking_smart, min_conflicts,
               hill_climbing, beam_search, genetic_algorithm]


def average(numbers):
    """Average of a list (0 if the list is empty)."""
    if len(numbers) == 0:
        return 0
    return round(sum(numbers) / len(numbers), 2)


# ---------------------------------------------------------------
# Table 1: attacker searches on the main network
# ---------------------------------------------------------------
def search_comparison(graph=None, start=START, goal=GOAL):
    """Compare the 6 search algorithms on one network."""
    if graph is None:
        graph = build_main_network()
    results = run_all(graph, start, goal)
    best_cost = min(r["cost"] for r in results)
    rows = []
    for r in results:
        rows.append({"Algorithm": r["name"], "Path cost": r["cost"],
                     "Nodes expanded": r["expanded"], "Time (ms)": r["time_ms"],
                     "Optimal?": "Yes" if r["cost"] == best_cost else "No",
                     "Path": " -> ".join(r["path"])})
    return rows


# ---------------------------------------------------------------
# Table 2: defender methods on one problem
# ---------------------------------------------------------------
def csp_comparison(p):
    """Compare all 6 defender methods on one problem."""
    rows = []
    for method in CSP_METHODS:
        r = method(p)
        rows.append({"Method": r["name"], "Solved?": "Yes" if r["solved"] else "No",
                     "Defense cost": r["cost"], "Work (tries/steps)": r["tries"],
                     "Time (ms)": r["time_ms"],
                     "Defended nodes": ", ".join(r["defended"]) if r["defended"] else "-"})
    return rows


# ---------------------------------------------------------------
# Table 3: Minimax vs Alpha-Beta
# ---------------------------------------------------------------
def game_comparison(p, depths=(2, 3, 4, 5)):
    rows = []
    for row in compare_depths(p, list(depths)):
        rows.append({"Depth": row["depth"],
                     "Minimax positions": row["minimax_positions"],
                     "Alpha-Beta positions": row["alphabeta_positions"],
                     "Saved %": row["saved_percent"],
                     "Minimax time (ms)": row["minimax_ms"],
                     "Alpha-Beta time (ms)": row["alphabeta_ms"],
                     "Same moves?": "Yes" if row["same_moves"] else "No",
                     "Winner": row["winner"]})
    return rows


# ---------------------------------------------------------------
# Table 4: scaling test for the attacker searches
# ---------------------------------------------------------------
def scaling_search(sizes=(10, 25, 50, 100, 200), seeds=(1, 2, 3)):
    """Make bigger and bigger random networks. Average over a few random seeds."""
    rows = []
    for size in sizes:
        collected = {}
        for seed in seeds:
            graph, start, goal = make_random_network(size, seed)
            results = run_all(graph, start, goal)
            best_cost = min(r["cost"] for r in results)
            for r in results:
                if r["name"] not in collected:
                    collected[r["name"]] = {"expanded": [], "cost": [], "time": [], "optimal": 0}
                collected[r["name"]]["expanded"].append(r["expanded"])
                collected[r["name"]]["cost"].append(r["cost"])
                collected[r["name"]]["time"].append(r["time_ms"])
                if r["cost"] == best_cost:
                    collected[r["name"]]["optimal"] += 1
        for name in collected:
            c = collected[name]
            rows.append({"Nodes": size, "Algorithm": name,
                         "Avg nodes expanded": average(c["expanded"]),
                         "Avg path cost": average(c["cost"]),
                         "Avg time (ms)": average(c["time"]),
                         "Optimal runs": str(c["optimal"]) + "/" + str(len(seeds))})
    return rows


# ---------------------------------------------------------------
# Table 5: scaling test for the defender methods
# ---------------------------------------------------------------
def scaling_csp(sizes=(10, 20, 30, 40, 50), seeds=(1, 2, 3)):
    rows = []
    for size in sizes:
        collected = {}
        for seed in seeds:
            p = make_random_problem(size, seed)
            for method in CSP_METHODS:
                r = method(p)
                if r["name"] not in collected:
                    collected[r["name"]] = {"work": [], "cost": [], "time": [], "solved": 0}
                collected[r["name"]]["work"].append(r["tries"])
                collected[r["name"]]["time"].append(r["time_ms"])
                if r["solved"]:
                    collected[r["name"]]["solved"] += 1
                    collected[r["name"]]["cost"].append(r["cost"])
        for name in collected:
            c = collected[name]
            rows.append({"Nodes": size, "Method": name,
                         "Solved": str(c["solved"]) + "/" + str(len(seeds)),
                         "Avg defense cost": average(c["cost"]),
                         "Avg work (tries/steps)": average(c["work"]),
                         "Avg time (ms)": average(c["time"])})
    return rows


# ---------------------------------------------------------------
# Table 6: what if the budget changes?
# ---------------------------------------------------------------
def budget_test(budgets=(12, 17, 20, 25, 30), depth=3):
    rows = []
    for budget in budgets:
        p = make_main_problem(budget)
        r = backtracking_smart(p)
        game = play_game(p, alpha_beta, depth)
        plan_cost = "-"
        if r["solved"]:
            plan_cost = r["cost"]
        rows.append({"Budget": budget,
                     "Defense plan found?": "Yes" if r["solved"] else "No",
                     "Plan cost": plan_cost,
                     "Game winner (depth " + str(depth) + ")": game["winner"]})
    return rows


# ---------------------------------------------------------------
# Table 7: what if a NEW weakness (zero-day) appears?
# ---------------------------------------------------------------
def zero_day_test(budget=20):
    """Add a new edge Internet -> Student Portal (cost 2), like a new vulnerability.
    Then check: does the old defense still work? How hard is it to plan again?"""
    p = make_main_problem(budget)
    old_plan = backtracking_smart(p)["defended"]

    new_graph = copy.deepcopy(p["graph"])
    new_graph["Internet"]["Student Portal"] = 2
    p2 = make_main_problem(budget)
    p2["graph"] = new_graph

    still_valid = is_valid_plan(p2, set(old_plan))
    return {"old_plan": old_plan,
            "old_plan_still_valid": still_valid,
            "attacker_searches": search_comparison(new_graph),
            "defender_replanning": csp_comparison(p2)}


# ---------------------------------------------------------------
# Run everything and save as CSV files
# ---------------------------------------------------------------
def run_everything():
    p = make_main_problem(budget=20)
    tables = {
        "1_search_comparison": search_comparison(),
        "2_defender_comparison": csp_comparison(p),
        "3_minimax_vs_alphabeta": game_comparison(p),
        "4_scaling_search": scaling_search(),
        "5_scaling_defender": scaling_csp(),
        "6_budget_test": budget_test(),
    }
    return tables


def save_tables(tables, folder="results"):
    """Save every table as a CSV file in the 'results' folder."""
    if not os.path.exists(folder):
        os.makedirs(folder)
    for name in tables:
        pd.DataFrame(tables[name]).to_csv(os.path.join(folder, name + ".csv"), index=False)


# Quick test: run  python experiments.py   (takes a few seconds)
if __name__ == "__main__":
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.max_colwidth", 60)

    tables = run_everything()
    for name in tables:
        print()
        print("=== " + name)
        print(pd.DataFrame(tables[name]).to_string(index=False))
    save_tables(tables)

    print()
    print("=== 7_zero_day_test")
    z = zero_day_test()
    print("Old plan:", z["old_plan"])
    print("Old plan still valid after the new weakness?", z["old_plan_still_valid"])
    print(pd.DataFrame(z["defender_replanning"]).to_string(index=False))
    print()
    print("Saved CSV files in the 'results' folder.")