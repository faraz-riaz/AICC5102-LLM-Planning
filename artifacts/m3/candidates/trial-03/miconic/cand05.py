from heuristics.heuristic_base import Heuristic

def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Miconic domain.

    # Summary
    This heuristic estimates the minimum number of actions required to reach the goal state, 
    where all passengers have been transported to their destination floors and are `served`.

    # Assumptions
    - Each passenger requires exactly 1 `board` action and 1 `depart` action to be fully served.
    - If a passenger is already boarded, they only require the `depart` action.
    - The lift can travel directly between any two floors in exactly 1 action (using `up` or `down`).
    - The number of moving actions required is primarily bounded by the number of unique floors 
      that must be visited (either to pick up an unboarded passenger or drop off an unserved passenger).

    # Heuristic Initialization
    - Iterates through the goals to identify all passengers that need to be served.
    - Extracts static relationships, specifically the `destin` (destination) of each passenger.
    - Extracts the initial `origin` of each passenger from the task's initial state, since `origin` 
      is deleted when a passenger boards but represents their initial starting location.

    # Step-By-Step Thinking for Computing Heuristic
    1. Identify the Current State: 
       - Parse the state to find the current floor of the lift (`lift-at`), the set of passengers 
         that are currently in the lift (`boarded`), and the set of passengers that are already 
         at their destinations (`served`).
    2. Assess Passenger Needs:
       - For each passenger, check if they are `served`. If so, no actions are needed.
       - If they are not `served`, we need 1 `depart` action, and we add their destination floor 
         to our `floors_to_visit` set.
       - We also check if the passenger is `boarded`. If they are not `boarded`, we additionally 
         need 1 `board` action, and we add their origin floor to `floors_to_visit`.
    3. Estimate Moving Cost:
       - Since any floor can be reached from any other floor in 1 move, the number of required moves 
         is estimated by the number of unique floors in `floors_to_visit`.
       - If the lift is already at one of the required floors, we need one less move because we 
         can perform a `board` or `depart` action immediately before moving.
    4. Compute Final Value:
       - The heuristic value is the sum of required `board` actions, `depart` actions, and the 
         estimated number of `move` actions.
    """

    def __init__(self, task):
        """
        Initialize the heuristic by extracting:
        - Passengers that need to be served (from goals).
        - Destinations of all passengers (from static facts).
        - Origins of all passengers (from initial state).
        """
        self.passengers = []
        for goal in task.goals:
            parts = get_parts(goal)
            if parts and parts[0] == "served":
                self.passengers.append(parts[1])
                
        self.destinations = {}
        for fact in task.static:
            parts = get_parts(fact)
            if parts and parts[0] == "destin":
                self.destinations[parts[1]] = parts[2]
                
        self.origins = {}
        for fact in task.initial_state:
            parts = get_parts(fact)
            if parts and parts[0] == "origin":
                self.origins[parts[1]] = parts[2]

    def __call__(self, node):
        """Compute the estimated minimum cost to reach the goal state."""
        state = node.state
        
        boarded = set()
        served = set()
        current_floor = None
        
        # Single pass through the state to extract current fluents
        for fact in state:
            parts = get_parts(fact)
            if not parts:
                continue
            head = parts[0]
            if head == "served":
                served.add(parts[1])
            elif head == "boarded":
                boarded.add(parts[1])
            elif head == "lift-at":
                current_floor = parts[1]
                
        boards = 0
        departs = 0
        floors_to_visit = set()
        
        # Determine the unfulfilled needs of each passenger
        for p in self.passengers:
            if p in served:
                continue
                
            departs += 1
            dest = self.destinations.get(p)
            if dest:
                floors_to_visit.add(dest)
                
            if p not in boarded:
                boards += 1
                origin = self.origins.get(p)
                if origin:
                    floors_to_visit.add(origin)
                
        # If no floors need visiting, the goal state is achieved
        if not floors_to_visit:
            return 0
            
        # Estimate the number of moves needed to visit all required floors
        moves = len(floors_to_visit)
        if current_floor in floors_to_visit:
            moves -= 1
            
        return boards + departs + moves
