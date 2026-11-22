from fnmatch import fnmatch
from heuristics.heuristic_base import Heuristic

def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the miconic domain.

    # Summary
    This heuristic estimates the minimum number of remaining actions to reach the goal.
    It calculates the exact required `board` and `depart` actions for all unserved passengers,
    and accurately estimates the number of elevator move operations needed by tracking the 
    set of distinct floors that must be visited.

    # Assumptions
    - An unserved passenger who hasn't boarded needs exactly 2 actions (board + depart).
    - An unserved passenger who has boarded needs exactly 1 action (depart).
    - Because the elevator can skip floors (i.e., move directly between any two floors as 
      long as the direction matches the `above` total order constraint), visiting any new 
      required floor costs exactly 1 move action.
    - We divide the required floors into "ready" floors (where a useful action like boarding 
      or departing can be performed immediately) and "unready" floors (which must be visited 
      eventually, but are not yet actionable). This distinction helps smoothly break ties and 
      penalize moving to a destination before picking up the corresponding passenger.

    # Heuristic Initialization
    - Parses the static facts to create a mapping from each passenger to their destination floor.
    
    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to identify unserved passengers, separating them into boarded and unboarded.
    2. Count pure action costs: 2 for each unboarded passenger, 1 for each boarded passenger.
    3. Identify the set of "Ready" floors where an action can immediately occur:
       - Origins of unboarded passengers.
       - Destinations of boarded passengers.
    4. Identify "Unready" floors that must be visited eventually but aren't ready yet:
       - Destinations of unboarded passengers.
    5. The total set of unique floors to visit `V` is the union of Ready and Unready floors.
    6. Estimate move actions: 
       - Base moves required is `len(V)`.
       - If the elevator is already at a `Ready` floor, it can perform an action without moving first, 
         so we subtract 1 from the move cost.
    7. The total heuristic value is the sum of the passenger action costs and the estimated move actions.
    """

    def __init__(self, task):
        """
        Initialize the heuristic by extracting the static destination facts.
        """
        self.destinations = {}
        for fact in task.static:
            if fact.startswith('(destin '):
                parts = get_parts(fact)
                # parts[1] is passenger, parts[2] is destination floor
                self.destinations[parts[1]] = parts[2]

    def __call__(self, node):
        """
        Compute the estimated cost to reach the goal from the current state.
        """
        state = node.state
        
        unserved_not_boarded_count = 0
        boarded_passengers_count = 0
        current_floor = None
        
        ready_floors = set()
        unready_floors = set()
        served_passengers = set()
        boarded_passengers = set()
        
        # 1. Parse current state for lift position and passenger statuses
        for fact in state:
            if fact.startswith('(origin '):
                unserved_not_boarded_count += 1
                parts = get_parts(fact)
                passenger, floor = parts[1], parts[2]
                ready_floors.add(floor)
            elif fact.startswith('(boarded '):
                boarded_passengers_count += 1
                parts = get_parts(fact)
                boarded_passengers.add(parts[1])
            elif fact.startswith('(served '):
                parts = get_parts(fact)
                served_passengers.add(parts[1])
            elif fact.startswith('(lift-at '):
                parts = get_parts(fact)
                current_floor = parts[1]
                
        # 2. Determine unready floors and additional ready floors based on passenger destinations
        for passenger, dest in self.destinations.items():
            if passenger not in served_passengers:
                if passenger in boarded_passengers:
                    # Passenger is boarded, their destination is now a ready floor
                    ready_floors.add(dest)
                else:
                    # Passenger is not yet boarded, their destination is needed eventually
                    unready_floors.add(dest)
                    
        # 3. Check for goal state (all passengers served)
        if unserved_not_boarded_count == 0 and boarded_passengers_count == 0 and len(served_passengers) == len(self.destinations):
            return 0
            
        # 4. Calculate move costs
        V = ready_floors.union(unready_floors)
        moves_required = len(V)
        
        # If the elevator is already at a floor where it can perform a useful action,
        # it saves one initial movement step.
        if current_floor in ready_floors:
            moves_required -= 1
            
        # 5. Compute the total heuristic estimate
        action_costs = (unserved_not_boarded_count * 2) + (boarded_passengers_count * 1)
        total_cost = action_costs + moves_required
        
        return total_cost
