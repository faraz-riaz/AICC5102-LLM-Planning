from heuristics.heuristic_base import Heuristic

def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()

class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the transport domain.

    # Summary
    This heuristic estimates the minimum number of actions required to transport 
    all packages to their respective goal locations. It relaxes the problem by 
    ignoring vehicle capacity constraints and treating each package's delivery 
    as an independent task. 

    # Assumptions
    - Each package needs to be picked up, transported, and dropped off.
    - If a package is already at its goal, no actions are needed.
    - If a package is in a vehicle, it only needs to be transported to the goal and dropped.
    - The cost of moving a vehicle to a package is approximated by the distance from the 
      closest vehicle to that package.
    - Road distances are uniform (each drive action costs 1).
    - Capacity constraints are ignored (similar to a delete relaxation), so we assume any vehicle 
      can pick up a package without having to drop another first.

    # Heuristic Initialization
    - The heuristic extracts all static `road` facts to build a directed graph of locations.
    - An all-pairs shortest path dictionary is computed using Breadth-First Search (BFS),
      since all edge weights are 1.
    - The goal locations for each object are identified from the task's goals.
    - The set of vehicles is extracted from the initial state by identifying any object that 
      has a `capacity` fact.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to identify the location of all vehicles and packages.
       - A vehicle's location is extracted if it matches an `at` fact and is a known vehicle.
       - A package's location is extracted if it matches an `at` fact and is not a vehicle.
       - Packages currently loaded in vehicles are identified using `in` facts.
    2. Initialize `total_cost = 0`.
    3. For each object that has a goal location:
       - If it is a package currently in a vehicle:
         - Find the vehicle's current location.
         - Add the shortest path distance from the vehicle to the goal + 1 (for the drop action).
       - If it is a package at a location (not in a vehicle) and not at its goal:
         - Calculate the distance from its current location to the goal.
         - Find the minimum distance from any vehicle to the package's location.
         - Add both distances + 2 (for pick-up and drop actions).
       - If the goal is for a vehicle itself to be at a location, add the shortest path 
         distance from its current location to the goal.
    4. If any required location is unreachable, a large penalty (1000) is added to 
       guide the search away from dead ends.
    5. Return the sum of costs for all goals.
    """

    def __init__(self, task):
        self.goals = task.goals
        
        self.adj = {}
        locations = set()
        
        # Extract roads from static facts to build the graph
        for fact in task.static:
            parts = get_parts(fact)
            if parts[0] == "road":
                u, v = parts[1], parts[2]
                self.adj.setdefault(u, []).append(v)
                locations.add(u)
                locations.add(v)
                
        self.vehicles = set()
        
        # Extract vehicle capacities and locations from the initial state
        for fact in task.initial_state:
            parts = get_parts(fact)
            if parts[0] == "at":
                locations.add(parts[2])
            elif parts[0] == "capacity":
                self.vehicles.add(parts[1])
                
        self.goal_locations = {}
        # Extract goal locations for packages (and potentially vehicles)
        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == "at":
                obj, location = parts[1], parts[2]
                self.goal_locations[obj] = location
                locations.add(location)
                
        # Compute all-pairs shortest paths using BFS (since edge costs are 1)
        self.distances = {}
        locations_list = list(locations)
        for u in locations_list:
            self.distances[u] = {u: 0}
            queue = [u]
            while queue:
                curr = queue.pop(0)
                for nxt in self.adj.get(curr, []):
                    if nxt not in self.distances[u]:
                        self.distances[u][nxt] = self.distances[u][curr] + 1
                        queue.append(nxt)

    def __call__(self, node):
        state = node.state
        
        vehicle_locations = {}
        package_locations = {}
        packages_in_vehicles = {}
        
        # Parse the current state
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                if obj in self.vehicles:
                    vehicle_locations[obj] = loc
                else:
                    package_locations[obj] = loc
            elif parts[0] == "in":
                pkg, veh = parts[1], parts[2]
                packages_in_vehicles[pkg] = veh
                
        total_cost = 0
        
        for obj, goal_loc in self.goal_locations.items():
            if obj in packages_in_vehicles:
                # The object is a package currently inside a vehicle
                veh = packages_in_vehicles[obj]
                veh_loc = vehicle_locations.get(veh)
                
                if veh_loc:
                    dist = self.distances.get(veh_loc, {}).get(goal_loc, float('inf'))
                    if dist != float('inf'):
                        total_cost += dist + 1  # travel distance + 1 drop action
                    else:
                        total_cost += 1000  # Penalty for being unreachable
                        
            elif obj in package_locations:
                # The object is a package currently on the ground
                pkg_loc = package_locations[obj]
                if pkg_loc == goal_loc:
                    continue  # Already at its goal, 0 cost
                
                dist_to_goal = self.distances.get(pkg_loc, {}).get(goal_loc, float('inf'))
                
                # Find the distance of the closest vehicle to this package
                min_veh_dist = float('inf')
                for v, v_loc in vehicle_locations.items():
                    d = self.distances.get(v_loc, {}).get(pkg_loc, float('inf'))
                    if d < min_veh_dist:
                        min_veh_dist = d
                        
                if dist_to_goal != float('inf') and min_veh_dist != float('inf'):
                    total_cost += min_veh_dist + dist_to_goal + 2  # closest vehicle travel + pick-up + travel to goal + drop
                else:
                    total_cost += 1000  # Penalty for being unreachable
                    
            elif obj in vehicle_locations:
                # If there's an explicit goal for a vehicle to be somewhere
                veh_loc = vehicle_locations[obj]
                if veh_loc == goal_loc:
                    continue
                
                dist = self.distances.get(veh_loc, {}).get(goal_loc, float('inf'))
                if dist != float('inf'):
                    total_cost += dist
                else:
                    total_cost += 1000

        return total_cost
