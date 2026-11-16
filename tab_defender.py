# tab_defender.py
# The "Defender" tab: the defender chooses which nodes to defend (a CSP problem).

import pandas as pd
import streamlit as st

from network import build_main_network, make_heuristic, START, GOAL
from search import a_star
from csp import make_main_problem, make_random_problem, MAIN_COSTS
from game import reduced_graph
from experiments import csp_comparison
from visuals import draw_network


def show(budget, depth, attacker_algorithm, defender_method, game_algorithm):
    st.subheader("🔵 Defender")
    st.write("The defender has a limited **budget** and must choose which nodes to defend. "
             "A defended node is blocked, so the attacker cannot pass through it.")

    # The CSP in simple words
    with st.expander("This is a CSP (Constraint Satisfaction Problem). What are the parts?"):
        st.write("- **Variables:** every node except Internet and Database")
        st.write("- **Domain:** 1 = defend the node, 0 = do not defend it")
        st.write("- **Constraint 1:** total cost of the defended nodes must stay within the budget")
        st.write("- **Constraint 2:** the Admin PC must always be defended")
        st.write("- **Constraint 3:** the attacker must NOT be able to reach the Database")
        costs = pd.DataFrame({"Node": list(MAIN_COSTS.keys()),
                              "Cost to defend": list(MAIN_COSTS.values())})
        st.dataframe(costs, hide_index=True)

    graph = build_main_network()
    problem = make_main_problem(budget)
    rows = csp_comparison(problem)           # runs all 6 defender methods

    # Find the row of the method chosen in the sidebar
    chosen = rows[0]
    for row in rows:
        if row["Method"] == defender_method:
            chosen = row

    # 1. Result of the chosen method
    st.markdown("### Result of " + defender_method + " (budget " + str(budget) + ")")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Solved?", chosen["Solved?"])
    col2.metric("Defense cost", chosen["Defense cost"] if chosen["Solved?"] == "Yes" else "-")
    col3.metric("Work (tries/steps)", chosen["Work (tries/steps)"])
    col4.metric("Time (ms)", chosen["Time (ms)"])

    defended = []
    if chosen["Solved?"] == "Yes":
        defended = chosen["Defended nodes"].split(", ")
        st.write("**Defended nodes:** " + chosen["Defended nodes"])

        # What can the attacker do after the defense?
        left = reduced_graph(graph, defended)
        attack = a_star(left, START, GOAL, make_heuristic(left, GOAL))
        if attack["path"] is None:
            st.success("The attacker is completely blocked. The Database is safe!")
        else:
            st.error("The attacker can still get in!")
    else:
        st.warning("No valid defense plan found with this budget (or this method gave up). "
                   "Try a bigger budget in the sidebar.")

    st.plotly_chart(draw_network(graph, defended=defended), key="defender_tab_map")

    # 2. Comparison of all methods
    st.markdown("### All defender methods compared")
    table = pd.DataFrame(rows)
    st.dataframe(table, hide_index=True)

    solved = table[table["Solved?"] == "Yes"]
    if len(solved) > 0:
        data = solved.set_index("Method")
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("**Defense cost** (smaller = cheaper plan)")
            st.bar_chart(data[["Defense cost"]])
        with col_b:
            st.write("**Work done** (tries or steps, smaller = faster)")
            st.bar_chart(data[["Work (tries/steps)"]])

        cheapest = solved.sort_values("Defense cost").iloc[0]
        fastest = solved.sort_values("Work (tries/steps)").iloc[0]
        st.success("Cheapest plan: **" + cheapest["Method"] + "** (cost "
                   + str(cheapest["Defense cost"]) + "). Least work: **"
                   + fastest["Method"] + "** (" + str(fastest["Work (tries/steps)"]) + ").")
    st.caption("On this small network every method is quick. "
               "The real difference shows on bigger networks. Try the test below.")

    # 3. Bigger network test (what if the network grows?)
    st.markdown("### What if the network is bigger?")
    size = st.slider("Number of nodes in a random network", min_value=10, max_value=40,
                     value=30, step=5)
    if st.button("Run this test"):
        big = make_random_problem(size, seed=1)
        big_rows = csp_comparison(big)
        big_table = pd.DataFrame(big_rows).drop(columns=["Defended nodes"])
        st.write("Random network with **" + str(size) + " nodes** (budget " + str(big["budget"]) + ")")
        st.dataframe(big_table, hide_index=True)
        st.info("Look at the 'Work' column. Plain Backtracking does far more work than "
                "Backtracking + MRV + FC as the network grows.")