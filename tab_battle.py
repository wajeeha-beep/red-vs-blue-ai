# tab_battle.py
# The "Battle" tab: Attacker (Red) vs Defender (Blue), turn by turn.

import time
import pandas as pd
import streamlit as st

from network import build_main_network, START
from csp import make_main_problem
from game import play_game, minimax, alpha_beta
from experiments import game_comparison
from visuals import draw_network


@st.cache_data
def run_game(budget, depth, algorithm_name):
    """Play one full game (the answer is remembered, so moving the slider is fast)."""
    problem = make_main_problem(budget)
    if algorithm_name == "Minimax":
        return play_game(problem, minimax, depth)
    return play_game(problem, alpha_beta, depth)


@st.cache_data
def run_comparison(budget):
    """Compare Minimax and Alpha-Beta at depths 2 to 5 (takes a few seconds, done once)."""
    return game_comparison(make_main_problem(budget), depths=(2, 3, 4, 5))


def show(budget, depth, attacker_algorithm, defender_method, game_algorithm):
    st.subheader("⚔️ Battle")
    st.write("Each round, the **attacker** moves one step, then the **defender** blocks one node "
             "(it costs budget). Both think ahead using **" + game_algorithm + "** "
             "with depth " + str(depth) + ".")
    st.write("The attacker wins by reaching the Database. "
             "The defender wins if the attacker gets stuck.")

    graph = build_main_network()
    game = run_game(budget, depth, game_algorithm)
    log = game["log"]

    # 1. The result
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Winner", game["winner"])
    col2.metric("Rounds", len(log))
    col3.metric("Positions searched", game["positions"])
    col4.metric("Time (ms)", game["time_ms"])
    if game["winner"] == "Defender":
        st.success("The defender won. The attacker could not reach the Database.")
    else:
        st.error("The attacker won. The budget was not enough to stop it.")

    # 2. What happened in each round
    table_rows = []
    for entry in log:
        blocked = entry["defender_blocked"]
        if blocked is None:
            blocked = "-"
        table_rows.append({"Round": entry["round"],
                           "Attacker moves to": entry["attacker_to"],
                           "Defender blocks": blocked})
    st.dataframe(pd.DataFrame(table_rows), hide_index=True)

    # 3. Watch the battle round by round
    st.markdown("### Watch the battle")

    def draw_round(r, key):
        """Draw the network as it looks after round r."""
        path = [START]
        blocked = []
        for entry in log[:r]:
            path.append(entry["attacker_to"])
            if entry["defender_blocked"] not in (None, "pass"):
                blocked.append(entry["defender_blocked"])
        if r == 0:
            st.write("**Start:** the attacker is at the Internet.")
        else:
            entry = log[r - 1]
            text = "**Round " + str(r) + ":** attacker moves to " + entry["attacker_to"]
            if entry["defender_blocked"] not in (None, "pass"):
                text = text + ", defender blocks " + entry["defender_blocked"]
            st.write(text)
        st.plotly_chart(draw_network(graph, attack_path=path, defended=blocked,
                                     compromised=[path[-1]]), key=key)

    play = st.button("▶ Play the battle")
    round_number = st.slider("Or move through the rounds yourself", min_value=0,
                             max_value=len(log), value=len(log))
    slot = st.empty()
    if play:
        for r in range(len(log) + 1):
            with slot.container():
                draw_round(r, "battle_play_" + str(r))
            time.sleep(0.8)
    else:
        with slot.container():
            draw_round(round_number, "battle_slider_map")
    st.caption("Red path = where the attacker has been. Green = nodes blocked by the defender. "
               "Orange-red = where the attacker is now.")

    # 4. Minimax vs Alpha-Beta
    st.markdown("### Minimax vs Alpha-Beta")
    st.write("Alpha-Beta gives the same moves as Minimax, but skips branches that cannot change "
             "the answer. So it looks at fewer positions.")
    if st.button("Compare them (takes a few seconds)"):
        rows = run_comparison(budget)
        table = pd.DataFrame(rows)
        st.dataframe(table, hide_index=True)
        chart = table.set_index("Depth")[["Minimax positions", "Alpha-Beta positions"]]
        st.bar_chart(chart)
        st.info("Deeper search means many more positions. Alpha-Beta saves more work "
                "as the depth grows.")

    st.caption("What if? Try budget 12 in the sidebar: the defender cannot afford enough "
               "guards and the attacker wins.")