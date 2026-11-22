from heuristics.heuristic_base import Heuristic

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the miconic domain.

    # Summary
    This heuristic estimates the minimum number of actions required to serve all target passengers.
    It computes the exact number of `board` and `depart` actions needed for all unserved goal passengers,
    and estimates the number of elevator movements (`up` or `down`) required to visit all necessary floors.

    # Assumptions
    - Each unserved passenger waiting at a floor requires exactly one `board` action and one `depart` action.
    - Each boarded passenger requires exactly one `depart` action.
    - The elevator can move directly between any two floors in exactly 1 action (either `up` or `down`), regardless of the distance.
    - The number of moves is bounded below by the number of distinct floors that need to be visited.
    - If the elevator is already at a floor where an action (board or depart) can be performed immediately, it saves one initial move.
    - The elevator has infinite capacity, so multiple passengers can be transported simultaneously without returning.

    # Heuristic Initialization
    - Extract the destination floors for all passengers from the static facts (`destin` predicate) and store them in a dictionary.
    - Identify the goal passengers from the task's goals (`served` predicate).

    # Step-By-Step Thinking for Computing Heuristic
    1. Identify the current floor of the elevator from the state.
    2. Iterate over the state to find all target passengers who are still waiting (from `origin` facts) and those who are already boarded (from `boarded` facts).
    3. If there are no waiting or boarded target passengers, the goal is reached, so return 0.
    4. For each waiting passenger, add their origin and destination floors to a set of `stops`. Increment the action cost by 2 (one board, one depart).
    5. For each boarded passenger, add their destination floor to the set of `stops`. Increment the action cost by 1 (one depart).
    6. Check if the elevator's current floor is in `stops` AND if there is an immediately applicable action (i.e., a waiting passenger is at the current floor, or a boarded passenger's destination is the current floor).
    7. Calculate the move cost as the total number of unique floors in `stops`.
    8. If an immediate action is possible at the current floor, subtract 1 from the move cost.
    9. The final heuristic value is the sum of the required board/depart actions and the estimated move cost.
    """
    def __init__(self, task):
        self.destinations = {}
        self.target_passengers = set()
        
        # Parse static facts to extract passenger destinations
        for fact in task.static:
            parts = fact[1:-1].split()
            if parts[0] == "destin":
                self.destinations[parts[1]] = parts[2]
                
        # Parse goals to know which passengers need to be served
        for goal in task.goals:
            parts = goal[1:-1].split()
            if parts[0] == "served":
                self.target_passengers.add(parts[1])

    def __call__(self, node):
        state = node.state
        
        current_floor = None
        
        # First, find the current floor of the elevator
        for fact in state:
            if fact.startswith("(lift-at "):
                current_floor = fact[1:-1].split()[1]
                break
                
        stops = set()
        immediate_action = False
        action_cost = 0
        
        # Second, identify unserved passengers and accumulate required stops and action costs
        for fact in state:
            if fact.startswith("(origin "):
                parts = fact[1:-1].split()
                p, f = parts[1], parts[2]
                
                if p in self.target_passengers:
                    stops.add(f)
                    dest = self.destinations.get(p)
                    if dest:
                        stops.add(dest)
                    action_cost += 2
                    
                    # If we are currently at a floor with a waiting passenger, an immediate action (board) is possible
                    if f == current_floor:
                        immediate_action = True
                        
            elif fact.startswith("(boarded "):
                parts = fact[1:-1].split()
                p = parts[1]
                
                if p in self.target_passengers:
                    dest = self.destinations.get(p)
                    if dest:
                        stops.add(dest)
                        # If we are currently at the destination of a boarded passenger, an immediate action (depart) is possible
                        if dest == current_floor:
                            immediate_action = True
                    action_cost += 1
                    
        # If there are no actions required for target passengers, we are at a goal state
        if action_cost == 0:
            return 0
            
        move_cost = len(stops)
        
        # Subtract 1 move if the elevator is already at a stop and an immediate passenger action can be performed
        if immediate_action:
            move_cost -= 1
            
        # Ensure move_cost doesn't fall below zero 
        if move_cost < 0:
            move_cost = 0
            
        return action_cost + move_cost
