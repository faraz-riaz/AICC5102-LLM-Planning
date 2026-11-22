from heuristics.heuristic_base import Heuristic

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Miconic domain.

    # Summary
    This heuristic estimates the minimum number of actions required to serve all remaining 
    passengers. It calculates the exact number of `board` and `depart` actions needed 
    for the unserved passengers, and provides a highly accurate estimate of the number 
    of elevator movements (`up` and `down` actions) by counting the unique floors that 
    still need to be visited.

    # Assumptions
    - Every passenger in the goal must be served.
    - Serving a passenger requires boarding them at their origin floor and departing them 
      at their destination floor.
    - An unboarded, unserved passenger requires exactly 2 actions (`board` and `depart`).
    - A boarded, unserved passenger requires exactly 1 action (`depart`).
    - The elevator can jump directly between any two floors as long as they are ordered, 
      meaning a continuous movement to a specific new floor can be modeled as 1 action 
      per floor stop.
    - The number of unique floors that must be visited serves as a strong, informative 
      baseline for the required number of movement actions.

    # Heuristic Initialization
    - Extract the list of passengers that need to be served from the goal state (`task.goals`).
    - Extract the destination floor of each passenger from the static facts or the initial 
      state (`task.static | task.initial_state`), since destinations never change during execution.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to determine:
       - The current floor of the elevator (`lift-at`).
       - The current locations (origins) of all unboarded passengers (`origin`).
       - The set of passengers who are currently in the elevator (`boarded`).
       - The set of passengers who have already been delivered (`served`).
    2. Iterate through each passenger that needs to be served. If they are already served, skip them.
    3. For each unserved passenger:
       - If they are boarded, add 1 to the action cost (for `depart`). Add their destination 
         floor to the set of floors to visit. Check if the elevator's current floor is their 
         destination; if so, an action can be performed immediately without moving.
       - If they are not boarded, add 2 to the action cost (for `board` and `depart`). Add both 
         their origin and destination floors to the set of floors to visit. Check if the elevator's 
         current floor is their origin; if so, an action can be performed immediately without moving.
    4. Estimate the movement cost:
       - The base movement cost is the total number of unique floors that need to be visited.
       - If the elevator is already at a floor where an action can immediately be taken (i.e., 
         picking up a waiting passenger or dropping off a boarded passenger), we save 1 movement action.
    5. Return the sum of the passenger action costs and the estimated movement cost.
    """

    def __init__(self, task):
        # Identify all passengers that need to be served from the goal conditions.
        self.passengers = set()
        for goal in task.goals:
            parts = goal[1:-1].split()
            if parts[0] == "served":
                self.passengers.add(parts[1])
                
        # Extract the destination floor of each passenger.
        # Destinations are static, so they will be in either task.static or task.initial_state.
        self.destin = {}
        for fact in task.static | task.initial_state:
            parts = fact[1:-1].split()
            if parts[0] == "destin":
                self.destin[parts[1]] = parts[2]
                
    def __call__(self, node):
        state = node.state
        
        # Single pass over the current state to efficiently extract current dynamic facts.
        current_locations = {}
        boarded = set()
        served = set()
        current_floor = None
        
        for fact in state:
            parts = fact[1:-1].split()
            if parts[0] == 'origin':
                current_locations[parts[1]] = parts[2]
            elif parts[0] == 'boarded':
                boarded.add(parts[1])
            elif parts[0] == 'served':
                served.add(parts[1])
            elif parts[0] == 'lift-at':
                current_floor = parts[1]
                
        action_cost = 0
        floors_to_visit = set()
        can_act_here = False
        
        # Evaluate requirements for each unserved passenger.
        for p in self.passengers:
            if p in served:
                continue
                
            if p in boarded:
                # Passenger is on board and just needs to be dropped off.
                action_cost += 1
                dest = self.destin.get(p)
                if dest:
                    floors_to_visit.add(dest)
                    # We can act immediately if the lift is currently at this passenger's destination.
                    if current_floor == dest:
                        can_act_here = True
            else:
                # Passenger is waiting to be picked up and eventually dropped off.
                action_cost += 2
                orig = current_locations.get(p)
                dest = self.destin.get(p)
                
                if orig:
                    floors_to_visit.add(orig)
                    # We can act immediately if the lift is currently at this passenger's origin.
                    if current_floor == orig:
                        can_act_here = True
                if dest:
                    floors_to_visit.add(dest)
                    
        # Calculate the required movement cost.
        move_cost = len(floors_to_visit)
        
        # If we can perform a useful action at the current floor without moving, 
        # it effectively saves us the very first movement.
        if can_act_here and move_cost > 0:
            move_cost -= 1
            
        # The estimated total cost is the sum of interaction actions and traversal actions.
        return action_cost + move_cost
