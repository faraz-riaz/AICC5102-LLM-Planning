from heuristics.heuristic_base import Heuristic

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the miconic domain.

    # Summary
    This heuristic estimates the minimum number of actions required to serve all target passengers. 
    It accurately accounts for board and depart actions, and estimates the number of movement actions 
    based on the distinct floors that still need to be visited.

    # Assumptions
    - The elevator has infinite capacity.
    - Any floor can be reached from any other floor in a single action if it's in the correct direction. 
      This is true due to the complete transitivity of the `above` predicate in this domain.
    - The minimum number of movement actions is tightly bounded by the number of unique unvisited floors 
      that must be stopped at.

    # Heuristic Initialization
    - Extract all goal passengers (those that need to be `served`) and the optional goal floor (`lift-at`).
    - Extract the static `destin` facts from the task to know the destination floor of each passenger.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to identify the elevator's current floor (`lift-at`), boarded passengers, 
       served passengers, and the origins of unboarded passengers.
    2. Initialize an action counter (`actions = 0`) and a set of distinct floors to visit (`stops_to_make`).
    3. Determine if the current floor is "useful now". A floor is useful now if we can immediately 
       perform a required `board` or `depart` action for an unserved passenger without moving.
    4. For each passenger that needs to be served:
       - If they are already boarded, add 1 to the action count (for `depart`), and add their destination 
         to `stops_to_make`. If their destination is the current floor, set `useful_now = True`.
       - If they are not boarded, add 2 to the action count (for `board` and `depart`), and add both their 
         origin and destination to `stops_to_make`. If their origin is the current floor, set `useful_now = True`.
    5. Calculate the movement cost:
       - If there are stops to make, add `len(stops_to_make)` to the action count.
       - If the current floor is "useful now", we can perform an action before moving, effectively saving 
         us one initial movement action. Subtract 1 from the movement cost.
    6. Return the total action count as the heuristic value.
    """

    def __init__(self, task):
        self.goals = task.goals
        
        self.destinations = {}
        # Ensure we catch 'destin' whether it's classified as static or in the initial state.
        for fact in task.static | task.initial_state:
            parts = fact[1:-1].split()
            if parts[0] == "destin":
                self.destinations[parts[1]] = parts[2]
                
        self.goal_passengers = set()
        self.goal_floor = None
        for goal in self.goals:
            parts = goal[1:-1].split()
            if parts[0] == "served":
                self.goal_passengers.add(parts[1])
            elif parts[0] == "lift-at":
                self.goal_floor = parts[1]

    def __call__(self, node):
        state = node.state

        boarded = set()
        origins = {}
        lift_at = None
        served = set()

        for fact in state:
            parts = fact[1:-1].split()
            predicate = parts[0]
            if predicate == "boarded":
                boarded.add(parts[1])
            elif predicate == "origin":
                origins[parts[1]] = parts[2]
            elif predicate == "lift-at":
                lift_at = parts[1]
            elif predicate == "served":
                served.add(parts[1])

        actions = 0
        stops_to_make = set()
        useful_now = False

        for p in self.goal_passengers:
            if p in served:
                continue
            
            dest_floor = self.destinations.get(p)
            
            if p in boarded:
                actions += 1
                if dest_floor:
                    stops_to_make.add(dest_floor)
                    if dest_floor == lift_at:
                        useful_now = True
            else:
                actions += 2
                origin_floor = origins.get(p)
                if origin_floor:
                    stops_to_make.add(origin_floor)
                    if origin_floor == lift_at:
                        useful_now = True
                if dest_floor:
                    stops_to_make.add(dest_floor)

        if self.goal_floor:
            if self.goal_floor != lift_at:
                stops_to_make.add(self.goal_floor)
            elif len(stops_to_make) == 0:
                useful_now = True

        if stops_to_make:
            if useful_now:
                actions += len(stops_to_make) - 1
            else:
                actions += len(stops_to_make)

        return actions
