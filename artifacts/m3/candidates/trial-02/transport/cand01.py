import collections
from fnmatch import fnmatch
from heuristics.heuristic_base import Heuristic

def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()

class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Transport domain.
    
    # Summary
    This heuristic estimates the minimum number of actions (drive, pick-up, drop) 
    required to transport all target packages and vehicles to their respective goal locations.
    
    # Assumptions
    - Vehicles have infinite capacity (capacity constraints are relaxed).
    - All roads have a uniform traversal cost of 1 action (drive).
    - Packages require 1 action to be picked up and 1 action to be dropped.
    - Vehicles can reach packages and drop them off directly without interacting with other vehicles.
    
    # Heuristic Initialization
    - Extracts all `road` facts from the initial state and static facts to build a map of locations.
    - Identifies all vehicles by looking for `capacity` facts in the initial state.
    - Computes All-Pairs Shortest Path (APSP) between all locations using Breadth-First Search (BFS) to precompute drive distances.
    - Extracts all `(at ?obj ?loc)` goals to identify destination locations for packages and vehicles.
    
    # Step-By-Step Thinking for Computing Heuristic
    1. Scan the current state to find the location of every vehicle and package.
    2. For each goal `(at ?obj ?goal_loc)`:
       a. If `?obj` is already at `?goal_loc`, cost is 0.
       b. If `?obj` is a vehicle and it is at `?curr_loc`, add the shortest path distance to `?goal_loc`.
       c. If `?obj` is a package and it is currently at some location `?curr_loc` (on the ground):
          - Add the shortest path distance from `?curr_loc` to `?goal_loc`.
          - Add 2 actions for `pick-up` and `drop`.
          - Find the nearest vehicle to `?curr_loc` and add the distance required for that vehicle to reach the package.
       d. If `?obj` is a package and it is currently inside a vehicle:
          - Add the shortest path distance from the vehicle's current location to `?goal_loc`.
          - Add 1 action for `drop`.
    3. Return the sum of all these costs. This provides a strong gradient guiding vehicles to pick up packages and drive them to their destinations.
    """
    
    def __init__(self, task):
        self.goals = task.goals
        self.static_facts = task.static
        self.initial_state = task.initial_state
        
        # Extract all road connections to build a graph
        roads = []
        for fact in self.static_facts | self.initial_state:
            parts = get_parts(fact)
            if parts[0] == "road":
                roads.append((parts[1], parts[2]))
                
        # Extract vehicles (they have a capacity in the initial state)
        self.vehicles = set()
        for fact in self.initial_state | self.static_facts:
            parts = get_parts(fact)
            if parts[0] == "capacity":
                self.vehicles.add(parts[1])
                
        # Build adjacency list for locations
        adj = {}
        locations = set()
        for u, v in roads:
            adj.setdefault(u, []).append(v)
            locations.add(u)
            locations.add(v)
            
        # Compute All-Pairs Shortest Path (APSP) using BFS
        self.distances = {}
        for loc in locations:
            self.distances[loc] = {}
            queue = collections.deque([loc])
            self.distances[loc][loc] = 0
            while queue:
                curr = queue.popleft()
                curr_dist = self.distances[loc][curr]
                for neighbor in adj.get(curr, []):
                    if neighbor not in self.distances[loc]:
                        self.distances[loc][neighbor] = curr_dist + 1
                        queue.append(neighbor)
                        
        # Store goal locations
        self.goal_locations = {}
        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == "at":
                self.goal_locations[parts[1]] = parts[2]

    def __call__(self, node):
        state = node.state
        
        current_loc = {}
        in_vehicle = {}
        vehicle_locs = {}
        
        # Parse current object locations and states
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                current_loc[obj] = loc
                if obj in self.vehicles:
                    vehicle_locs[obj] = loc
            elif parts[0] == "in":
                pkg, v = parts[1], parts[2]
                in_vehicle[pkg] = v
                
        cost = 0
        
        # Calculate distance-based cost for each unachieved goal
        for obj, goal_loc in self.goal_locations.items():
            if obj in current_loc:
                curr_loc = current_loc[obj]
                
                # Goal already met for this object
                if curr_loc == goal_loc:
                    continue
                    
                dist = self.distances.get(curr_loc, {}).get(goal_loc, 1000)
                
                if obj in self.vehicles:
                    # Vehicle just needs to drive to its goal
                    cost += dist
                else:
                    # Package needs to be picked up, transported, and dropped off
                    cost += dist + 2
                    
                    # Add distance for the nearest vehicle to reach this package
                    min_v_dist = 1000
                    for v_loc in vehicle_locs.values():
                        v_dist = self.distances.get(v_loc, {}).get(curr_loc, 1000)
                        if v_dist < min_v_dist:
                            min_v_dist = v_dist
                    cost += min_v_dist
                    
            elif obj in in_vehicle:
                # Package is currently inside a vehicle
                v = in_vehicle[obj]
                v_loc = vehicle_locs.get(v)
                if v_loc:
                    # Vehicle needs to drive to goal and drop the package
                    dist = self.distances.get(v_loc, {}).get(goal_loc, 1000)
                    cost += dist + 1
                else:
                    # Fallback for unreachable or unplaced vehicles
                    cost += 1000
                    
        return cost
