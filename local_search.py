# local_search.py
# More ways for the DEFENDER to choose a defense plan.
# These methods do not build a plan step by step. They start with a complete plan
# and keep improving it:
#   1. hill_climbing          : keep moving to a better neighbour plan
#   2. beam_search            : like hill climbing, but keeps the best K plans at once
#   3. genetic_algorithm      : a population of plans that mix and mutate (like evolution)
#
# Score of a plan (SMALLER is BETTER):
#   score = conflicts x 100 + defense cost
# A valid plan has 0 conflicts, so its score is just its cost.
# So these methods look for a valid plan that is also CHEAP.

import time
import random
from csp import (make_main_problem, make_random_problem, get_variables,
                 count_conflicts, plan_cost, is_valid_plan, result)


def score(p, defended):
    """Smaller is better. 100 per conflict + the cost of the plan."""
    return count_conflicts(p, defended) * 100 + plan_cost(p, defended)


def random_plan(p, variables):
    """A random plan: each node is defended with 50% chance. Must-defend nodes always."""
    defended = set()
    for v in variables:
        if random.random() < 0.5 or v in p["must"]:
            defended.add(v)
    return defended


def neighbours(p, defended, variables):
    """All plans we get by flipping ONE node (defend <-> not defend)."""
    plans = []
    for v in variables:
        if v in p["must"]:
            continue
        plan = set(defended)
        if v in plan:
            plan.remove(v)
        else:
            plan.add(v)
        plans.append(plan)
    return plans


# ---------------------------------------------------------------
# 1. Hill Climbing (with random restarts)
# ---------------------------------------------------------------
def hill_climbing(p, restarts=10, seed=1):
    t = time.perf_counter()
    random.seed(seed)
    variables = get_variables(p)
    evaluations = 0
    best_plan = None
    best_score = None

    for r in range(restarts):
        current = random_plan(p, variables)
        current_score = score(p, current)
        evaluations = evaluations + 1
        while True:
            # look at all neighbours and pick the best one
            best_neighbour = None
            best_neighbour_score = None
            for plan in neighbours(p, current, variables):
                s = score(p, plan)
                evaluations = evaluations + 1
                if best_neighbour_score is None or s < best_neighbour_score:
                    best_neighbour = plan
                    best_neighbour_score = s
            # stop when no neighbour is better (we are on a hill top / local best)
            if best_neighbour_score is None or best_neighbour_score >= current_score:
                break
            current = best_neighbour
            current_score = best_neighbour_score

        if best_score is None or current_score < best_score:
            best_plan = current
            best_score = current_score

    return result(p, "Hill Climbing", best_plan, evaluations, 0, t,
                  gave_up=not is_valid_plan(p, best_plan))


# ---------------------------------------------------------------
# 2. Beam Search (keep the best K plans)
# ---------------------------------------------------------------
def beam_search(p, width=5, max_steps=50, seed=1):
    t = time.perf_counter()
    random.seed(seed)
    variables = get_variables(p)
    evaluations = 0

    beam = []
    for i in range(width):
        beam.append(random_plan(p, variables))

    best_plan = None
    best_score = None
    for step in range(max_steps):
        # collect all neighbours of every plan in the beam
        candidates = []
        for plan in beam:
            candidates.append(plan)
            candidates = candidates + neighbours(p, plan, variables)
        scored = []
        for plan in candidates:
            scored.append((score(p, plan), sorted(plan)))
            evaluations = evaluations + 1
        scored.sort()

        # keep the best 'width' DIFFERENT plans
        new_beam = []
        seen = []
        for s, plan in scored:
            if plan not in seen:
                seen.append(plan)
                new_beam.append(set(plan))
            if len(new_beam) == width:
                break
        beam = new_beam

        top_score = scored[0][0]
        if best_score is not None and top_score >= best_score:
            break                              # no improvement, stop
        best_score = top_score
        best_plan = beam[0]

    return result(p, "Beam Search", best_plan, evaluations, 0, t,
                  gave_up=not is_valid_plan(p, best_plan))


# ---------------------------------------------------------------
# 3. Genetic Algorithm
# ---------------------------------------------------------------
def genetic_algorithm(p, population_size=30, generations=60, mutation=0.05, seed=1):
    t = time.perf_counter()
    random.seed(seed)
    variables = get_variables(p)
    evaluations = 0

    # A chromosome is a list of 0/1, one number for each node
    def to_plan(chromosome):
        plan = set()
        for i in range(len(variables)):
            if chromosome[i] == 1 or variables[i] in p["must"]:
                plan.add(variables[i])
        return plan

    def fitness(chromosome):
        return score(p, to_plan(chromosome))

    # Step 1: make a random starting population
    population = []
    for i in range(population_size):
        chromosome = []
        for v in variables:
            chromosome.append(random.randint(0, 1))
        population.append(chromosome)

    best = None
    best_score = None
    for g in range(generations):
        # Step 2: score everyone (smaller is better)
        scored = []
        for chromosome in population:
            scored.append((fitness(chromosome), chromosome))
            evaluations = evaluations + 1
        scored.sort(key=lambda item: item[0])

        if best_score is None or scored[0][0] < best_score:
            best_score = scored[0][0]
            best = scored[0][1]

        # Step 3: build the next generation
        new_population = [scored[0][1], scored[1][1]]       # keep the 2 best as they are
        while len(new_population) < population_size:
            # pick 2 parents: the best of 3 random plans (tournament)
            parents = []
            for k in range(2):
                group = random.sample(scored, 3)
                group.sort(key=lambda item: item[0])
                parents.append(group[0][1])
            # crossover: first part from parent 1, second part from parent 2
            cut = random.randint(1, len(variables) - 1)
            child = parents[0][:cut] + parents[1][cut:]
            # mutation: flip a few values by chance
            for i in range(len(child)):
                if random.random() < mutation:
                    child[i] = 1 - child[i]
            new_population.append(child)
        population = new_population

    best_plan = to_plan(best)
    return result(p, "Genetic Algorithm", best_plan, evaluations, 0, t,
                  gave_up=not is_valid_plan(p, best_plan))


# Quick test: run  python local_search.py
if __name__ == "__main__":
    p = make_main_problem(budget=20)
    print("Main network, budget =", p["budget"])
    for method in [hill_climbing, beam_search, genetic_algorithm]:
        r = method(p)
        print("-" * 60)
        print(r["name"])
        print("  Solved     :", r["solved"])
        print("  Defended   :", r["defended"])
        print("  Cost       :", r["cost"])
        print("  Evaluations:", r["tries"])
        print("  Time(ms)   :", r["time_ms"])