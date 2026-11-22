from heuristics.heuristic_base import Heuristic

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the miconic domain.
    
    # Summary
    This heuristic estimates the minimum number of actions required to serve all passengers specified in the goal. It calculates the necessary boarding, departing, and lift moving actions based on the current state.

    # Assumptions
    - The elevator has infinite capacity and can carry any number of passengers at once.
    - Moving between any two connected floors takes exactly 1 action (either `up` or `down`), as the `above` predicate typically creates a fully connected total order.
    - Multiple passengers can board or depart at the same floor simultaneously (each takes 1 action) without requiring the elevator to move.

    # Heuristic Initialization
    - Extract the goal state to identify which passengers need to be served.
    - Extract static facts to map each passenger to their destination floor, making lookups efficient during state evaluation.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to identify the elevator's current location (`lift-at`).
    2. Identify the status of all passengers that need to be served:
       - Unboarded passengers (have an `origin` in the current state).
       - Boarded passengers (have a `boarded` predicate in the current state).
    3. Calculate necessary passenger actions:
       - Each unboarded passenger needs 1 `board` and 1 `depart` action (2 actions in total).
       - Each boarded passenger needs 1 `depart` action (1 action in total).
    4. Calculate necessary lift movement actions:
       - Collect the set of all unique floors that must be visited. This includes the origins of all unboarded passengers and the destinations of all unboarded and boarded passengers.
       - The minimum number of lift moves to visit a set of N floors is N if the lift is not currently at one of those floors, and N - 1 if the lift is already at one of those floors.
    5. Sum the passenger actions and the minimum lift movement actions to get the final heuristic value.
    """

    def __init__(self, task):
        """Initialize the heuristic by extracting goal conditions and static facts."""
        self.goals = set()
        for fact in task.goals:
            parts = fact[1:-1].split()
            if parts[0] == "served":
                self.goals.add(parts[1])
                
        self.destinations = {}
        for fact in task.static:
            parts = fact[1:-1].split()
            if parts[0] == "destin":
                self.destinations[parts[1]] = parts[2]

    def __call__(self, node):
        """Estimate the minimum cost to serve all targeted passengers from the current state."""
        state = node.state
        
        unboarded_target = {}
        boarded_target = set()
        lift_at = None
        
        # Parse the current state
        for fact in state:
            parts = fact[1:-1].split()
            pred = parts[0]
            if pred == "origin":
                if parts[1] in self.goals:
                    unboarded_target[parts[1]] = parts[2]
            elif pred == "boarded":
                if parts[1] in self.goals:
                    boarded_target.add(parts[1])
            elif pred == "lift-at":
                lift_at = parts[1]
                
        # Count minimum boarding and departing actions
        boards = len(unboarded_target)
        departs = len(unboarded_target) + len(boarded_target)
        
        # Determine the set of unique floors that must be visited
        floors_to_visit = set()
        for p, orig_f in unboarded_target.items():
            floors_to_visit.add(orig_f)
            floors_to_visit.add(self.destinations[p])
            
        for p in boarded_target:
            floors_to_visit.add(self.destinations[p])
            
        # Estimate the minimum number of lift movement actions required
        if not floors_to_visit:
            moves = 0
        else:
            if lift_at in floors_to_visit:
                moves = len(floors_to_visit) - 1
            else:
                moves = len(floors_to_visit)
                
        # Return the estimated total cost to the goal state
        return boards + departs + moves
