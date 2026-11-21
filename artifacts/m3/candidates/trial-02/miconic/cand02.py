from heuristics.heuristic_base import Heuristic

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Miconic domain.

    # Summary
    This heuristic estimates the minimum number of actions required to serve all passengers 
    and satisfy any lift-position goals. It assigns a heavily weighted action cost for 
    boarding and departing passengers, and a move cost based on the number of unique 
    actionable target floors the elevator still needs to visit.

    # Assumptions
    - Passengers can be boarded if the elevator is at their origin floor.
    - Passengers can be departed (served) if the elevator is at their destination floor.
    - The elevator can hold an unlimited number of passengers concurrently.
    - The elevator can move directly between any two valid floors in 1 action (since the `above` predicate is specified as a fully connected transitive closure in Miconic instances).

    # Heuristic Initialization
    - Extract the goal conditions to identify which passengers need to be served or boarded, and whether there's a specific goal for the final lift position.
    - Extract static information, specifically the `destin` (destination) of each passenger.
    - Extract `initial_origins` in case an unboarded passenger's origin is missing from a state evaluation due to a parsed anomaly, providing a safe fallback.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find:
       - Which passengers are `served`.
       - Which passengers are `boarded`.
       - The current `origin` of unboarded passengers.
       - The current location of the elevator (`lift-at`).
    2. Identify actionable target floors and calculate passenger action costs:
       - For each passenger that needs to be served:
           - If already served, cost is 0.
           - If boarded, we need 1 action to depart. To ensure a strictly decreasing gradient, we weight passenger actions by 2, so `cost += 2`. The passenger's destination is added to the actionable target floors.
           - If not boarded, we need 2 actions (board, depart). We add `cost += 4`. The passenger's origin is added to the actionable target floors.
       - For any `lift-at` goal, add it to the target floors if not already satisfied.
    3. Compute move costs:
       - The base move cost is the total number of unique actionable target floors.
       - If the elevator's current floor is already one of these target floors, it does not need an initial move to reach a target, so we subtract 1 from the move cost.
    4. Return the sum of passenger action costs and the move cost. Because of the weighted passenger cost (+2 per physical action) versus move cost (+1 per floor sequence), every required logical step locally or globally guarantees a strictly decreasing heuristic score without deep plateaus.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.target_served = set()
        self.target_boarded = set()
        self.goal_lift_at = None

        # Extract goals efficiently by removing parentheses and checking prefixes
        for goal in self.goals:
            if goal.startswith("(served "):
                self.target_served.add(goal[8:-1])
            elif goal.startswith("(boarded "):
                self.target_boarded.add(goal[9:-1])
            elif goal.startswith("(lift-at "):
                self.goal_lift_at = goal[9:-1]

        self.destin = {}
        self.initial_origins = {}
        
        # Extract static information and initial origins as a fallback map
        for fact in list(task.static) + list(task.initial_state):
            if fact.startswith("(destin "):
                parts = fact[8:-1].split()
                if len(parts) == 2:
                    self.destin[parts[0]] = parts[1]
            elif fact.startswith("(origin "):
                parts = fact[8:-1].split()
                if len(parts) == 2:
                    self.initial_origins[parts[0]] = parts[1]

    def __call__(self, node):
        state = node.state
        served = set()
        boarded = set()
        origins = {}
        lift_at = None

        # Parse the current node's state
        for fact in state:
            if fact.startswith("(served "):
                served.add(fact[8:-1])
            elif fact.startswith("(boarded "):
                boarded.add(fact[9:-1])
            elif fact.startswith("(origin "):
                parts = fact[8:-1].split()
                if len(parts) == 2:
                    origins[parts[0]] = parts[1]
            elif fact.startswith("(lift-at "):
                lift_at = fact[9:-1]

        cost = 0
        target_floors = set()

        # Compute cost for passengers needing to be served
        for p in self.target_served:
            if p in served:
                continue
            
            if p in boarded:
                cost += 2
                if p in self.destin:
                    target_floors.add(self.destin[p])
            else:
                cost += 4
                origin_floor = origins.get(p, self.initial_origins.get(p))
                if origin_floor:
                    target_floors.add(origin_floor)

        # Compute cost for any passengers that only need to be boarded (rare but fully supported)
        for p in self.target_boarded:
            if p in self.target_served or p in served or p in boarded:
                continue
            
            cost += 2
            origin_floor = origins.get(p, self.initial_origins.get(p))
            if origin_floor:
                target_floors.add(origin_floor)

        # Include specific lift location goal if requested
        if self.goal_lift_at and lift_at != self.goal_lift_at:
            target_floors.add(self.goal_lift_at)

        # Calculate estimated movement cost based on distinct target floors
        moves = 0
        if target_floors:
            moves = len(target_floors)
            # If the elevator is already at a target floor, one initial commute is saved
            if lift_at in target_floors:
                moves -= 1

        return cost + moves
