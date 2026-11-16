# app.py
# The FRONTEND of the project (what the user sees in the browser).
# Run it with:  streamlit run app.py
# This is the FINAL version of app.py. From now on you never edit it again.
# Every other tab lives in its own file (tab_search.py, tab_defender.py, ...).

import importlib
import pandas as pd
import streamlit as st

from network import build_main_network, make_heuristic, START, GOAL
from search import bfs, dfs, progressive_deepening, best_first, a_star, branch_and_bound
from csp import make_main_problem, backtracking, backtracking_smart, min_conflicts
from local_search import hill_climbing, beam_search, genetic_algorithm
from game import reduced_graph
from visuals import draw_network

# ---------------------------------------------------------------
# Small helper functions
# ---------------------------------------------------------------
DEFENDERS = {
    "Backtracking": backtracking,
    "Backtracking + MRV + FC": backtracking_smart,
    "Min-Conflicts": min_conflicts,
    "Hill Climbing": hill_climbing,
    "Beam Search": beam_search, 
    "Genetic Algorithm": genetic_algorithm,
}


def run_attacker(name, graph):
    """Run the chosen search algorithm and return its result."""
    h = make_heuristic(graph, GOAL)
    if name == "BFS":
        return bfs(graph, START, GOAL)
    if name == "DFS":
        return dfs(graph, START, GOAL)
    if name == "Progressive Deepening":
        return progressive_deepening(graph, START, GOAL)
    if name == "Best-First":
        return best_first(graph, START, GOAL, h)
    if name == "A*":
        return a_star(graph, START, GOAL, h)
    return branch_and_bound(graph, START, GOAL)


def show_tab(module_name, **settings):
    """Load the file of a tab (for example tab_search.py) and show it.
    If the file does not exist yet, show a 'coming soon' message instead."""
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        st.info("Coming soon. Create the file " + module_name + ".py to fill this tab.")
        return
    module.show(**settings)


# ---------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------
st.set_page_config(page_title="Red vs Blue AI", page_icon="🛡️", layout="wide")

st.title("🛡️ Red vs Blue AI")
st.caption("Attacker AI vs Defender AI on a university network "
           "(Search, CSP, Local Search and Adversarial Search)")

# ---------------------------------------------------------------
# Sidebar: the settings the user can change
# ---------------------------------------------------------------
st.sidebar.header("⚙️ Settings")

budget = st.sidebar.slider("Defense budget", min_value=5, max_value=40, value=20,
                           help="How much money the defender can spend on defending nodes")

depth = st.sidebar.slider("Game search depth", min_value=2, max_value=5, value=3,
                          help="How many moves ahead Minimax / Alpha-Beta think")

attacker_algorithm = st.sidebar.selectbox(
    "Attacker search algorithm",
    ["BFS", "DFS", "Progressive Deepening", "Best-First", "A*", "Branch and Bound"],
    index=4)

defender_method = st.sidebar.selectbox(
    "Defender method",
    ["Backtracking", "Backtracking + MRV + FC", "Min-Conflicts",
     "Hill Climbing", "Beam Search", "Genetic Algorithm"],
    index=1)

game_algorithm = st.sidebar.radio("Battle algorithm", ["Alpha-Beta", "Minimax"])

st.sidebar.markdown("---")
st.sidebar.write("**Start:**", START)
st.sidebar.write("**Goal:**", GOAL)

# ---------------------------------------------------------------
# Main area: tabs
# ---------------------------------------------------------------
tab_network, tab_search, tab_defender, tab_battle, tab_experiments, tab_why = st.tabs(
    ["🌐 Network", "🔴 Attacker Search", "🔵 Defender", "⚔️ Battle",
     "📊 Experiments", "🧠 Why hacked?"])

graph = build_main_network()

with tab_network:
    st.subheader("The university network")

    edge_count = 0
    for node in graph:
        edge_count = edge_count + len(graph[node])
    col1, col2, col3 = st.columns(3)
    col1.metric("Nodes", len(graph))
    col2.metric("Connections", edge_count)
    col3.metric("Defense budget", budget)

    show_attack = st.checkbox("Show the attacker's path (red)", value=True)
    show_defense = st.checkbox("Show the defense plan (green)", value=False)

    # Step 1: get the defense plan (if the user wants to see it)
    defended = []
    if show_defense:
        problem = make_main_problem(budget)
        plan = DEFENDERS[defender_method](problem)
        if plan["solved"]:
            defended = plan["defended"]
            st.success("Defense plan (" + defender_method + "), cost "
                       + str(plan["cost"]) + ": " + ", ".join(defended))
        else:
            st.warning("No valid defense plan found with this budget. Try a bigger budget.")

    # Step 2: find the attacker's path (on the network that is left after the defense)
    path = []
    if show_attack:
        attack_graph = reduced_graph(graph, defended)
        result = run_attacker(attacker_algorithm, attack_graph)
        if result["path"] is None:
            st.success("The attacker is completely blocked. The Database is safe!")
        else:
            path = result["path"]
            st.write("**" + attacker_algorithm + "** path (cost " + str(result["cost"]) + "): "
                     + " → ".join(path))

    # Step 3: draw the map
    st.plotly_chart(draw_network(graph, attack_path=path, defended=defended))
    st.caption("Numbers on the arrows = difficulty of that attack step.")

    with st.expander("Show all connections as a table"):
        rows = []
        for a in graph:
            for b in graph[a]:
                rows.append({"From": a, "To": b, "Difficulty": graph[a][b]})
        st.dataframe(pd.DataFrame(rows), hide_index=True)

# Each of these tabs lives in its own file. Just add the file and it appears here.
settings = dict(budget=budget, depth=depth, attacker_algorithm=attacker_algorithm,
                defender_method=defender_method, game_algorithm=game_algorithm)

with tab_search:
    show_tab("tab_search", **settings)

with tab_defender:
    show_tab("tab_defender", **settings)

with tab_battle:
    show_tab("tab_battle", **settings)

with tab_experiments:
    show_tab("tab_experiments", **settings)

with tab_why:
    show_tab("tab_why", **settings)