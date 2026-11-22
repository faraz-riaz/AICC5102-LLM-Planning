from collections import deque
from heuristics.heuristic_base import Heuristic


def get_parts(fact):
    """
    Extract the components of a PDDL fact by removing parentheses and splitting the string.
    """
    return fact[1:-1].split()


class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Transport domain.
    
    # Summary
    This heuristic estimates the minimum number of actions required to transport 
    all packages to their respective goal locations. It computes the shortest-path 
    distances between locations and evaluates the cost based on the current state 
    of packages (whether they are waiting at a location or already loaded in a vehicle).
    
    # Assumptions
    - Each drive, pick-up, and drop action has a uniform cost of 1.
    - All roads are traversable by any vehicle. 
    - The shortest path distance correctly approximates the number of drive actions.
    - Capacity constraints are partially relaxed: the heuristic groups the required 
      pickups but ensures that only vehicles with remaining capacity are considered 
      when estimating the distance to fetch a package.
    - The primary goals are package locations (`at` predicates).
    
    # Heuristic Initialization
    - Parses all `road` facts from the static and initial state facts.
    - Computes all-pairs shortest paths using Breadth-First Search (BFS).
    - Identifies all vehicles and their valid capacity sizes (`capacity-predecessor`).
    - Extracts goal locations for packages and vehicles.
    
    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find the locations of all vehicles and packages, 
       and determine which packages are inside which vehicles.
    2. Identify "available vehicles" (vehicles that have a capacity size allowing 
       at least one more pick-up).
    3. For each package that has a goal location:
       a. If it is already at its goal, the cost is 0.
       b. If it is inside a vehicle: 
          - Calculate the distance from the vehicle's current location to the goal.
          - Add 1 action for dropping the package.
       c. If it is waiting at a location (not in a vehicle):
          - Calculate the distance from the package's location to its goal.
          - Add 2 actions for pick-up and drop.
          - Find the minimum distance from any *available* vehicle to the package's location.
          - Add this vehicle-approach distance to the cost. (This creates a strong 
            gradient pulling available vehicles toward clusters of waiting packages).
    4. For any vehicle with a specific goal location, add the distance from its 
       current location to its goal.
    5. Sum all calculated costs to return the total estimated cost. If the cost is 
       0 but some unspecified goals remain unmet, return a fallback value of 1.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.static_facts = task.static
        
        # 1. Extract roads and build adjacency list
        self.adj = {}
        self.locations = set()
        
        # PDDL might put immutable facts in either static or initial_state depending on the parser.
        all_initial_facts = self.static_facts | task.initial_state
        
        for fact in all_initial_facts:
            parts = get_parts(fact)
            if parts[0] == "road":
                l1, l2 = parts[1], parts[2]
                self.adj.setdefault(l1, set()).add(l2)
                self.locations.add(l1)
                self.locations.add(l2)
                
        # 2. Precompute all-pairs shortest path distances using BFS
        self.dist = {}
        for start_loc in self.locations:
            self.dist[start_loc] = {start_loc: 0}
            queue = deque([start_loc])
            while queue:
                curr = queue.popleft()
                d = self.dist[start_loc][curr]
                for nxt in self.adj.get(curr, []):
                    if nxt not in self.dist[start_loc]:
                        self.dist[start_loc][nxt] = d + 1
                        queue.append(nxt)
                        
        # 3. Identify vehicles and capacity rules
        self.vehicles = set()
        for fact in task.initial_state:
            parts = get_parts(fact)
            if parts[0] == "capacity":
                self.vehicles.add(parts[1])
                
        self.can_pickup_sizes = set()
        for fact in all_initial_facts:
            parts = get_parts(fact)
            if parts[0] == "capacity-predecessor":
                # parts[2] is the larger size required in the precondition to allow a pick-up
                self.can_pickup_sizes.add(parts[2])
                
        # 4. Parse goals
        self.package_goals = {}
        self.vehicle_goals = {}
        self.in_goals = {}
        
        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                if obj in self.vehicles:
                    self.vehicle_goals[obj] = loc
                else:
                    self.package_goals[obj] = loc
            elif parts[0] == "in":
                self.in_goals[parts[1]] = parts[2]

    def __call__(self, node):
        state = node.state
        
        at_loc = {}
        in_vehicle = {}
        vehicle_locs = {}
        available_vehicles = set()
        
        # 1. Parse the current state
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                at_loc[obj] = loc
                if obj in self.vehicles:
                    vehicle_locs[obj] = loc
            elif parts[0] == "in":
                pkg, veh = parts[1], parts[2]
                in_vehicle[pkg] = veh
            elif parts[0] == "capacity":
                veh, size = parts[1], parts[2]
                if size in self.can_pickup_sizes:
                    available_vehicles.add(veh)
                    
        # Determine valid target vehicles to fetch waiting packages
        valid_vehicle_locs = set(vehicle_locs[v] for v in available_vehicles if v in vehicle_locs)
        if not valid_vehicle_locs:
            # Fallback if all vehicles are currently completely full
            valid_vehicle_locs = set(vehicle_locs.values())
            
        total_cost = 0
        min_v_dist_cache = {}
        
        # 2. Package AT goals
        for pkg, g_loc in self.package_goals.items():
            if pkg in at_loc:
                p_loc = at_loc[pkg]
                if p_loc == g_loc:
                    continue  # The package is already at its goal location
                    
                d_to_goal = self.dist.get(p_loc, {}).get(g_loc, 10000)
                
                # Retrieve or calculate the distance from the closest vehicle
                if p_loc not in min_v_dist_cache:
                    min_v_dist = 10000
                    if valid_vehicle_locs:
                        for v_loc in valid_vehicle_locs:
                            v_d = self.dist.get(v_loc, {}).get(p_loc, 10000)
                            if v_d < min_v_dist:
                                min_v_dist = v_d
                    else:
                        min_v_dist = 0
                    min_v_dist_cache[p_loc] = min_v_dist
                else:
                    min_v_dist = min_v_dist_cache[p_loc]
                    
                # 2 actions (pickup + drop) + distance to target + vehicle traveling to package
                total_cost += d_to_goal + 2 + min_v_dist
                
            elif pkg in in_vehicle:
                veh = in_vehicle[pkg]
                v_loc = vehicle_locs.get(veh)
                if v_loc:
                    d_to_goal = self.dist.get(v_loc, {}).get(g_loc, 10000)
                    total_cost += d_to_goal + 1  # 1 action (drop) + distance to target
                else:
                    total_cost += 10000
                    
        # 3. Vehicle AT goals
        for veh, g_loc in self.vehicle_goals.items():
            if veh in vehicle_locs:
                v_loc = vehicle_locs[veh]
                if v_loc != g_loc:
                    total_cost += self.dist.get(v_loc, {}).get(g_loc, 10000)
                    
        # 4. Package IN goals (fallback support, rarely present in this domain)
        for pkg, g_veh in self.in_goals.items():
            if pkg in in_vehicle:
                if in_vehicle[pkg] != g_veh:
                    total_cost += 2  # Needs to be dropped and picked up by the correct vehicle
            else:
                total_cost += 1  # Needs to be picked up
                
        # 5. Sanity check: Ensure heuristic is strictly 0 only for actual goal states
        if total_cost == 0 and not self.goals.issubset(state):
            return 1
            
        return total_cost
