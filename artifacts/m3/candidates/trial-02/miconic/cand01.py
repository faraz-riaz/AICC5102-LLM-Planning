from heuristics.heuristic_base import Heuristic

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the miconic domain.

    # Summary
    This heuristic estimates the minimum number of actions required to serve all remaining
    passengers. It computes the necessary board and depart actions, and approximates the
    number of elevator movements needed to visit all required pickup and dropoff floors.

    # Assumptions
    - The elevator can travel directly between any two floors (since `above` facts are transitively closed).
    - Unserved passengers are either waiting at their origin (unboarded) or currently in the elevator (boarded).
    - Served passengers require no further actions and do not have `origin` or `boarded` facts in the state.
    - An unboarded passenger requires at least 2 passenger actions (board, depart).
    - A boarded passenger requires at least 1 passenger action (depart).
    - Moving the elevator between floors costs 1 action per unique unvisited destination or origin floor.

    # Heuristic Initialization
    - Parses the static facts to map each passenger to their respective destination floor.
    - This map is stored in `self.destinations` for O(1) lookup during state evaluation.

    # Step-By-Step Thinking for Computing Heuristic
    1. Iterate over all facts in the current state to identify:
       - `unboarded_origins`: the set of floors where passengers are currently waiting.
       - `boarded_passengers`: the set of passengers currently inside the elevator.
       - `current_floor`: the current location of the elevator from the `lift-at` fact.
    2. Compute the `unserved_destinations` set, which contains the destination floors
       for both waiting and boarded passengers.
    3. Calculate the `action_cost`:
       - Add 2 for every waiting passenger (1 for board + 1 for depart).
       - Add 1 for every boarded passenger (1 for depart).
       - If `action_cost` is 0, return 0 (all passengers are served, goal state reached).
    4. Determine the number of `moves` required:
       - Combine `unboarded_origins` and `unserved_destinations` into a set `floors_to_visit`.
       - The base movement cost is the number of unique floors in `floors_to_visit`.
       - If the `current_floor` is in `unboarded_origins` (can board someone now) or in the 
         destinations of currently *boarded* passengers (can drop someone off now), subtract 1 
         from `moves` because the elevator is already positioned to make progress.
    5. The final heuristic value is the sum of `action_cost` and `moves`.
    """

    def __init__(self, task):
        self.destinations = {}
        for fact in task.static:
            if fact.startswith("(destin "):
                parts = fact[1:-1].split()
                if len(parts) >= 3:
                    passenger = parts[1]
                    floor = parts[2]
                    self.destinations[passenger] = floor

    def __call__(self, node):
        state = node.state
        
        unboarded_origins = set()
        boarded_passengers = set()
        unserved_destinations = set()
        current_floor = None
        
        num_unboarded = 0
        num_boarded = 0

        for fact in state:
            if fact.startswith("(origin "):
                parts = fact[1:-1].split()
                p = parts[1]
                f = parts[2]
                unboarded_origins.add(f)
                if p in self.destinations:
                    unserved_destinations.add(self.destinations[p])
                num_unboarded += 1
            elif fact.startswith("(boarded "):
                parts = fact[1:-1].split()
                p = parts[1]
                boarded_passengers.add(p)
                if p in self.destinations:
                    unserved_destinations.add(self.destinations[p])
                num_boarded += 1
            elif fact.startswith("(lift-at "):
                parts = fact[1:-1].split()
                current_floor = parts[1]

        # Action cost mapping exactly to necessary board/depart operations
        action_cost = 2 * num_unboarded + 1 * num_boarded
        
        # If no passenger actions are needed, we are in a goal state
        if action_cost == 0:
            return 0
            
        # Determine movement requirements
        boarded_destinations = {self.destinations[p] for p in boarded_passengers if p in self.destinations}
        floors_to_visit = unboarded_origins | unserved_destinations
        
        moves = len(floors_to_visit)
        
        # Discount a move if we are exactly at an actionable active floor
        if current_floor in unboarded_origins or current_floor in boarded_destinations:
            moves -= 1
            
        return action_cost + moves
