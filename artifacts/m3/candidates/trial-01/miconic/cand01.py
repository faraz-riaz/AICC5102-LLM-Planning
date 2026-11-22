from heuristics.heuristic_base import Heuristic

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the miconic domain.
    
    # Summary
    This heuristic estimates the number of actions required to serve all goal passengers. 
    It computes the number of `board` and `depart` actions needed for each unserved 
    passenger, and estimates the minimum number of movement actions (`up` or `down`) 
    needed to visit all the required origin and destination floors.
    
    # Assumptions
    - The goal is to serve a specific set of passengers, indicated by `(served ?p)`.
    - Passengers are served by boarding at their origin and departing at their destination.
    - An elevator can carry any number of passengers simultaneously.
    - Movement between any two floors requires exactly one action (due to the transitive 
      nature of the `above` predicate in this domain).
    - The relaxed plan length (ignoring the deletion of `lift-at` facts) provides a 
      highly accurate and efficient estimate for the number of required moves, which is 
      exactly the number of distinct floors that need to be visited, minus one if the 
      elevator is already at one of those floors.
    
    # Heuristic Initialization
    - Extract the set of goal passengers from the task's goals.
    - Extract the destination floor for each passenger from the static facts and the 
      initial state, storing it in a dictionary for fast lookup.
    
    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find the elevator's current floor (`lift-at`).
    2. Identify the status of all passengers: which ones are currently waiting (have an 
       `origin` fact), which are in the elevator (`boarded`), and which are `served`.
    3. Initialize counters for the number of required `board` and `depart` actions, and 
       a set `V` to collect all floors that must be visited.
    4. For each goal passenger that is not yet served:
       - If they are boarded, increment the `depart` count and add their destination 
         floor to `V`.
       - If they are waiting, increment both `board` and `depart` counts, and add both 
         their origin and destination floors to `V`.
    5. Calculate the required number of movement actions as the size of `V`. If the 
       elevator's current floor is already in `V`, subtract 1 from the movement count.
    6. The final heuristic value is the sum of required `board` actions, `depart` actions, 
       and movement actions.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.goal_passengers = set()
        
        # Extract passengers that need to be served from the goals
        for goal in self.goals:
            parts = goal[1:-1].split()
            if parts[0] == 'served':
                self.goal_passengers.add(parts[1])
                
        # Extract destination floors for each passenger
        # The 'destin' predicate is never deleted, so it's guaranteed to be 
        # in either the initial_state or the static facts.
        self.destinations = {}
        for fact in task.initial_state | task.static:
            parts = fact[1:-1].split()
            if parts[0] == 'destin':
                passenger = parts[1]
                floor = parts[2]
                self.destinations[passenger] = floor

    def __call__(self, node):
        state = node.state
        
        f_curr = None
        waiting_origins = {}
        boarded_passengers = set()
        served_passengers = set()
        
        # Parse current state dynamically
        for fact in state:
            parts = fact[1:-1].split()
            if parts[0] == 'lift-at':
                f_curr = parts[1]
            elif parts[0] == 'origin':
                waiting_origins[parts[1]] = parts[2]
            elif parts[0] == 'boarded':
                boarded_passengers.add(parts[1])
            elif parts[0] == 'served':
                served_passengers.add(parts[1])
                
        boards = 0
        departs = 0
        V = set()
        
        # Evaluate required actions and floors to visit for each goal passenger
        for p in self.goal_passengers:
            if p in served_passengers:
                # Passenger already served, no further actions needed.
                continue
            
            if p in boarded_passengers:
                # Needs to depart at destination
                departs += 1
                if p in self.destinations:
                    V.add(self.destinations[p])
            elif p in waiting_origins:
                # Needs to board at origin and depart at destination
                boards += 1
                departs += 1
                V.add(waiting_origins[p])
                if p in self.destinations:
                    V.add(self.destinations[p])
                    
        # Calculate moves based on distinct floors to visit
        moves = len(V)
        if f_curr in V:
            moves -= 1
            
        # Total cost is the sum of logical operations plus physical moves
        total_actions = boards + departs + max(0, moves)
        
        return total_actions
