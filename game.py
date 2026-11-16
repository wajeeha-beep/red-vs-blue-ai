# game.py
# The BATTLE: Attacker (Red) vs Defender (Blue), taking turns.
#
# Each round:
#   1. The attacker moves one step along the network (to a node that is not defended).
#   2. The defender blocks one node (it costs budget).
# The attacker wins by reaching the Database.
# The defender wins if the attacker has no move left.
#
# Both players think ahead using:
#   minimax     : tries every move of both players up to a depth limit
#   alpha_beta  : gives the SAME answer as minimax but skips useless branches (faster)
#
# Attacker = MAX player (wants a high score), Defender = MIN player (wants a low score).

import time
from network import make_heuristic
from search import a_star
from csp import make_main_problem, get_variables

WIN = 1000      # score for "attacker reached the goal" (and -WIN when attacker is trapped)
INF = 10 ** 9

# A state is a tuple:  (attacker_node, defended_nodes, money_spent, visited_nodes)


def reduced_graph(graph, defended):
    """The network with the defended nodes removed."""
    new = {}
    for node in graph:
        if node not in defended:
            new[node] = {}
            for nxt in graph[node]:
                if nxt not in defended:
                    new[node][nxt] = graph[node][nxt]
    return new


def evaluate(p, state):
    """Score a position from the attacker's point of view (higher = better for attacker).
    We use A* to find the cheapest path left for the attacker. A shorter path is better."""
    node, defended, spent, visited = state
    if node == p["goal"]:
        return WIN
    graph = reduced_graph(p["graph"], defended)
    h = make_heuristic(graph, p["goal"])
    r = a_star(graph, node, p["goal"], h)
    if r["path"] is None:
        return -WIN
    return -r["cost"]


def attacker_moves(p, state):
    """All moves of the attacker: step to a neighbour that is open and not visited yet."""
    node, defended, spent, visited = state
    moves = []
    for nxt in p["graph"][node]:
        if nxt not in defended and nxt not in visited:
            moves.append((nxt, (nxt, defended, spent, visited + (nxt,))))
    return moves


def defender_moves(p, state):
    """All moves of the defender: block one node that it can still afford."""
    node, defended, spent, visited = state
    moves = []
    for v in get_variables(p):
        if v in defended or v == node or v in visited:
            continue
        cost = p["costs"][v]
        if spent + cost <= p["budget"]:
            moves.append((v, (node, defended | {v}, spent + cost, visited)))
    if len(moves) == 0:
        moves.append(("pass", state))         # nothing left to block
    return moves


# ---------------------------------------------------------------
# Minimax
# ---------------------------------------------------------------
def minimax(p, state, depth, attacker_turn, counter):
    """Returns (score, best_move). counter[0] counts how many positions we looked at."""
    counter[0] = counter[0] + 1
    if state[0] == p["goal"]:
        return WIN + depth, None              # attacker got there (sooner = better)
    if depth == 0:
        return evaluate(p, state), None

    if attacker_turn:
        moves = attacker_moves(p, state)
        if len(moves) == 0:
            return -WIN - depth, None         # attacker is trapped
        best_value = -INF
        best_move = None
        for move, new_state in moves:
            value, ignore = minimax(p, new_state, depth - 1, False, counter)
            if value > best_value:
                best_value = value
                best_move = move
        return best_value, best_move
    else:
        best_value = INF
        best_move = None
        for move, new_state in defender_moves(p, state):
            value, ignore = minimax(p, new_state, depth - 1, True, counter)
            if value < best_value:
                best_value = value
                best_move = move
        return best_value, best_move


