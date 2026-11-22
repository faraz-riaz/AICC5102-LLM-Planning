from heuristics.heuristic_base import Heuristic

class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the miconic domain.

    # Summary
    This heuristic estimates the minimum number of actions (moves, boards, and departs) 
    required to transport all unserved goal passengers to their destinations.

    # Assumptions
    - The elevator has infinite capacity, so multiple passengers can be boarded and transported simultaneously.
    - Moving between any two floors requires exactly 1 action (`up` or `down`), regardless of the physical distance, assuming proper topological ordering (`above`).
    - Passengers that are not explicitly part of the goal state can be safely ignored.

    # Heuristic Initialization
    - Parses the goal conditions to identify the set of `goal_passengers` that must be served.
    - Parses the static facts to create a mapping (`destin_map`) from each passenger to their destination floor.

    # Step-By-Step Thinking for Computing Heuristic
    1. Identify Current Passenger States:
       - Iterate over the facts in the state to find passengers who are waiting (indicated by an `origin` fact) and those who are currently in the elevator (indicated by a `boarded` fact).
       - Filter out any passengers that are not in `goal_passengers`.
    2. Determine Required Stops:
       - `immediate_stops`: Floors the elevator must visit to make immediate progress. This includes the origins of all waiting passengers (so they can board) and the destinations of all currently boarded passengers (so they can depart).
       - `future_stops`: Floors the elevator must visit eventually, but not immediately. These are the destinations of currently waiting passengers. If a future stop is already an `immediate_stop`, it is excluded to avoid double counting.
    3. Estimate Move Actions:
       - Since any floor can be reached in 1 action from any other floor, visiting a set of unique floors takes 1 move action per floor.
       - If the elevator's current floor (`lift_floor`) is already in `immediate_stops`, we save 1 move action.
       - Estimated move actions = |immediate_stops \ {lift_floor}| + |future_stops|.
    4. Estimate Board and Depart Actions:
       - Every waiting passenger must eventually board, costing 1 action per waiting passenger.
       - Every waiting and boarded passenger must eventually depart at their destination, costing 1 action per unserved passenger.
    5. Final Summation:
       - The heuristic value is the sum of the estimated move, board, and depart actions.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.static = task.static
        
        # Extract passengers that must be served to satisfy the goal
        self.goal_passengers = set()
        for goal in self.goals:
            parts = goal[1:-1].split()
            if parts[0] == "served":
                self.goal_passengers.add(parts[1])
                
        # Create a mapping from passenger to their destination floor using static facts
        self.destin_map = {}
        for fact in self.static:
            parts = fact[1:-1].split()
            if parts[0] == "destin":
                passenger = parts[1]
                destination_floor = parts[2]
                self.destin_map[passenger] = destination_floor

    def __call__(self, node):
        state = node.state
        
        waiting_passengers = set()
        waiting_origins = set()
        boarded_passengers = set()
        lift_floor = None
        
        # Extract information from the current state
        for fact in state:
            parts = fact[1:-1].split()
            if parts[0] == "origin":
                passenger = parts[1]
                if passenger in self.goal_passengers:
                    waiting_passengers.add(passenger)
                    waiting_origins.add(parts[2])
            elif parts[0] == "boarded":
                passenger = parts[1]
                if passenger in self.goal_passengers:
                    boarded_passengers.add(passenger)
            elif parts[0] == "lift-at":
                lift_floor = parts[1]
                
        # Determine necessary destination stops for passengers
        waiting_destins = {self.destin_map[p] for p in waiting_passengers}
        boarded_destins = {self.destin_map[p] for p in boarded_passengers}
        
        # Calculate unique immediate and future floors to visit
        immediate_stops = waiting_origins | boarded_destins
        future_stops = waiting_destins - immediate_stops
        
        # Compute required movement actions
        if lift_floor in immediate_stops:
            moves = len(immediate_stops) - 1 + len(future_stops)
        else:
            moves = len(immediate_stops) + len(future_stops)
            
        # Compute required passenger interactions
        board_cost = len(waiting_passengers)
        depart_cost = len(waiting_passengers) + len(boarded_passengers)
        
        # The total estimated cost to reach the goal
        return moves + board_cost + depart_cost
