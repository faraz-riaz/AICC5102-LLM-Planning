from heuristics.heuristic_base import Heuristic


def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()


class miconicLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the miconic domain.
    
    # Summary
    This heuristic estimates the required number of actions to transport all goal passengers 
    from their origin to their destination. The heuristic strictly decreases along the optimal 
    path by evaluating base action costs (moves, boarding, departing) and applying a small 
    subtractive bonus ("demand" bonus) for floors where useful actions can be applied immediately.

    # Assumptions
    - The elevator has unlimited capacity, so multiple passengers can be carried simultaneously.
    - Because the `above` relation is fully connected in the domain, the elevator can travel 
      directly from any floor to any other floor in exactly 1 action (either `up` or `down`).
    - The main goal is to have a set of passengers `served`. We only consider passengers 
      that are explicitly part of the goal state to avoid unnecessary extra work.

    # Heuristic Initialization
    - Extract the passengers that need to be served from the goal facts.
    - Parse the static facts to identify the destination (`destin`) floor for each passenger.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find the elevator's location (`lift-at`), the origins of 
       unboarded goal passengers, and the set of currently boarded goal passengers.
    2. Identify all unique floors that still need to be visited: the origins of all unboarded 
       goal passengers, plus the destinations of all unboarded and boarded goal passengers.
    3. Compute a base cost for passenger actions:
       - Each unboarded passenger requires 2 actions (board and depart). We scale this by 2 (cost = 4).
       - Each boarded passenger requires 1 action (depart). We scale this by 2 (cost = 2).
    4. Compute a base cost for move actions:
       - The minimum number of moves is the number of required unique floors, minus 1 if the 
         elevator is already currently at one of them. We scale this move cost by 2.
    5. Compute a 'demand' bonus to break plateaus:
       - Count how many useful passenger actions can be applied at the current elevator floor 
         (i.e., passengers waiting to board here + boarded passengers destined to depart here).
    6. Return the total scaled base cost minus the demand bonus. This ensures the heuristic 
       strictly decreases when the elevator moves to a floor with demands, or when an action 
       (board/depart) fulfills a demand.
    """

    def __init__(self, task):
        self.goals = task.goals
        static_facts = task.static

        self.goal_passengers = set()
        self.goal_floor = None
        
        # Extract passengers that must be served and any potential target floor for the elevator
        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == "served":
                self.goal_passengers.add(parts[1])
            elif parts[0] == "lift-at":
                self.goal_floor = parts[1]

        self.destinations = {}
        # Destinations are static facts and do not change throughout the problem
        for fact in static_facts:
            if fact.startswith("(destin "):
                parts = get_parts(fact)
                self.destinations[parts[1]] = parts[2]

    def __call__(self, node):
        state = node.state
        
        lift_at = None
        origins = {}
        boarded = set()
        
        # Parse the current state properties
        for fact in state:
            if fact.startswith("(lift-at "):
                lift_at = get_parts(fact)[1]
            elif fact.startswith("(origin "):
                parts = get_parts(fact)
                p = parts[1]
                # Only track passengers that are part of the goals
                if p in self.goal_passengers:
                    origins[p] = parts[2]
            elif fact.startswith("(boarded "):
                parts = get_parts(fact)
                p = parts[1]
                if p in self.goal_passengers:
                    boarded.add(p)
                    
        visit_floors = set()
        
        if self.goal_floor:
            visit_floors.add(self.goal_floor)
            
        # Add all mandatory pickup locations and drop-off locations to the 'must visit' set
        for p, orig in origins.items():
            visit_floors.add(orig)
            visit_floors.add(self.destinations[p])
            
        for p in boarded:
            visit_floors.add(self.destinations[p])
            
        # Base multiplier logic: unboarded=4, boarded=2
        base_cost = 4 * len(origins) + 2 * len(boarded)
        
        # Movement cost logic: 1 action per required floor (scaled by 2)
        if lift_at in visit_floors:
            move_cost = len(visit_floors) - 1
        else:
            move_cost = len(visit_floors)
            
        base_cost += 2 * move_cost
        
        # Calculate 'demands' (number of actions we can perform at the CURRENT floor)
        demands = 0
        for p, orig in origins.items():
            if orig == lift_at:
                demands += 1
        for p in boarded:
            if self.destinations[p] == lift_at:
                demands += 1
                
        # Final calculation: The more demands we can resolve immediately, the lower the heuristic.
        # This resolves tie-breaking gracefully and guides the search directly towards productive operations.
        return base_cost - demands
