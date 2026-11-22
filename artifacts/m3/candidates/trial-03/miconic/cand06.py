from heuristics.heuristic_base import Heuristic

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Miconic domain.

    # Summary
    This heuristic estimates the total number of actions (moves, boards, departs) 
    required to serve all goal passengers. It does this by computing an independent 
    cost for each passenger based on their current status (waiting, boarded, or served) 
    and summing these costs. By summing individual passenger costs, the heuristic 
    creates a strong "gravity" effect that naturally guides the elevator towards floors 
    with the most passengers waiting or needing to be dropped off.

    # Assumptions
    - The elevator has unlimited capacity (can hold any number of passengers).
    - Moving between any two floors takes 1 action (the domain is fully connected via the `above` predicate).
    - All valid passengers have a specific `origin` and `destin` (destination) floor.
    - `destin` facts are static or present in the initial state and do not change.
    - `origin` facts are present in the initial state. While they get removed when a passenger boards, their initial value is sufficient to know where they started.

    # Heuristic Initialization
    - Extract all goal passengers from `task.goals`.
    - Extract the destination (`destin`) for each passenger by parsing `task.static` and `task.initial_state`.
    - Extract the starting floor (`origin`) for each passenger by parsing `task.initial_state`.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find the elevator's current floor by looking for the `(lift-at ?floor)` fact.
    2. Iterate over all goal passengers to determine their status:
       - If `(served ?p)` is in the state, the passenger has reached their destination (cost = 0).
       - If `(boarded ?p)` is in the state, the passenger is currently in the elevator.
       - Otherwise, the passenger is still waiting at their origin floor.
    3. Calculate the estimated cost per passenger:
       - Served: 0 actions remaining.
       - Boarded: 1 action to `depart` + 1 move if the elevator is not currently at their destination floor.
       - Waiting: 2 actions (`board` and `depart`) + 1 move if the elevator is not at their origin + 1 move for the trip to their destination.
    4. Sum the costs across all goal passengers. This provides a strict and steep gradient that pulls the greedy best-first search towards the goal while prioritizing high-reward floors.
    """

    def __init__(self, task):
        self.goals = task.goals
        
        # Extract the passengers that need to be served from the goals
        self.goal_passengers = []
        for goal in self.goals:
            parts = goal[1:-1].split()
            if parts[0] == "served":
                self.goal_passengers.append(parts[1])
                
        # Dictionaries to store static destinations and initial origins
        self.destinations = {}
        self.origins = {}
        
        # Parse both static and initial_state to cover all bases for finding properties
        for fact in task.static | task.initial_state:
            parts = fact[1:-1].split()
            if parts[0] == "destin":
                self.destinations[parts[1]] = parts[2]
            elif parts[0] == "origin":
                self.origins[parts[1]] = parts[2]

    def __call__(self, node):
        state = node.state
        
        # Find the current floor of the elevator
        current_floor = None
        for fact in state:
            if fact.startswith("(lift-at "):
                current_floor = fact[1:-1].split()[1]
                break
                
        if not current_floor:
            # Fallback in case lift-at is missing (should not happen in valid states)
            return 0
            
        total_cost = 0
        
        # Calculate cost for every goal passenger
        for p in self.goal_passengers:
            served_fact = f"(served {p})"
            if served_fact in state:
                continue  # Passenger is successfully served
                
            boarded_fact = f"(boarded {p})"
            if boarded_fact in state:
                # Passenger is currently inside the elevator
                destin = self.destinations.get(p)
                
                # 1 action required: depart
                total_cost += 1
                
                # 1 move required if not already at destination
                if current_floor != destin:
                    total_cost += 1
            else:
                # Passenger is waiting for the elevator at their origin
                origin = self.origins.get(p)
                destin = self.destinations.get(p)
                
                # 2 actions required: board, depart
                total_cost += 2
                
                # Move to origin if the elevator is not already there
                if current_floor != origin:
                    total_cost += 1
                    
                # Move from origin to destination (this step will always take at least 1 move)
                total_cost += 1
                
        return total_cost
