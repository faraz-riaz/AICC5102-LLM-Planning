from heuristics.heuristic_base import Heuristic

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Miconic domain.
    
    # Summary
    This heuristic estimates the minimum number of actions required to serve all passengers.
    It computes the exact number of `board` and `depart` actions needed for each passenger,
    and estimates the number of elevator move actions by counting the unique floors that
    must still be visited. It closely matches the optimal relaxed plan length but
    improves upon it by avoiding plateaus, providing a strictly monotonic gradient toward the goal.
    
    # Assumptions
    - Each passenger needs exactly one `board` and one `depart` action, except those already boarded who only need `depart`.
    - The elevator can travel directly between any two floors in exactly 1 step (because the `above` relation in Miconic defines a fully connected, complete order of floors).
    - Passengers who are not yet boarded must have their origin floor visited.
    - Passengers who are waiting or boarded must have their destination floor visited.
    
    # Heuristic Initialization
    - Extract the destination floor for each passenger from the static facts (and initial state), as this never changes during the plan.
    
    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to identify the elevator's current floor (`lift-at`), the set of waiting passengers (`origin`), and the set of boarded passengers (`boarded`).
    2. Count passenger actions: 2 actions for each waiting passenger and 1 action for each boarded passenger.
    3. Identify the set of unique floors that must be visited (`U`). This is the union of the origins of all waiting passengers and the destinations of all waiting and boarded passengers.
    4. Identify the set of "currently actionable" floors (`S`). These are floors where a valid passenger action (`board` or `depart`) can be performed immediately (i.e., origins of waiting passengers and destinations of currently boarded passengers).
    5. Estimate elevator moves:
       - If there are no floors to visit (`U` is empty), 0 moves are needed.
       - If the elevator is currently at a floor in `S`, it can immediately perform a useful action. Thus, it needs at least `|U| - 1` moves to visit the remaining floors.
       - If the elevator is not at a floor in `S`, it cannot perform a useful action here and must first move to a floor in `S`. This initial move does not reduce the number of required unique floor visits, so it needs at least `|U|` moves.
    6. Return the sum of passenger actions and estimated elevator moves.
    """

    def __init__(self, task):
        self.goals = task.goals
        
        # Extract destination for each passenger (static information)
        self.destin = {}
        for fact in task.static | task.initial_state:
            parts = fact[1:-1].split()
            if parts[0] == "destin":
                self.destin[parts[1]] = parts[2]
                
    def __call__(self, node):
        state = node.state
        
        lift_at = None
        P_wait = set()
        F_origins = set()
        P_board = set()
        
        # Parse state
        for fact in state:
            parts = fact[1:-1].split()
            if parts[0] == "lift-at":
                lift_at = parts[1]
            elif parts[0] == "origin":
                P_wait.add(parts[1])
                F_origins.add(parts[2])
            elif parts[0] == "boarded":
                P_board.add(parts[1])
                
        P_unserved = P_wait | P_board
        
        # If no unserved passengers remain, we are at the goal
        if not P_unserved:
            return 0
            
        F_destins = {self.destin[p] for p in P_unserved}
        
        # U is the set of all unique floors that must be visited
        U = F_origins | F_destins
        
        # S is the set of floors where we can immediately do a useful action
        S = F_origins | {self.destin[p] for p in P_board}
        
        # Number of passenger actions required
        actions = 2 * len(P_wait) + len(P_board)
        
        # Number of elevator moves required
        if len(U) > 0:
            if lift_at in S:
                moves = len(U) - 1
            else:
                moves = len(U)
        else:
            moves = 0
            
        return actions + moves
