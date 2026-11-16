# tab_search.py
# The "Attacker Search" tab: shows how the 6 search algorithms behave on the network.

import pandas as pd
import streamlit as st

from network import build_main_network
from experiments import search_comparison
from visuals import draw_network


def show(budget, depth, attacker_algorithm, defender_method, game_algorithm):
    st.subheader("🔴 Attacker search")
    st.write("The attacker wants to go from the **Internet** to the **Database**. "
             "Each algorithm finds a path in its own way. Let us see which one is best.")

    graph = build_main_network()
    rows = search_comparison(graph)          # runs all 6 algorithms

    # Find the row of the algorithm chosen in the sidebar
    chosen = rows[0]
    for row in rows:
        if row["Algorithm"] == attacker_algorithm:
            chosen = row

    # 1. Result of the chosen algorithm
    st.markdown("### Result of " + attacker_algorithm)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Path cost", chosen["Path cost"])
    col2.metric("Nodes expanded", chosen["Nodes expanded"])
    col3.metric("Time (ms)", chosen["Time (ms)"])
    col4.metric("Optimal?", chosen["Optimal?"])
    st.write("**Path:** " + chosen["Path"])

    path = chosen["Path"].split(" -> ")
    st.plotly_chart(draw_network(graph, attack_path=path), key="search_tab_map")

    # 2. Comparison of all algorithms
    st.markdown("### All algorithms compared")
    table = pd.DataFrame(rows)
    st.dataframe(table, hide_index=True)

    chart_data = table.set_index("Algorithm")
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Nodes expanded** (smaller = faster search)")
        st.bar_chart(chart_data[["Nodes expanded"]])
    with col_b:
        st.write("**Path cost** (smaller = easier for the attacker)")
        st.bar_chart(chart_data[["Path cost"]])

    # 3. Which one is the most feasible?
    best = None
    for row in rows:
        if row["Optimal?"] == "Yes":
            if best is None or row["Nodes expanded"] < best["Nodes expanded"]:
                best = row
    st.success("Most feasible: **" + best["Algorithm"] + "**. It finds the cheapest path "
               "(cost " + str(best["Path cost"]) + ") and opens only "
               + str(best["Nodes expanded"]) + " nodes.")

    with st.expander("What does each algorithm do? (simple words)"):
        st.write("- **BFS:** checks the network level by level. Finds the path with the fewest steps, "
                 "but not always the cheapest.")
        st.write("- **DFS:** goes deep first. Fast sometimes, but the path can be very bad.")
        st.write("- **Progressive Deepening:** DFS with a depth limit of 1, 2, 3 ... "
                 "Fewest steps like BFS, but repeats work.")
        st.write("- **Best-First:** always goes to the node that looks closest to the goal. "
                 "Opens few nodes, but can miss the cheapest path.")
        st.write("- **A\\*:** looks at (cost so far + guess to the goal). "
                 "Cheapest path and few nodes opened.")
        st.write("- **Branch and Bound:** extends the cheapest partial path and drops paths that are "
                 "already too costly. Cheapest path, but opens more nodes than A*.")