from heuristics.heuristic_base import Heuristic

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the miconic domain.

    # Summary
    This heuristic estimates the minimum number of actions required to transport all unserved passengers 
    to their destinations. It exactly calculates the necessary `board` and `depart` actions and intelligently 
    estimates the minimum number of `up` or `down` moves required to visit all necessary floors, properly handling cycles.

    # Assumptions
    - Any floor can be reached from any other floor in exactly 1 move, as `up` and `down` use the transitivity of the `above` predicate.
    - The cost to move between any two distinct floors is exactly 1 action.
    - Passengers can be boarded and dropped off without capacity limits.
    - `destin` facts are static (or present in the initial state), while `origin`, `boarded`, and `served` are updated dynamically.

    # Heuristic Initialization
    - The `__init__` method extracts the set of passengers that need to be served from the goal conditions.
    - It parses `task.static` and `task.initial_state` to build a dictionary mapping each passenger to their destination floor.
    - It also optionally identifies if there is a final `lift-at` goal (though standard miconic goals are purely passenger-based).

    # Step-By-Step Thinking for Computing Heuristic
    1. Scan the current state to find the lift's current floor (`lift-at`), the origins of waiting passengers (`origin`), and which passengers are `boarded` or `served`.
    2. For each passenger that still needs to be served:
       - Add 1 to `departs_needed`. Add their destination floor to a set of needed floors `F`.
       - If they are not yet boarded:
         - Add 1 to `boards_needed`. Add their origin floor to `F`.
         - Add their destination floor to a subset `return_floors`. (This set represents floors we are forced to return to because a passenger needs to be dropped off there but hasn't even been picked up yet).
    3. If `F` is empty (and no other actions are needed), the estimated move cost is 0.
    4. Estimate the minimum number of moves to cover all floors in `F`:
       - Start with the assumption that visiting a set of `N` unique floors takes `N` moves.
       - If the lift is currently NOT at a floor in `F`:
         - If all floors in `F` are also in `return_floors` (which implies a cycle of dependencies where every target floor requires a revisit), it takes `N + 1` moves.
         - Otherwise, we need exactly `N` moves.
       - If the lift is currently AT a floor in `F` (`f_curr in F`):
         - If `f_curr` is NOT in `return_floors`, we can resolve whatever is needed at this floor right now and never return, saving 1 move (`N - 1`).
         - Otherwise, we will be forced to leave and come back, so we still need `N` moves.
    5. The total estimated cost is `boards_needed + departs_needed + estimated_moves`.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.passengers_to_serve = set()
        self.lift_goal = None
        
        # Extract goal targets
        for goal in self.goals:
            parts = goal[1:-1].split()
            if parts[0] == "served":
                self.passengers_to_serve.add(parts[1])
            elif parts[0] == "lift-at":
                self.lift_goal = parts[1]
                
        # Extract destination mappings which are static facts
        self.destinations = {}
        for fact in task.static | task.initial_state:
            parts = fact[1:-1].split()
            if parts[0] == "destin":
                self.destinations[parts[1]] = parts[2]

    def __call__(self, node):
        state = node.state
        
        f_curr = None
        origins = {}
        boarded = set()
        served = set()

        # Parse current state
        for fact in state:
            parts = fact[1:-1].split()
            pred = parts[0]
            if pred == "lift-at":
                f_curr = parts[1]
            elif pred == "origin":
                origins[parts[1]] = parts[2]
            elif pred == "boarded":
                boarded.add(parts[1])
            elif pred == "served":
                served.add(parts[1])
                
        F = set()
        return_floors = set()
        
        boards_needed = 0
        departs_needed = 0
        
        # Evaluate passengers that still need serving
        for p in self.passengers_to_serve:
            if p in served:
                continue
                
            departs_needed += 1
            dest = self.destinations.get(p)
            if dest:
                F.add(dest)
            
            # If passenger is waiting at an origin floor
            if p not in boarded:
                orig = origins.get(p)
                if orig:
                    F.add(orig)
                boards_needed += 1
                if dest:
                    return_floors.add(dest)

        # Handle a hypothetical explicit lift-at goal
        if self.lift_goal:
            if boards_needed > 0 or departs_needed > 0:
                F.add(self.lift_goal)
                return_floors.add(self.lift_goal)
            elif f_curr != self.lift_goal:
                F.add(self.lift_goal)

        # Base case: nothing left to visit
        if not F:
            return boards_needed + departs_needed

        # Estimate the number of moves needed to resolve all locations
        if f_curr is None or f_curr not in F:
            if len(return_floors) == len(F):
                moves = len(F) + 1
            else:
                moves = len(F)
        else:
            if f_curr not in return_floors:
                moves = len(F) - 1
            else:
                moves = len(F)

        return boards_needed + departs_needed + moves
