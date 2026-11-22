import collections
from heuristics.heuristic_base import Heuristic


def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()


class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Transport domain.

    # Summary
    This heuristic estimates the minimum number of actions (drive, pick-up, drop)
    required to deliver all packages to their goal locations. It also accounts for 
    vehicle location goals and package-in-vehicle goals, if any.

    # Assumptions
    - Vehicles can pick up packages, drive along roads, and drop them off.
    - Each drive, pick-up, and drop action costs 1.
    - We relax the problem by ignoring vehicle capacity constraints when calculating distances.
    - The travel distance between locations is the shortest path in the road network.
    - If multiple packages are at the same location, they might share a vehicle's travel distance
      in the heuristic's perspective, which provides a strong gradient towards clusters of packages.

    # Heuristic Initialization
    - Parses all static and initial state facts to construct the road network (adjacency list).
    - Computes all-pairs shortest paths using Breadth-First Search (BFS).
    - Extracts all vehicles by looking for `capacity` facts in the initial state.
    - Classifies goals into package destination goals, vehicle location goals, and `in-vehicle` goals.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find the locations of all vehicles and packages, as well as 
       which packages are currently inside which vehicles.
    2. For each package that has a target location goal:
        a. If the package is already at its goal location, cost is 0.
        b. If the package is currently at a non-goal location:
           - Cost includes 2 actions (1 pick-up + 1 drop).
           - Add the driving distance from the package's current location to its goal.
           - Add the driving distance of the closest vehicle to the package's current location.
        c. If the package is inside a vehicle:
           - Cost includes 1 action (drop).
           - Add the driving distance from the vehicle's current location to the package's goal.
    3. Add distances for any vehicle location goals (if the vehicle is not at its goal).
    4. Add costs for any package-in-vehicle goals (if the package is not in the correct vehicle).
    5. Return the total sum as the heuristic value.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.static = task.static
        self.initial_state = task.initial_state

        # 1. Build road network and identify all locations
        self.roads = collections.defaultdict(list)
        locations = set()
        
        # Roads can sometimes be classified as static or initial state depending on the planner's pre-processor
        for fact in self.static | self.initial_state:
            parts = get_parts(fact)
            if parts[0] == "road":
                l1, l2 = parts[1], parts[2]
                self.roads[l1].append(l2)
                locations.add(l1)
                locations.add(l2)

        # 2. Compute all-pairs shortest paths
        self.distances = {}
        for loc in locations:
            self.distances[loc] = self.bfs(loc, locations)

        # 3. Extract vehicles
        # Vehicles always have a capacity fact in the initial state
        self.vehicles = set()
        for fact in self.initial_state:
            parts = get_parts(fact)
            if parts[0] == "capacity":
                self.vehicles.add(parts[1])

        # 4. Extract and classify goals
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
                obj, veh = parts[1], parts[2]
                self.in_goals[obj] = veh

    def bfs(self, start_loc, locations):
        """Find the shortest distance from the start_loc to all other locations using BFS."""
        distances = {start_loc: 0}
        queue = collections.deque([start_loc])
        
        while queue:
            curr = queue.popleft()
            dist = distances[curr]
            for neighbor in self.roads[curr]:
                if neighbor not in distances:
                    distances[neighbor] = dist + 1
                    queue.append(neighbor)
        
        # Assign a large finite penalty for unreachable locations (10000)
        for loc in locations:
            if loc not in distances:
                distances[loc] = 10000
                
        return distances

    def __call__(self, node):
        state = node.state
        
        vehicle_locs = {}
        package_locs = {}
        package_in_veh = {}
        
        # Parse current state facts
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                if obj in self.vehicles:
                    vehicle_locs[obj] = loc
                else:
                    package_locs[obj] = loc
            elif parts[0] == "in":
                package_in_veh[parts[1]] = parts[2]

        total_cost = 0
        
        # 1. Package Location Goals
        for pkg, goal_loc in self.package_goals.items():
            if pkg in package_locs:
                curr_loc = package_locs[pkg]
                if curr_loc == goal_loc:
                    continue  # Package is already at its final destination
                    
                total_cost += 2  # Action cost for pick-up and drop
                total_cost += self.distances.get(curr_loc, {}).get(goal_loc, 10000)  # Drive distance to goal
                
                # Minimum distance for any available vehicle to reach the package
                min_veh_dist = 10000
                for v, v_loc in vehicle_locs.items():
                    d = self.distances.get(v_loc, {}).get(curr_loc, 10000)
                    if d < min_veh_dist:
                        min_veh_dist = d
                total_cost += min_veh_dist
                
            elif pkg in package_in_veh:
                v = package_in_veh[pkg]
                v_loc = vehicle_locs.get(v)
                if v_loc:
                    total_cost += 1  # Action cost for drop
                    total_cost += self.distances.get(v_loc, {}).get(goal_loc, 10000)  # Drive distance to goal
                    
        # 2. Vehicle Location Goals (if specified in the problem instance)
        for veh, goal_loc in self.vehicle_goals.items():
            curr_loc = vehicle_locs.get(veh)
            if curr_loc and curr_loc != goal_loc:
                total_cost += self.distances.get(curr_loc, {}).get(goal_loc, 10000)
                
        # 3. Package In-Vehicle Goals (if specified in the problem instance)
        for pkg, v_goal in self.in_goals.items():
            if pkg in package_in_veh:
                curr_v = package_in_veh[pkg]
                if curr_v != v_goal:
                    total_cost += 2  # Drop from current vehicle and pick-up by goal vehicle
                    curr_loc = vehicle_locs.get(curr_v)
                    v_goal_loc = vehicle_locs.get(v_goal)
                    if curr_loc and v_goal_loc:
                        total_cost += self.distances.get(v_goal_loc, {}).get(curr_loc, 10000)
            elif pkg in package_locs:
                curr_loc = package_locs[pkg]
                v_goal_loc = vehicle_locs.get(v_goal)
                if v_goal_loc:
                    total_cost += 1  # Pick-up
                    total_cost += self.distances.get(v_goal_loc, {}).get(curr_loc, 10000)
                    
        return total_cost
