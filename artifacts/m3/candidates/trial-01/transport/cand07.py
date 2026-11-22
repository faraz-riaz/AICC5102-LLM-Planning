from collections import defaultdict
from heuristics.heuristic_base import Heuristic

def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()

class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Transport domain.
    
    # Summary
    Estimates the minimum number of actions to transport all packages to their destinations.
    It uses precomputed all-pairs shortest paths for the road network to estimate travel costs.
    
    # Assumptions
    - Each drive action costs 1.
    - Pick-up and drop actions cost 1.
    - Vehicle capacity constraints are relaxed (ignored) for the heuristic, assuming vehicles will eventually free up space.
    - To prevent plateaus when a vehicle moves away from unpicked packages to deliver its cargo, 
      the remaining distance to the goal is weighted by 2, while the distance to the closest vehicle is weighted by 1.
      This ensures a strictly negative heuristic gradient when vehicles make progress on their deliveries, effectively avoiding tie-breaking dead ends.

    # Heuristic Initialization
    1. The road network and locations are parsed from `task.static` and `task.initial_state`.
    2. All-pairs shortest path distances between locations are computed using Breadth-First Search (BFS).
    3. Vehicles are identified by looking for `capacity` facts in the initial state.
    4. Goal locations for packages (and potentially vehicles) are extracted from `task.goals`.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find the locations of all vehicles and the statuses of all packages.
       - A vehicle's location is extracted from `(at ?v ?loc)`.
       - A package can be at a location `(at ?p ?loc)` or inside a vehicle `(in ?p ?v)`.
    2. Initialize `total_cost = 0`.
    3. For each package that has a goal location:
       - If it is already at its goal, cost = 0.
       - If it is inside a vehicle `v`, its cost is `2 * distance(loc(v), goal) + 1`.
         (The weight 2 ensures that delivering packages provides a steeper gradient than moving empty vehicles).
       - If it is at a location `l` (not in a vehicle), its cost is:
         `min(distance(loc(v), l) for all v) + 2 * distance(l, goal) + 2`.
    4. For any vehicle that has a specific goal location (if any), add its distance to the goal.
    5. Return the sum of costs for all goals.
    """

    def __init__(self, task):
        self.goals = task.goals
        
        # 1. Identify roads and locations
        self.roads = defaultdict(list)
        locations_set = set()
        
        for fact in task.static | task.initial_state:
            parts = get_parts(fact)
            if parts[0] == "road":
                _, l1, l2 = parts
                self.roads[l1].append(l2)
                locations_set.add(l1)
                locations_set.add(l2)
            elif parts[0] == "at":
                # Fallback to catch any isolated locations
                locations_set.add(parts[2])
                
        # 2. Compute All-Pairs Shortest Paths via BFS
        self.distances = {}
        for start in locations_set:
            dist = {start: 0}
            queue = [start]
            while queue:
                curr = queue.pop(0)
                d = dist[curr]
                for neighbor in self.roads[curr]:
                    if neighbor not in dist:
                        dist[neighbor] = d + 1
                        queue.append(neighbor)
            self.distances[start] = dist
            
        # 3. Extract vehicles
        self.vehicles = set()
        for fact in task.static | task.initial_state:
            parts = get_parts(fact)
            if parts[0] == "capacity":
                self.vehicles.add(parts[1])
                
        # 4. Extract goal locations for packages and vehicles
        self.goal_locations = {}
        self.vehicle_goals = {}
        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                if obj in self.vehicles:
                    self.vehicle_goals[obj] = loc
                else:
                    self.goal_locations[obj] = loc

    def __call__(self, node):
        state = node.state
        
        vehicle_locations = {}
        package_status = {}
        
        # Parse the current state
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                if obj in self.vehicles:
                    vehicle_locations[obj] = loc
                else:
                    package_status[obj] = ('at', loc)
            elif parts[0] == "in":
                pkg, veh = parts[1], parts[2]
                package_status[pkg] = ('in', veh)
                
        total_cost = 0
        
        # Process package goals
        for pkg, goal_loc in self.goal_locations.items():
            if pkg not in package_status:
                continue
                
            status, loc_or_veh = package_status[pkg]
            
            if status == 'at':
                current_loc = loc_or_veh
                if current_loc == goal_loc:
                    continue
                
                # Minimum distance from any vehicle to the unpicked package
                min_v_dist = float('inf')
                for v_loc in vehicle_locations.values():
                    d = self.distances.get(v_loc, {}).get(current_loc, float('inf'))
                    if d < min_v_dist:
                        min_v_dist = d
                        
                dist_to_goal = self.distances.get(current_loc, {}).get(goal_loc, float('inf'))
                
                total_cost += min_v_dist + 2 * dist_to_goal + 2
                
            elif status == 'in':
                veh = loc_or_veh
                v_loc = vehicle_locations.get(veh)
                if v_loc is None:
                    continue
                    
                dist_to_goal = self.distances.get(v_loc, {}).get(goal_loc, float('inf'))
                total_cost += 2 * dist_to_goal + 1
                
        # Process vehicle goals (if any exist)
        for veh, goal_loc in self.vehicle_goals.items():
            current_loc = vehicle_locations.get(veh)
            if current_loc and current_loc != goal_loc:
                dist = self.distances.get(current_loc, {}).get(goal_loc, float('inf'))
                total_cost += dist
                
        return total_cost
