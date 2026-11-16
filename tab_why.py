# tab_why.py
# The "Why hacked?" tab: a small knowledge-based system explains HOW the Database gets hacked.
# It uses IF-THEN rules with forward chaining and backward chaining (see kb.py).

import pandas as pd
import streamlit as st

from network import build_main_network
from kb import (RULES, GOAL_FACT, SMALL_SCENARIO, ALL_WEAKNESSES, forward_chaining,
                backward_chaining, compromised_nodes, single_fix_test)
from visuals import draw_network


def show(budget, depth, attacker_algorithm, defender_method, game_algorithm):
    st.subheader("🧠 Why was it hacked?")
    st.write("This part is a **knowledge-based system**. It knows IF-THEN rules about the network. "
             "Choose which weaknesses exist, and it explains how the attacker can reach the Database.")

    # The rules
    with st.expander("See the rules (the knowledge base)"):
        rule_rows = []
        for rule in RULES:
            rule_rows.append({"Rule": rule["name"],
                              "IF": " AND ".join(rule["if"]),
                              "THEN": rule["then"]})
        st.dataframe(pd.DataFrame(rule_rows), hide_index=True)

    # 1. Choose the weaknesses
    st.markdown("### 1. Which weaknesses exist?")
    choice = st.radio("Scenario", ["Small (one attack chain)", "Every weakness",
                                   "Choose my own"], horizontal=True)
    if choice == "Small (one attack chain)":
        facts = list(SMALL_SCENARIO)
    elif choice == "Every weakness":
        facts = list(ALL_WEAKNESSES)
    else:
        facts = st.multiselect("Pick the weaknesses", ALL_WEAKNESSES, default=SMALL_SCENARIO)

    st.write("**Known weaknesses:** " + (", ".join(facts) if len(facts) > 0 else "none"))

    # 2. Forward chaining
    st.markdown("### 2. Forward chaining: what gets hacked?")
    st.write("We start from the weaknesses and keep applying the rules, like the doctor example "
             "in the lecture.")
    known, steps = forward_chaining(facts)
    hacked = GOAL_FACT in known

    col1, col2 = st.columns(2)
    col1.metric("Rules fired", len(steps))
    col2.metric("Database hacked?", "Yes" if hacked else "No")

    if len(steps) > 0:
        step_rows = []
        number = 1
        for step in steps:
            step_rows.append({"Step": number, "Rule": step["rule"],
                              "IF": " AND ".join(step["if"]), "THEN": step["then"]})
            number = number + 1
        st.dataframe(pd.DataFrame(step_rows), hide_index=True)
    else:
        st.info("No rule can fire with these weaknesses.")

    if hacked:
        st.error("The Database gets hacked.")
    else:
        st.success("The Database stays safe with these weaknesses.")

    graph = build_main_network()
    st.plotly_chart(draw_network(graph, compromised=compromised_nodes(known)),
                    key="why_tab_map")
    st.caption("Orange-red nodes are the ones the attacker takes over.")

    # 3. Backward chaining
    st.markdown("### 3. Backward chaining: why can the Database be hacked?")
    st.write("We start from the goal **" + GOAL_FACT + "** and ask: what must be true for this?")
    answer, trace = backward_chaining(GOAL_FACT, facts)
    st.code("\n".join(trace), language=None)
    if answer:
        st.write("**Answer:** yes, the goal can be proved.")
    else:
        st.write("**Answer:** no, the goal cannot be proved.")

    # 4. What if we fix one weakness?
    st.markdown("### 4. What if we fix one weakness?")
    if len(facts) > 0:
        fixes = single_fix_test(facts)
        st.dataframe(pd.DataFrame(fixes), hide_index=True)
        saved = [row["Weakness fixed"] for row in fixes
                 if row["Database still hacked?"] == "No"]
        if not hacked:
            st.info("The Database is already safe.")
        elif len(saved) > 0:
            st.success("Fixing any one of these stops the attack: " + ", ".join(saved) + ".")
        else:
            st.warning("No single fix is enough. There are many attack chains, "
                       "so the defender needs several defenses.")
    else:
        st.info("Pick at least one weakness to try this.")