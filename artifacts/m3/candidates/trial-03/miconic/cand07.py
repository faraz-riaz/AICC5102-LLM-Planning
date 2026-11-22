from heuristics.heuristic_base import Heuristic

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the miconic domain.

    # Summary
    This heuristic estimates the minimum number of actions required to serve all passengers.
    It counts the exact number of necessary `board` and `depart` actions for each unserved passenger,
    and accurately estimates the number of `up`/`down` move actions needed to visit all required floors.

    # Assumptions
    - The elevator has infinite capacity and can carry any number of passengers at once.
    - Moving between any two connected floors takes exactly 1 action, regardless of distance,
      because the `above` predicate typically connects all valid floor pairs directly.
    - An unserved passenger not yet boarded requires 1 `board` and 1 `depart` action.
    - A currently boarded passenger requires 1 `depart` action.
    - The lift needs to visit all origins of waiting passengers and destinations of all unserved passengers.

    # Heuristic Initialization
    - Extract all passengers that need to be served from the goal state.
    - Extract the destination floor for each passenger from the static facts or initial state.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to determine which passengers are `boarded`, which are `served`,
       the current `lift-at` location, and the `origin` floors of waiting passengers.
    2. For each passenger that still needs to be served:
       a. If they are `boarded`, they need 1 action (`depart`). Their destination floor is added to the set of required destinations `D`, and to the set of active floors `A`.
       b. If they are not `boarded`, they need 2 actions (`board` and `depart`). Their origin is added to the set of required origins `O`, their destination to `D`. Their origin is also added to the set of active floors `A`.
    3. Calculate the number of distinct floors that still need to be visited as the union of `O` and `D`.
    4. The minimum number of move actions is exactly `max(0, len(O | D) - 1)` because moving to any floor costs 1 action.
    5. If the lift is currently NOT at an active floor (a floor where it can immediately board or depart someone), it must make an additional move to reach an active floor. We add 1 to the move count in this case to break plateaus and provide a strict gradient.
    6. Return the sum of required passenger actions and move actions.
    """

    def __init__(self, task):
        self.goals = task.goals
        
        # Identify which passengers need to be served to reach the goal.
        self.passengers = set()
        for goal in self.goals:
            parts = goal[1:-1].split()
            if parts[0] == "served":
                self.passengers.add(parts[1])
                
        # Extract destination floor for each passenger.
        # Depending on the parser, destin could be in static or initial_state.
        self.destin = {}
        for fact in task.static | task.initial_state:
            parts = fact[1:-1].split()
            if parts[0] == "destin":
                self.destin[parts[1]] = parts[2]

    def __call__(self, node):
        boarded = set()
        served = set()
        lift_at = None
        origins = {}
        
        # Extract relevant information from the current state
        for fact in node.state:
            parts = fact[1:-1].split()
            pred = parts[0]
            if pred == "boarded":
                boarded.add(parts[1])
            elif pred == "served":
                served.add(parts[1])
            elif pred == "lift-at":
                lift_at = parts[1]
            elif pred == "origin":
                origins[parts[1]] = parts[2]
                
        O = set()  # Origins of waiting passengers
        D = set()  # Destinations of all unserved passengers
        A = set()  # Active floors (where a passenger can immediately board or depart)
        total_actions = 0
        
        for p in self.passengers:
            if p in served:
                continue
            
            if p in boarded:
                dest = self.destin.get(p)
                if dest:
                    D.add(dest)
                    A.add(dest)
                total_actions += 1  # 1 depart action needed
            else:
                orig = origins.get(p)
                dest = self.destin.get(p)
                if orig:
                    O.add(orig)
                    A.add(orig)
                if dest:
                    D.add(dest)
                total_actions += 2  # 1 board and 1 depart action needed
                
        # Determine the number of unique floors that must be visited
        OD = O | D
        moves = max(0, len(OD) - 1)
        
        # If the lift is not currently at a floor where it can perform a helpful action,
        # it will cost 1 extra move just to reach the first useful floor.
        if A and lift_at not in A:
            moves += 1
            
        return total_actions + moves
