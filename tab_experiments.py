# tab_experiments.py
# The "Experiments" tab: runs ALL algorithms and shows the comparison tables and charts.
# This is the testing and analysis part of the project.

import pandas as pd
import streamlit as st

from csp import make_main_problem
from experiments import (search_comparison, csp_comparison, game_comparison,
                         scaling_search, scaling_csp, budget_test, zero_day_test)


@st.cache_data
def get_fixed_tables():
    """Tables that do not depend on the budget (done once, then remembered)."""
    return {"search": search_comparison(),
            "scaling_search": scaling_search(),
            "scaling_csp": scaling_csp()}


@st.cache_data
def get_budget_tables(budget):
    """Tables that depend on the budget chosen in the sidebar."""
    p = make_main_problem(budget)
    # The new-weakness test needs a working defense plan first.
    # With a budget below 17 no plan exists, so that test uses budget 20 instead.
    zero_budget = budget
    if budget < 17:
        zero_budget = 20
    return {"defender": csp_comparison(p),
            "game": game_comparison(p),
            "budget": budget_test(),
            "zero_day": zero_day_test(zero_budget),
            "zero_budget": zero_budget}


def download_button(table, name):
    """A small button to download a table as a CSV file."""
    st.download_button("Download this table (CSV)", table.to_csv(index=False),
                       file_name=name + ".csv", key="download_" + name)


def show(budget, depth, attacker_algorithm, defender_method, game_algorithm):
    st.subheader("📊 Experiments")
    st.write("Here every algorithm is tested on the same problems. "
             "These tables and charts are the results for the report.")

    if st.button("Run all experiments (takes about 10 seconds)"):
        st.session_state["experiments_done"] = True
    if not st.session_state.get("experiments_done", False):
        st.info("Click the button above to run the experiments.")
        return

    fixed = get_fixed_tables()
    changing = get_budget_tables(budget)

    # ---------------- 1. Attacker searches ----------------
    st.markdown("### 1. Attacker searches (main network)")
    t1 = pd.DataFrame(fixed["search"])
    st.dataframe(t1, hide_index=True)
    st.bar_chart(t1.set_index("Algorithm")[["Nodes expanded"]])
    st.caption("A* and Branch and Bound find the cheapest path. A* opens fewer nodes.")
    download_button(t1, "1_search_comparison")

    # ---------------- 2. Defender methods ----------------
    st.markdown("### 2. Defender methods (budget " + str(budget) + ")")
    t2 = pd.DataFrame(changing["defender"])
    st.dataframe(t2, hide_index=True)
    download_button(t2, "2_defender_comparison")

    # ---------------- 3. Minimax vs Alpha-Beta ----------------
    st.markdown("### 3. Minimax vs Alpha-Beta")
    t3 = pd.DataFrame(changing["game"])
    st.dataframe(t3, hide_index=True)
    st.bar_chart(t3.set_index("Depth")[["Minimax positions", "Alpha-Beta positions"]])
    download_button(t3, "3_minimax_vs_alphabeta")

    # ---------------- 4. Scaling: attacker searches ----------------
    st.markdown("### 4. Bigger networks: attacker searches")
    t4 = pd.DataFrame(fixed["scaling_search"])
    st.dataframe(t4, hide_index=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Average nodes expanded** as the network grows")
        st.line_chart(t4.pivot_table(index="Nodes", columns="Algorithm",
                                     values="Avg nodes expanded"))
    with col_b:
        biggest = t4["Nodes"].max()
        st.write("**Average path cost** on the biggest network (" + str(biggest) + " nodes)")
        last = t4[t4["Nodes"] == biggest].set_index("Algorithm")
        st.bar_chart(last[["Avg path cost"]])
    download_button(t4, "4_scaling_search")

    # ---------------- 5. Scaling: defender methods ----------------
    st.markdown("### 5. Bigger networks: defender methods")
    t5 = pd.DataFrame(fixed["scaling_csp"])
    st.dataframe(t5, hide_index=True)
    st.write("**Average work (tries/steps)** as the network grows")
    st.line_chart(t5.pivot_table(index="Nodes", columns="Method",
                                 values="Avg work (tries/steps)"))
    download_button(t5, "5_scaling_defender")

    # ---------------- 6. What if the budget changes? ----------------
    st.markdown("### 6. What if the budget changes?")
    t6 = pd.DataFrame(changing["budget"])
    st.dataframe(t6, hide_index=True)
    download_button(t6, "6_budget_test")

    # ---------------- 7. What if a new weakness appears? ----------------
    st.markdown("### 7. What if a new weakness appears?")
    st.write("We add a new attack step: Internet to Student Portal (difficulty 2).")
    if changing["zero_budget"] != budget:
        st.caption("Your budget is too small for any defense plan, so this test uses budget "
                   + str(changing["zero_budget"]) + ".")
    z = changing["zero_day"]
    if z["old_plan_still_valid"]:
        st.success("The old defense plan still works.")
    else:
        st.error("The old defense plan " + str(z["old_plan"]) + " no longer works. "
                 "The defender must plan again.")
    t7 = pd.DataFrame(z["defender_replanning"])
    st.dataframe(t7, hide_index=True)
    download_button(t7, "7_zero_day_replanning")

    # ---------------- Key findings (written from the numbers above) ----------------
    st.markdown("### Key findings")
    big5 = t5[t5["Nodes"] == t5["Nodes"].max()].set_index("Method")
    plain = big5.loc["Backtracking", "Avg work (tries/steps)"]
    smart = big5.loc["Backtracking + MRV + FC", "Avg work (tries/steps)"]
    st.write("- On " + str(t5["Nodes"].max()) + " nodes, plain Backtracking needed about "
             + str(plain) + " tries, but Backtracking + MRV + FC needed only about "
             + str(smart) + ".")
    last_game = t3.iloc[-1]
    st.write("- At depth " + str(last_game["Depth"]) + ", Alpha-Beta searched "
             + str(last_game["Alpha-Beta positions"]) + " positions and Minimax "
             + str(last_game["Minimax positions"]) + " (same moves).")
    best_search = t1[t1["Optimal?"] == "Yes"].sort_values("Nodes expanded").iloc[0]
    st.write("- For the attacker, the most feasible search is " + best_search["Algorithm"]
             + ": cheapest path with the fewest nodes opened.")