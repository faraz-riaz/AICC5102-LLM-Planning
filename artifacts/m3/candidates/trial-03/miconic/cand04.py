from heuristics.heuristic_base import Heuristic

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the miconic (elevator) domain.
    
    # Summary
    This heuristic estimates the total cost (in number of actions) to serve all remaining passengers. 
    It accurately accounts for both the necessary `board` and `depart` actions for each unserved passenger, 
    as well as the minimum number of lift movements required to visit all necessary pick-up and drop-off floors.

    # Assumptions
    - The goal is to serve a specific set of passengers, which involves picking them up from their origin floor 
      and dropping them off at their destination floor.
    - `board` and `depart` actions take exactly 1 step each.
    - Because the elevator can move directly from any floor to any other floor using the `up` and `down` actions 
      (as long as they are transitively ordered by the `above` predicate), transitioning between any two floors 
      requires exactly 1 action.
    - Therefore, the number of move actions is strongly bounded by the number of unique floors that still need 
      to be visited.

    # Heuristic Initialization
    - Extract the list of passengers that must be `served` from the goal conditions.
    - Extract the destination floors for each passenger from the static facts (`destin` predicate) and store 
      them in a dictionary mapping passenger to destination floor.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find the current position of the lift (`lift-at`), the set of passengers 
       currently in the lift (`boarded`), the set of passengers already delivered (`served`), and the waiting 
       locations of unboarded passengers (`origin`).
    2. Identify the set of floors that must be visited (`all_needed`):
       - For every unserved goal passenger, their destination floor must be visited.
       - If the passenger is not yet boarded, their origin floor must also be visited.
    3. Identify the subset of floors where an action can be performed *immediately* (`active`):
       - Origin floors of unboarded passengers (where a `board` action can be applied right away).
       - Destination floors of already boarded passengers (where a `depart` action can be applied right away).
    4. Calculate the required number of passenger actions:
       - 2 actions (`board` + `depart`) for every unboarded passenger.
       - 1 action (`depart`) for every boarded passenger.
    5. Estimate the required number of lift movements:
       - If no floors need to be visited, 0 moves are needed.
       - Otherwise, we need at least `len(all_needed)` moves to visit all distinct locations.
       - However, if the lift is currently at a floor in the `active` set, we do not need a move action 
         to perform the immediate next task at that floor, so we subtract 1 from the moves estimate.
    6. The total estimated cost is the sum of the required passenger actions and the required lift movements. 
       This provides an extremely smooth gradient for greedy best-first search with virtually no plateaus.
    """

    def __init__(self, task):
        # Extract the passengers that need to be served to achieve the goal.
        self.goal_passengers = set()
        for goal in task.goals:
            parts = goal[1:-1].split()
            if parts[0] == "served":
                self.goal_passengers.add(parts[1])
                
        # Extract static destinations for all goal passengers.
        self.destinations = {}
        for fact in task.static:
            parts = fact[1:-1].split()
            if parts[0] == "destin":
                if parts[1] in self.goal_passengers:
                    self.destinations[parts[1]] = parts[2]
                    
    def __call__(self, node):
        state = node.state
        
        lift_at = None
        boarded = set()
        served = set()
        origins = {}
        
        # Parse the dynamic facts from the current state.
        for fact in state:
            parts = fact[1:-1].split()
            if parts[0] == "lift-at":
                lift_at = parts[1]
            elif parts[0] == "boarded":
                boarded.add(parts[1])
            elif parts[0] == "served":
                served.add(parts[1])
            elif parts[0] == "origin":
                origins[parts[1]] = parts[2]
                
        all_needed = set()
        active = set()
        actions = 0
        
        # Process each goal passenger to accumulate required actions and floor visits.
        for p in self.goal_passengers:
            # If the passenger is already successfully served, no more actions/visits are needed for them.
            if p in served:
                continue
                
            dest = self.destinations.get(p)
            if dest:
                all_needed.add(dest)
                
                if p in boarded:
                    # Passenger is in the elevator. Only 1 action (depart) remains.
                    actions += 1
                    # We can immediately perform the depart action if we move to their destination.
                    active.add(dest)
                else:
                    # Passenger is waiting. 2 actions (board + depart) remain.
                    actions += 2
                    orig = origins.get(p)
                    if orig:
                        all_needed.add(orig)
                        # We can immediately perform the board action if we move to their origin.
                        active.add(orig)
                        
        # If all passengers are served, the goal is reached (0 cost).
        if not all_needed:
            return 0
            
        # The number of moves is bounded by the distinct number of floors we still have to visit.
        moves = len(all_needed)
        
        # If the elevator is currently located at a floor where an action can be immediately applied, 
        # we save 1 initial move.
        if lift_at in active:
            moves -= 1
            
        return actions + moves
