from heuristics.heuristic_base import Heuristic

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the miconic domain.
    
    # Summary
    This heuristic estimates the minimum number of actions required to transport all goal passengers 
    to their destinations. It calculates the exact number of required `board` and `depart` actions, 
    and estimates the number of elevator `move` actions by looking at the set of unique floors that 
    still need to be visited.
    
    # Assumptions
    - The elevator has unlimited capacity, meaning multiple passengers can be boarded at once.
    - The elevator can move directly between any two floors since the `above` relation forms a fully 
      connected valid progression. Therefore, each distinct floor can be reached in 1 action.
    - Passengers can only depart at their specific destination.
    - All goals are of the form `(served ?p)` for passengers.
    
    # Heuristic Initialization
    - Identify the set of passengers that need to be served by parsing the `goals` conditions.
    - Extract the destinations for all passengers from the static facts (`destin` predicate) 
      and store them in a dictionary for O(1) lookups during search.
      
    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find which passengers are already `served`, which are currently 
       `boarded`, their starting `origins`, and the current floor of the elevator (`lift-at`).
    2. For each unserved goal passenger:
       - If they are already boarded, they require only 1 action to complete their journey (`depart`). 
         Their destination floor is added to a global set of required floors (`global_floors`).
       - If they are unboarded, they require 2 actions (`board` and `depart`). Both their origin 
         and destination floors are added to `global_floors`.
    3. Calculate the number of elevator move actions:
       - Since the elevator can move to any required floor directly, the minimum number of moves 
         to visit a set of N distinct required floors is exactly N.
       - However, if the elevator is already located at one of those required floors, it saves one 
         initial move, reducing the number of move actions to N - 1.
    4. The total estimated cost to reach the goal is the sum of the required `board`/`depart` actions 
       and the estimated minimum move actions.
    5. If there are no unserved passengers (i.e., `global_floors` is empty), the heuristic correctly 
       returns 0.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.goal_passengers = set()
        
        # Extract all target passengers from the goal state
        for goal in self.goals:
            parts = goal[1:-1].split()
            if parts[0] == "served":
                self.goal_passengers.add(parts[1])
                
        # Precompute passenger destinations from static facts
        self.destinations = {}
        for fact in task.static:
            parts = fact[1:-1].split()
            if parts[0] == "destin":
                self.destinations[parts[1]] = parts[2]

    def __call__(self, node):
        state = node.state
        
        served = set()
        boarded = set()
        origins = {}
        lift_at = None
        
        # Parse current state facts
        for fact in state:
            parts = fact[1:-1].split()
            pred = parts[0]
            if pred == "served":
                served.add(parts[1])
            elif pred == "boarded":
                boarded.add(parts[1])
            elif pred == "origin":
                origins[parts[1]] = parts[2]
            elif pred == "lift-at":
                lift_at = parts[1]
                
        global_floors = set()
        bd_actions = 0
        
        # Determine required floors and board/depart actions
        for p in self.goal_passengers:
            if p in served:
                continue
                
            # The destination floor must always be visited to serve the passenger
            global_floors.add(self.destinations.get(p))
            
            if p in boarded:
                # Passenger just needs to depart at destination
                bd_actions += 1
            else:
                # Passenger needs to be boarded at origin, then depart at destination
                bd_actions += 2
                if p in origins:
                    global_floors.add(origins[p])
                    
        # Remove None in case any missing destinations crept in
        global_floors.discard(None)

        # If there are no required floors to visit, goal is reached
        if not global_floors:
            return 0
            
        # Estimate move actions
        if lift_at in global_floors:
            moves = len(global_floors) - 1
        else:
            moves = len(global_floors)
            
        return bd_actions + moves
