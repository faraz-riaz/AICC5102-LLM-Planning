from heuristics.heuristic_base import Heuristic

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the miconic domain.
    
    # Summary
    This heuristic estimates the number of actions required to serve all passengers.
    It computes an independent cost for each unserved passenger, assuming no shared trips,
    which provides a very strong and smooth gradient for Greedy Best-First Search (GBFS).

    # Assumptions
    - Each passenger needs to be boarded at their origin and departed at their destination.
    - Moving the lift between any two floors requires exactly 1 action (due to the fully connected `above` relation in miconic, meaning we can always reach any floor directly).
    - Passengers do not share rides in the heuristic calculation (this overestimates the cost but eliminates plateaus and provides an excellent search direction).

    # Heuristic Initialization
    - Extracts the set of goal passengers that need to be served.
    - Extracts the `destin` mappings for each passenger from the static or initial facts.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find the lift's current floor, boarded passengers, served passengers, and unboarded passengers' origins.
    2. Initialize `total_cost` to 0.
    3. Loop over all passengers in the goals:
       - If the passenger is already `served`, they add 0 to the cost.
       - If the passenger is `boarded`, they require 1 `depart` action. If the lift is not currently at their destination, they also require 1 `move` action.
       - If the passenger is not boarded and not served, they require 2 actions (`board` and `depart`). 
         - If the lift is not currently at their origin, add 1 `move` action to get to the origin.
         - If their origin is different from their destination, add 1 `move` action to get to the destination.
    4. Return `total_cost`. This value decreases exactly when progress is made (moving to a correct floor, boarding, or departing), successfully avoiding plateaus.
    """

    def __init__(self, task):
        # Extract passengers that are required to be served from the goals
        self.goal_passengers = set()
        for goal in task.goals:
            parts = goal[1:-1].split()
            if parts[0] == "served":
                self.goal_passengers.add(parts[1])

        # Extract passenger destinations.
        # They could be classified as static facts or remain in the initial state.
        self.destin = {}
        for fact in task.static | task.initial_state:
            if fact.startswith("(destin "):
                parts = fact[1:-1].split()
                self.destin[parts[1]] = parts[2]

    def __call__(self, node):
        state = node.state
        
        # Parse the current state in a single pass for efficiency
        lift_at = None
        boarded = set()
        served = set()
        origin = {}
        
        for fact in state:
            if fact.startswith("(lift-at "):
                lift_at = fact[1:-1].split()[1]
            elif fact.startswith("(boarded "):
                boarded.add(fact[1:-1].split()[1])
            elif fact.startswith("(served "):
                served.add(fact[1:-1].split()[1])
            elif fact.startswith("(origin "):
                parts = fact[1:-1].split()
                origin[parts[1]] = parts[2]
                
        total_cost = 0
        
        for p in self.goal_passengers:
            if p in served:
                # Goal reached for this passenger, no further actions needed
                continue
            
            if p in boarded:
                # Needs to be departed at destination
                total_cost += 1 
                
                # Check if movement is needed
                if lift_at != self.destin.get(p):
                    total_cost += 1
            else:
                # Needs to be boarded and departed
                total_cost += 2 
                
                origin_p = origin.get(p)
                destin_p = self.destin.get(p)
                
                if origin_p is not None:
                    # Check if movement to origin is needed
                    if lift_at != origin_p:
                        total_cost += 1
                    
                    # Check if movement from origin to destination is needed
                    if origin_p != destin_p:
                        total_cost += 1
                else:
                    # Fallback behavior if origin fact is somehow missing
                    if lift_at != destin_p:
                        total_cost += 1
                        
        return total_cost