# ---------------------------------------------------------------
# Alpha-Beta pruning
# ---------------------------------------------------------------
def alpha_beta(p, state, depth, attacker_turn, counter, alpha=-INF, beta=INF):
    """Same as minimax, but stops looking at a branch when it cannot change the answer.
    alpha = best score the attacker can already guarantee
    beta  = best score the defender can already guarantee"""
    counter[0] = counter[0] + 1
    if state[0] == p["goal"]:
        return WIN + depth, None
    if depth == 0:
        return evaluate(p, state), None

    if attacker_turn:
        moves = attacker_moves(p, state)
        if len(moves) == 0:
            return -WIN - depth, None
        best_value = -INF
        best_move = None
        for move, new_state in moves:
            value, ignore = alpha_beta(p, new_state, depth - 1, False, counter, alpha, beta)
            if value > best_value:
                best_value = value
                best_move = move
            if best_value > alpha:
                alpha = best_value
            if beta <= alpha:
                break                          # prune: the defender will never allow this
        return best_value, best_move
    else:
        best_value = INF
        best_move = None
        for move, new_state in defender_moves(p, state):
            value, ignore = alpha_beta(p, new_state, depth - 1, True, counter, alpha, beta)
            if value < best_value:
                best_value = value
                best_move = move
            if best_value < beta:
                beta = best_value
            if beta <= alpha:
                break                          # prune: the attacker will never allow this
        return best_value, best_move


# ---------------------------------------------------------------
# Play a full game
# ---------------------------------------------------------------
def play_game(p, algorithm, depth, start_defended=(), max_rounds=15):
    """Play Attacker vs Defender. 'algorithm' is minimax or alpha_beta.
    Returns the winner, a log of every round, and how many positions were searched."""
    t = time.perf_counter()
    defended = frozenset(start_defended)
    spent = 0
    for v in defended:
        spent = spent + p["costs"][v]
    state = (p["start"], defended, spent, (p["start"],))
    counter = [0]
    log = []
    winner = "Defender"

    for round_number in range(1, max_rounds + 1):
        # attacker moves
        value, move = algorithm(p, state, depth, True, counter)
        if move is None:
            winner = "Defender"                # attacker has no move
            break
        for m, new_state in attacker_moves(p, state):
            if m == move:
                state = new_state
        entry = {"round": round_number, "attacker_to": move, "defender_blocked": None}
        if state[0] == p["goal"]:
            log.append(entry)
            winner = "Attacker"
            break

        # defender moves
        value, move = algorithm(p, state, depth, False, counter)
        for m, new_state in defender_moves(p, state):
            if m == move:
                state = new_state
        entry["defender_blocked"] = move
        log.append(entry)
    else:
        winner = "Defender"                    # attacker ran out of rounds

    ms = (time.perf_counter() - t) * 1000
    return {"winner": winner, "log": log, "positions": counter[0],
            "time_ms": round(ms, 2), "path": list(state[3]),
            "blocked": sorted(state[1])}


def compare_depths(p, depths):
    """Run Minimax and Alpha-Beta for each depth and compare how much work they do."""
    rows = []
    for depth in depths:
        a = play_game(p, minimax, depth)
        b = play_game(p, alpha_beta, depth)
        saved = 0
        if a["positions"] > 0:
            saved = round(100 * (a["positions"] - b["positions"]) / a["positions"])
        rows.append({"depth": depth,
                     "minimax_positions": a["positions"], "alphabeta_positions": b["positions"],
                     "saved_percent": saved,
                     "minimax_ms": a["time_ms"], "alphabeta_ms": b["time_ms"],
                     "same_winner": a["winner"] == b["winner"],
                     "same_moves": a["log"] == b["log"],
                     "winner": a["winner"]})
    return rows


# Quick test: run  python game.py
if __name__ == "__main__":
    p = make_main_problem(budget=20)

    print("One game with Alpha-Beta, depth 3:")
    g = play_game(p, alpha_beta, 3)
    for entry in g["log"]:
        print("  Round", entry["round"], "| attacker goes to:", entry["attacker_to"],
              "| defender blocks:", entry["defender_blocked"])
    print("  Winner:", g["winner"])
    print("  Attacker path:", " -> ".join(g["path"]))

    print()
    print("Minimax vs Alpha-Beta (positions searched):")
    for row in compare_depths(p, [2, 3, 4]):
        print("  depth", row["depth"],
              "| minimax:", row["minimax_positions"],
              "| alpha-beta:", row["alphabeta_positions"],
              "| saved:", row["saved_percent"], "%",
              "| same moves:", row["same_moves"],
              "| winner:", row["winner"])