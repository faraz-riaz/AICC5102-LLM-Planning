from heuristics.heuristic_base import Heuristic

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the miconic domain.
    
    # Summary
    This heuristic accurately estimates the number of actions (board, depart, up, down) 
    required to serve all passengers. It tracks the exact number of passenger actions 
    remaining and calculates the minimum number of elevator movements required to visit 
    all the necessary floors.

    # Assumptions
    - The elevator has infinite capacity (it can carry any number of passengers at once).
    - Any floor can be reached from any other floor in 1 move due to the transitivity of 
      the `above` predicate, which is fully specified in the initial state.
    - The most efficient strategy picks up and drops off passengers optimally without 
      visiting unnecessary floors or making useless stops.

    # Heuristic Initialization
    - Parses the goal state to identify all passengers that must be served.
    - Extracts the destination floors for each passenger from the static facts.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find which passengers are boarded, which are already served, 
       the starting origins of unboarded passengers, and the current location of the elevator.
    2. Identify all passengers that still need to be served.
    3. For each unserved passenger, determine their state to compute remaining passenger actions:
       - If boarded: requires 1 action (depart). Add their destination to `F` (required floors) 
         and to `actionable` floors (since we can depart them immediately if we are at that floor).
       - If waiting (at origin): requires 2 actions (board, depart). Add their origin to `F` and 
         `actionable` (since we can board them there), and add their destination to `F`.
    4. Calculate movement cost based on required floor visits:
       - Every floor in `F` must be visited.
       - If the elevator is currently at an `actionable` floor, we can perform a useful passenger 
         action immediately without moving. The required number of remaining movements is `len(F) - 1`.
       - If the elevator is NOT at an `actionable` floor (either it's at an unneeded floor, or 
         at a destination floor of a passenger who hasn't been boarded yet), it must move to an 
         actionable floor first. The required number of movements is exactly `len(F)`.
    5. The final heuristic value is the sum of the passenger action costs and the movement cost.
    """

    def __init__(self, task):
        # Extract passengers that need to be served from the goal conditions.
        self.passengers = []
        for goal in task.goals:
            parts = goal[1:-1].split()
            if parts[0] == 'served':
                self.passengers.append(parts[1])
                
        # Extract destinations for all passengers from the static facts.
        self.destin = {}
        for fact in task.static:
            parts = fact[1:-1].split()
            if parts[0] == 'destin':
                self.destin[parts[1]] = parts[2]

    def __call__(self, node):
        state = node.state
        
        boarded = set()
        served = set()
        origin = {}
        lift_at = None
        
        # Parse the current state facts
        for fact in state:
            parts = fact[1:-1].split()
            if parts[0] == 'boarded':
                boarded.add(parts[1])
            elif parts[0] == 'served':
                served.add(parts[1])
            elif parts[0] == 'origin':
                origin[parts[1]] = parts[2]
            elif parts[0] == 'lift-at':
                lift_at = parts[1]
                
        cost = 0
        F = set()          # The set of all floors that must be visited
        actionable = set() # The set of floors where an action can be performed IMMEDIATELY
        
        # Calculate passenger action costs and populate required floors
        for p in self.passengers:
            if p in served:
                continue
            
            if p in boarded:
                cost += 1  # 1 action required: depart
                dest = self.destin.get(p)
                if dest:
                    F.add(dest)
                    actionable.add(dest)
            else:
                cost += 2  # 2 actions required: board and depart
                orig = origin.get(p)
                dest = self.destin.get(p)
                if orig:
                    F.add(orig)
                    actionable.add(orig)
                if dest:
                    F.add(dest)
                    
        # Add the cost of moving the elevator between the required floors
        if F:
            if lift_at in actionable:
                # If we are currently at an actionable floor, we can check it off without moving.
                cost += len(F) - 1
            else:
                # If we are not at an actionable floor, we must move to one, meaning we 
                # will traverse all len(F) legs.
                cost += len(F)
                
        return cost
