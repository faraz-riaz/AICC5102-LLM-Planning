from heuristics.heuristic_base import Heuristic


def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()


class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Transport domain.
    
    # Summary
    This heuristic estimates the minimum number of actions required to deliver all 
    remaining packages to their goal locations. It computes shortest paths between 
    locations and assigns fetch costs for uncollected packages based on available vehicles.
    
    # Assumptions
    - Driving between connected locations takes 1 action (cost = distance).
    - Picking up a package takes 1 action.
    - Dropping a package takes 1 action.
    - Capacity constraints are relaxed: vehicles can pick up packages if they are at the same location.
      The heuristic primarily drives vehicles towards packages and packages towards goals.
    
    # Heuristic Initialization
    - Parses `road` facts from both `task.static` and `task.initial_state` to build a location graph.
    - Extracts all known locations from the roads and the `at` facts.
    - Computes all-pairs shortest paths using Breadth-First Search (BFS).
    - Extracts the set of all vehicles by looking at the `capacity` facts in the initial state.
    - Stores the goal locations for each package.
    
    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to identify the location of all packages and vehicles.
    2. Track which packages are currently in transit (inside a vehicle using the `in` predicate).
    3. Determine `avail_locs`, which represents locations where vehicles are currently 
       available or will be available in the future. This includes:
       - The current locations of all vehicles.
       - The destination goal locations of any packages currently in transit.
    4. For each package that has a goal location:
       a. If the package is already at its goal location:
          - Cost = 0.
       b. If the package is in transit (inside a vehicle):
          - Cost = distance from the vehicle's current location to the package's goal + 1 (for the drop action).
       c. If the package is at a location and uncollected (not at its goal):
          - Cost = distance from its current location to the goal + 2 (for pick-up and drop actions).
          - Fetch Cost = minimum distance from any location in `avail_locs` to the package's current location.
          - Total cost for this package = Cost + Fetch Cost.
    5. Sum the individual costs over all packages to form the total heuristic estimate.
       If any required path is unreachable, return infinity.
    """

    def __init__(self, task):
        self.goals = task.goals
        
        self.roads = {}
        self.locations = set()
        self.vehicles = set()
        
        # 1. Parse static and initial state for roads, locations, and vehicles
        for fact in task.static | task.initial_state:
            parts = get_parts(fact)
            if parts[0] == "road":
                l1, l2 = parts[1], parts[2]
                if l1 not in self.roads:
                    self.roads[l1] = set()
                self.roads[l1].add(l2)
                self.locations.add(l1)
                self.locations.add(l2)
            elif parts[0] == "capacity":
                # Only vehicles have a capacity predicate
                self.vehicles.add(parts[1])
            elif parts[0] == "at":
                # Ensure all locations are captured even if they have no roads
                self.locations.add(parts[2])
                
        # 2. Extract goal locations for packages
        self.goal_locations = {}
        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                self.goal_locations[obj] = loc
                self.locations.add(loc)
                
        # 3. Compute all-pairs shortest paths using BFS
        self.dist = {}
        for l1 in self.locations:
            self.dist[l1] = {l2: float('inf') for l2 in self.locations}
            self.dist[l1][l1] = 0
            queue = [l1]
            visited = {l1}
            while queue:
                curr = queue.pop(0)
                for nxt in self.roads.get(curr, []):
                    if nxt not in visited:
                        visited.add(nxt)
                        self.dist[l1][nxt] = self.dist[l1][curr] + 1
                        queue.append(nxt)

    def __call__(self, node):
        state = node.state
        
        current_locations = {}
        package_in = {}
        
        # Extract current locations and transit states
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                current_locations[parts[1]] = parts[2]
            elif parts[0] == "in":
                package_in[parts[1]] = parts[2]
                
        # Determine locations where vehicles are or will be available
        avail_locs = set()
        for veh in self.vehicles:
            veh_loc = current_locations.get(veh)
            if veh_loc:
                avail_locs.add(veh_loc)
                
        for pkg, veh in package_in.items():
            goal_loc = self.goal_locations.get(pkg)
            if goal_loc:
                avail_locs.add(goal_loc)
                
        total_cost = 0
        
        # Compute the cost for each package
        for pkg, goal_loc in self.goal_locations.items():
            if pkg in current_locations:
                curr_loc = current_locations[pkg]
                if curr_loc == goal_loc:
                    continue  # Package is already at goal
                    
                # Package is uncollected, needs to be picked up, driven, and dropped
                d = self.dist.get(curr_loc, {}).get(goal_loc, float('inf'))
                if d == float('inf'):
                    return float('inf')
                    
                total_cost += d + 2
                
                # Fetch cost: distance for the nearest available vehicle to reach the package
                min_fetch = float('inf')
                for aloc in avail_locs:
                    fd = self.dist.get(aloc, {}).get(curr_loc, float('inf'))
                    if fd < min_fetch:
                        min_fetch = fd
                        
                if min_fetch == float('inf'):
                    return float('inf')
                    
                total_cost += min_fetch
                
            elif pkg in package_in:
                veh = package_in[pkg]
                veh_loc = current_locations.get(veh)
                if not veh_loc:
                    return float('inf')
                    
                # Package is inside a vehicle, needs to be driven and dropped
                d = self.dist.get(veh_loc, {}).get(goal_loc, float('inf'))
                if d == float('inf'):
                    return float('inf')
                    
                total_cost += d + 1
                
        return total_cost
