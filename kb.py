# kb.py
# A small KNOWLEDGE-BASED SYSTEM: it explains HOW the Database can be hacked.
#
# Knowledge base = a list of IF-THEN rules, for example:
#   IF "Staff PC compromised" AND "admin password is weak" THEN "Admin PC compromised"
#
# We use two ways of reasoning (same as the doctor/pneumonia example in the lecture):
#   forward_chaining  : start from the known weaknesses, find everything that gets hacked
#   backward_chaining : start from the goal ("Database compromised") and ask
#                       "what must be true for this to happen?"

RULES = [
    {"name": "R1",  "if": ["phishing email works"],                                  "then": "Mail Server compromised"},
    {"name": "R2",  "if": ["Mail Server compromised", "users reuse passwords"],      "then": "Staff PC compromised"},
    {"name": "R3",  "if": ["WiFi password is weak"],                                 "then": "WiFi compromised"},
    {"name": "R4",  "if": ["WiFi compromised", "lab PCs are unpatched"],             "then": "Lab PCs compromised"},
    {"name": "R5",  "if": ["VPN credentials stolen"],                                "then": "VPN compromised"},
    {"name": "R6",  "if": ["VPN compromised"],                                       "then": "Staff PC compromised"},
    {"name": "R7",  "if": ["Staff PC compromised", "admin password is weak"],        "then": "Admin PC compromised"},
    {"name": "R8",  "if": ["firewall is misconfigured"],                             "then": "Firewall bypassed"},
    {"name": "R9",  "if": ["Firewall bypassed", "portal has SQL injection"],         "then": "Student Portal compromised"},
    {"name": "R10", "if": ["Firewall bypassed", "web server is unpatched"],          "then": "Web Server compromised"},
    {"name": "R11", "if": ["Web Server compromised"],                                "then": "App Server compromised"},
    {"name": "R12", "if": ["Lab PCs compromised", "file server password is shared"], "then": "File Server compromised"},
    {"name": "R13", "if": ["Staff PC compromised", "file server password is shared"], "then": "File Server compromised"},
    {"name": "R14", "if": ["File Server compromised", "backups are not encrypted"],  "then": "Backup Server compromised"},
    {"name": "R15", "if": ["Admin PC compromised"],                                  "then": "Database compromised"},
    {"name": "R16", "if": ["Student Portal compromised"],                            "then": "Database compromised"},
    {"name": "R17", "if": ["App Server compromised"],                                "then": "Database compromised"},
    {"name": "R18", "if": ["Backup Server compromised"],                             "then": "Database compromised"},
]

GOAL_FACT = "Database compromised"

# Scenario 1: a small set of weaknesses (one attack chain)
SMALL_SCENARIO = ["phishing email works", "users reuse passwords", "admin password is weak"]

# Scenario 2: every weakness exists (many attack chains)
ALL_WEAKNESSES = ["phishing email works", "users reuse passwords", "WiFi password is weak",
                  "lab PCs are unpatched", "VPN credentials stolen", "admin password is weak",
                  "firewall is misconfigured", "portal has SQL injection",
                  "web server is unpatched", "file server password is shared",
                  "backups are not encrypted"]


def forward_chaining(facts):
    """Keep firing rules until nothing new can be found.
    Returns (all known facts, list of steps)."""
    known = set(facts)
    steps = []
    changed = True
    while changed:
        changed = False
        for rule in RULES:
            if rule["then"] in known:
                continue
            all_true = True
            for premise in rule["if"]:
                if premise not in known:
                    all_true = False
            if all_true:
                known.add(rule["then"])
                steps.append({"rule": rule["name"], "if": rule["if"], "then": rule["then"]})
                changed = True
    return known, steps


def backward_chaining(goal, facts):
    """Try to prove 'goal' by working backwards.
    Returns (True/False, trace). The trace is a list of text lines that explain the thinking."""
    trace = []

    def prove(fact, depth, visiting):
        pad = "    " * depth
        if fact in facts:
            trace.append(pad + fact + "  -> known weakness (TRUE)")
            return True
        rules = [r for r in RULES if r["then"] == fact]
        if len(rules) == 0:
            trace.append(pad + fact + "  -> no such weakness (FALSE)")
            return False
        if fact in visiting:
            trace.append(pad + fact + "  -> already being checked, skip")
            return False
        trace.append(pad + "Goal: " + fact)
        for rule in rules:
            trace.append(pad + "  Try " + rule["name"] + ": IF " + " AND ".join(rule["if"]))
            works = True
            for premise in rule["if"]:
                if not prove(premise, depth + 1, visiting + [fact]):
                    works = False
                    break
            if works:
                trace.append(pad + "  " + rule["name"] + " works, so '" + fact + "' is TRUE")
                return True
        trace.append(pad + "  No rule works, so '" + fact + "' is FALSE")
        return False

    answer = prove(goal, 0, [])
    return answer, trace


def compromised_nodes(known):
    """Turn the facts into network node names (used to colour the network map)."""
    nodes = []
    for fact in known:
        if fact.endswith(" compromised"):
            nodes.append(fact[:-len(" compromised")])
        if fact.endswith(" bypassed"):
            nodes.append(fact[:-len(" bypassed")])
    return sorted(nodes)


def single_fix_test(facts):
    """What if we fix ONE weakness? Does the Database still get hacked?"""
    rows = []
    for fact in facts:
        remaining = [f for f in facts if f != fact]
        known, steps = forward_chaining(remaining)
        hacked = GOAL_FACT in known
        rows.append({"Weakness fixed": fact,
                     "Database still hacked?": "Yes" if hacked else "No"})
    return rows


# Quick test: run  python kb.py
if __name__ == "__main__":
    print("SCENARIO 1: small set of weaknesses")
    print("Known weaknesses:", SMALL_SCENARIO)
    print()
    print("--- Forward chaining ---")
    known, steps = forward_chaining(SMALL_SCENARIO)
    for s in steps:
        print(" ", s["rule"], ": IF", " AND ".join(s["if"]), "THEN", s["then"])
    print("  Database hacked?", GOAL_FACT in known)
    print("  Compromised nodes:", compromised_nodes(known))

    print()
    print("--- Backward chaining (goal: Database compromised) ---")
    answer, trace = backward_chaining(GOAL_FACT, SMALL_SCENARIO)
    for line in trace:
        print(line)
    print("  Answer:", answer)

    print()
    print("--- What if we fix one weakness? ---")
    for row in single_fix_test(SMALL_SCENARIO):
        print(" ", row["Weakness fixed"], "->", row["Database still hacked?"])

    print()
    print("SCENARIO 2: every weakness exists")
    known, steps = forward_chaining(ALL_WEAKNESSES)
    print("  Rules fired:", len(steps))
    print("  Compromised nodes:", compromised_nodes(known))
    fixes = single_fix_test(ALL_WEAKNESSES)
    saved = [r["Weakness fixed"] for r in fixes if r["Database still hacked?"] == "No"]
    print("  Single fixes that stop the attack:", saved if saved else "none (many attack chains)")