from fnmatch import fnmatch
from heuristics.heuristic_base import Heuristic

def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()

class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Transport domain.
    
    # Summary
    This heuristic estimates the minimum number of actions (drive, pick-up, drop) required 
    to reach the goal state. It does this by calculating shortest paths in the road network 
    for each package and vehicle that has a destination goal.

    # Assumptions
    - Every action (drive, pick-up, drop) has an equal cost of 1.
    - We relax the problem by completely ignoring vehicle capacity limits.
    - We assume packages and vehicles take the shortest paths based on the `road` graph.
    - The cost to deliver multiple packages is estimated as the sum of their individual 
      costs, ignoring that multiple packages might share a ride in a single vehicle. 
      While this can overestimate the true cost, it provides a strong and monotonic gradient 
      for a greedy search.

    # Heuristic Initialization
    1. Extract `capacity` facts from the initial state and static facts to identify all vehicles.
    2. Extract all `road` facts to build a directed adjacency graph of locations.
    3. Perform a Breadth-First Search (BFS) from every known location to compute an 
       all-pairs shortest path distance matrix.
    4. Parse the goal conditions, separating them into vehicle goals and package goals.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find the physical locations of all vehicles (`at` predicate).
    2. Parse the current state to find the locations of all packages, which can either be at 
       a location (`at` predicate) or inside a vehicle (`in` predicate).
    3. Initialize the estimated cost to 0.
    4. For each vehicle that has a specific goal location:
       - Add the shortest path distance from its current location to its goal location.
    5. For each package that has a goal location:
       - If the package is at its goal location, it requires 0 actions.
       - If the package is currently in a vehicle:
         - Add the shortest path distance from the vehicle's current location to the 
           package's goal location (representing `drive` actions).
         - Add 1 for the required `drop` action.
       - If the package is at a location different from its goal:
         - Add the shortest path distance from its current location to its goal location.
         - Add 2 to account for the necessary `pick-up` and `drop` actions.
         - Find the vehicle closest to the package's current location and add its shortest 
           path distance to the package. This is a crucial step that penalizes states where 
           vehicles are far from packages, creating a gradient that pulls vehicles towards 
           uncollected packages.
    6. Return the total summed cost.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.static = task.static
        self.initial_state = task.initial_state
        
        # Identify all vehicles by looking for 'capacity' declarations
        self.vehicles = set()
        for fact in list(self.initial_state) + list(self.static):
            parts = get_parts(fact)
            if parts and parts[0] == 'capacity':
                self.vehicles.add(parts[1])
                
        # Extract road network and locate all known locations
        self.adj = {}
        self.locations = set()
        for fact in list(self.static) + list(self.initial_state) + list(self.goals):
            parts = get_parts(fact)
            if not parts:
                continue
            if parts[0] == 'road':
                l1, l2 = parts[1], parts[2]
                self.locations.add(l1)
                self.locations.add(l2)
                self.adj.setdefault(l1, set()).add(l2)
            elif parts[0] == 'at':
                self.locations.add(parts[2])
                
        # Compute all-pairs shortest paths using BFS
        self.distances = {}
        for start_node in self.locations:
            self.distances[start_node] = {}
            queue = [(start_node, 0)]
            visited = {start_node}
            while queue:
                curr, d = queue.pop(0)
                self.distances[start_node][curr] = d
                for neighbor in self.adj.get(curr, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, d + 1))
                        
        # Extract goal locations
        self.goal_locations = {}
        self.vehicle_goals = {}
        for goal in self.goals:
            parts = get_parts(goal)
            if parts and parts[0] == 'at':
                obj, loc = parts[1], parts[2]
                if obj in self.vehicles:
                    self.vehicle_goals[obj] = loc
                else:
                    self.goal_locations[obj] = loc

    def __call__(self, node):
        state = node.state
        v_locs = {}
        p_locs = {}
        in_vehicle = {}
        
        # Track the current status of all objects
        for fact in state:
            parts = get_parts(fact)
            if not parts:
                continue
            if parts[0] == 'at':
                obj, loc = parts[1], parts[2]
                if obj in self.vehicles:
                    v_locs[obj] = loc
                else:
                    p_locs[obj] = loc
            elif parts[0] == 'in':
                obj, v = parts[1], parts[2]
                in_vehicle[obj] = v
                
        cost = 0
        
        # Add required actions to achieve vehicle goals
        for v, goal_loc in self.vehicle_goals.items():
            curr_loc = v_locs.get(v)
            if curr_loc:
                cost += self.distances.get(curr_loc, {}).get(goal_loc, 10000)
                
        # Add required actions to achieve package goals
        for p, goal_loc in self.goal_locations.items():
            if p in in_vehicle:
                # Package is currently carried by a vehicle
                v = in_vehicle[p]
                v_loc = v_locs.get(v)
                if v_loc:
                    dist = self.distances.get(v_loc, {}).get(goal_loc, 10000)
                    cost += dist + 1  # driving distance + 1 drop action
                else:
                    cost += 10000
            elif p in p_locs:
                # Package is waiting at a location
                curr_loc = p_locs[p]
                if curr_loc == goal_loc:
                    continue  # The package has already reached its destination
                
                dist = self.distances.get(curr_loc, {}).get(goal_loc, 10000)
                cost += dist + 2  # driving distance + pick-up + drop
                
                # Minimum distance for the nearest vehicle to approach this package
                if v_locs:
                    min_dist = min(self.distances.get(vl, {}).get(curr_loc, 10000) for vl in v_locs.values())
                else:
                    min_dist = 10000
                cost += min_dist
                
        return cost
