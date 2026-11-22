from collections import deque
from heuristics.heuristic_base import Heuristic

def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()

class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Transport domain.

    # Summary
    This heuristic estimates the minimum number of actions required to transport all 
    target packages to their goal locations. It computes shortest path distances 
    between locations and sums up individual transport costs, while dynamically 
    matching available vehicles to packages waiting for pickup.
    
    # Assumptions
    - Each drive action costs 1.
    - Each pick-up and drop action costs 1.
    - All roads are unweighted (distance 1) and may be directed.
    - Vehicles have capacities, but the heuristic relaxes this by assuming a vehicle
      can always make multiple trips, capturing the distance costs efficiently without getting stuck in local minima.
    - Unreachable goals are heavily penalized (cost 1000000).

    # Heuristic Initialization
    - The shortest path distance between all pairs of locations is precomputed using Breadth-First Search (BFS) on the `road` facts from the static information.
    - Goal locations for each package are parsed and stored.
    - The set of all available vehicles is collected from the initial state's `capacity` facts.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to determine the locations of all vehicles and packages, as well as which packages are currently in which vehicles.
    2. For each package that has a goal location:
       - If it is already at its goal, cost is 0.
       - If it is currently inside a vehicle, add `dist(vehicle_loc, goal) + 1` (for driving and dropping).
       - If it is on the ground at a location different from its goal, add `dist(current_loc, goal) + 2` (for picking, driving, and dropping), and mark its location as an "unpicked location".
    3. Determine the "available locations" of each vehicle:
       - Its current physical location.
       - The goal locations of any packages it is currently carrying (since the vehicle will be available there after dropping them off).
    4. For each distinct "unpicked location" where at least one package is waiting:
       - Find the minimum distance from any vehicle's "available locations" to this unpicked location.
       - Add this minimum distance to the total cost. This creates a strong gradient pulling vehicles towards clusters of unpicked packages without overestimating excessively when multiple packages share a location.
    5. Return the total summed cost.
    """

    def __init__(self, task):
        self.goals = task.goals
        
        # Build graph for locations
        locations = set()
        adj = {}
        
        # Extract roads to build the adjacency list
        for fact in task.static:
            parts = get_parts(fact)
            if parts[0] == "road":
                _, l1, l2 = parts
                locations.add(l1)
                locations.add(l2)
                if l1 not in adj:
                    adj[l1] = []
                adj[l1].append(l2)
                
        # Also ensure locations from the initial state and goals are tracked 
        # (in case there are isolated locations with no connecting roads)
        for fact in task.initial_state:
            parts = get_parts(fact)
            if parts[0] == "at":
                locations.add(parts[2])
                
        self.goal_locations = {}
        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == "at":
                self.goal_locations[parts[1]] = parts[2]
                locations.add(parts[2])
                
        for l in locations:
            if l not in adj:
                adj[l] = []
                
        # Compute All-Pairs Shortest Paths (APSP) using Breadth-First Search
        self.distances = {}
        for l in locations:
            self.distances[l] = {l: 0}
            queue = deque([(l, 0)])
            while queue:
                curr, d = queue.popleft()
                for nxt in adj[curr]:
                    if nxt not in self.distances[l]:
                        self.distances[l][nxt] = d + 1
                        queue.append((nxt, d + 1))
                        
        # Identify vehicles from the initial state (vehicles have a capacity fact)
        self.vehicles = set()
        for fact in task.initial_state:
            parts = get_parts(fact)
            if parts[0] == "capacity":
                self.vehicles.add(parts[1])

    def __call__(self, node):
        state = node.state
        
        obj_loc = {}
        pkg_in = {}
        
        # Parse the current state properties
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                obj_loc[parts[1]] = parts[2]
            elif parts[0] == "in":
                pkg_in[parts[1]] = parts[2]
                
        total_cost = 0
        unpicked_locations = set()
        
        # 1. Base Transport Cost per Target Package
        for pkg, goal in self.goal_locations.items():
            if pkg in pkg_in:
                veh = pkg_in[pkg]
                v_loc = obj_loc.get(veh)
                if v_loc:
                    dist = self.distances.get(v_loc, {}).get(goal, 1000000)
                    total_cost += dist + 1
                else:
                    total_cost += 1000000
            else:
                loc = obj_loc.get(pkg)
                if loc == goal:
                    continue  # Already at its destination.
                if loc:
                    dist = self.distances.get(loc, {}).get(goal, 1000000)
                    total_cost += dist + 2
                    unpicked_locations.add(loc)
                else:
                    total_cost += 1000000
                    
        # 2. Vehicle Dispatch Matching Cost for unpicked packages
        # Track available future locations for each vehicle
        veh_locs = {v: set() for v in self.vehicles}
        for v in self.vehicles:
            if v in obj_loc:
                veh_locs[v].add(obj_loc[v])
                
        for pkg, veh in pkg_in.items():
            if pkg in self.goal_locations and veh in veh_locs:
                # Vehicle is also considered "available" at the drop-off location of its packages
                veh_locs[veh].add(self.goal_locations[pkg])
                
        # Compute matching distance for vehicles to travel to unpicked locations
        for loc in unpicked_locations:
            min_dist = 1000000
            for v, locs in veh_locs.items():
                for v_loc in locs:
                    d = self.distances.get(v_loc, {}).get(loc, 1000000)
                    if d < min_dist:
                        min_dist = d
            total_cost += min_dist
            
        return total_cost
