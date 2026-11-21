from collections import defaultdict, deque
from heuristics.heuristic_base import Heuristic

def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()

class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the transport domain.

    # Summary
    This heuristic estimates the minimum number of actions required to transport 
    each package to its goal location. It also accounts for the goals of vehicles if any.

    # Assumptions
    - Vehicles can move between locations connected by a road.
    - Packages need to be picked up, transported, and dropped off.
    - Capacity constraints exist: a vehicle cannot pick up a package if it has 
      reached its lowest capacity size (zero capacity).
    - A sum of individual package transport costs gives a strong directional gradient.

    # Heuristic Initialization
    - Extract all road connections to build a graph of locations.
    - Identify all isolated and connected locations from the initial state and static facts.
    - Compute all-pairs shortest paths between locations using Breadth-First Search (BFS) 
      since all road movements have a uniform cost of 1 action.
    - Identify all vehicles from the `capacity` facts in the initial state.
    - Identify the "zero" capacity size by looking at the `capacity-predecessor` facts. 
      The smallest size is the one that has no predecessor.
    - Store the specific goal locations for each package (or vehicle).

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find the locations of all vehicles and packages, 
       as well as the current capacity of each vehicle.
       - A package can either be at a location (`at ?p ?l`) or inside a vehicle (`in ?p ?v`).
    2. Identify which vehicles are completely full (i.e., they are currently at the zero capacity size).
    3. For each goal (package or vehicle), calculate the cost to satisfy it:
       - If it's a vehicle and it's not at its goal, add the driving distance.
       - If it's a package currently inside a vehicle, add the vehicle's driving distance 
         to the goal, plus 1 for the drop action.
       - If it's a package at a location (and not its goal), add the driving distance 
         from its current location to the goal, plus 2 (for pick-up and drop actions).
         Additionally, add the minimum distance from any NON-FULL vehicle to the package's 
         current location. This ensures that the heuristic value strictly decreases 
         as an available vehicle approaches the package to pick it up, avoiding search plateaus.
    4. Sum the estimated costs for all goals. If an object is already at its goal, 
       it contributes 0 to the heuristic for that goal.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.static = task.static
        self.initial_state = task.initial_state

        # Parse locations and roads
        self.roads = defaultdict(list)
        self.locations = set()
        
        all_s1 = set()
        all_s2 = set()
        
        self.vehicles = set()
        
        for fact in self.static | self.initial_state:
            parts = get_parts(fact)
            if parts[0] == "road":
                _, l1, l2 = parts
                self.roads[l1].append(l2)
                self.locations.add(l1)
                self.locations.add(l2)
            elif parts[0] == "capacity":
                self.vehicles.add(parts[1])
            elif parts[0] == "capacity-predecessor":
                all_s1.add(parts[1])
                all_s2.add(parts[2])
            elif parts[0] == "at":
                self.locations.add(parts[2])

        # Map objects to their goal locations and ensure all goal locations are known
        self.goal_locations = {}
        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == "at":
                _, obj, loc = parts
                self.goal_locations[obj] = loc
                self.locations.add(loc)

        # The size with no smaller predecessor is the zero capacity
        self.zero_capacities = all_s1 - all_s2

        # Compute all-pairs shortest paths
        self.distances = {}
        for start_loc in self.locations:
            self.distances[start_loc] = self._compute_bfs(start_loc)

    def _compute_bfs(self, start):
        dist = {start: 0}
        queue = deque([start])
        while queue:
            curr = queue.popleft()
            d = dist[curr]
            for neighbor in self.roads[curr]:
                if neighbor not in dist:
                    dist[neighbor] = d + 1
                    queue.append(neighbor)
        return dist

    def __call__(self, node):
        state = node.state
        
        at_locations = {}
        in_vehicle = {}
        full_vehicles = set()
        
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                at_locations[obj] = loc
            elif parts[0] == "in":
                pkg, vehicle = parts[1], parts[2]
                in_vehicle[pkg] = vehicle
            elif parts[0] == "capacity":
                vehicle, size = parts[1], parts[2]
                if size in self.zero_capacities:
                    full_vehicles.add(vehicle)
                
        total_cost = 0
        
        # Pre-extract vehicle locations to avoid multiple dict lookups
        vehicle_locations = {v: at_locations[v] for v in self.vehicles if v in at_locations}
        
        for obj, goal_loc in self.goal_locations.items():
            if obj in self.vehicles:
                # Goal is for a vehicle
                curr_loc = at_locations.get(obj)
                if curr_loc and curr_loc != goal_loc:
                    d = self.distances.get(curr_loc, {}).get(goal_loc, 1000)
                    total_cost += d
            else:
                # Goal is for a package
                if obj in in_vehicle:
                    vehicle = in_vehicle[obj]
                    v_loc = vehicle_locations.get(vehicle)
                    if v_loc:
                        d = self.distances.get(v_loc, {}).get(goal_loc, 1000)
                        total_cost += d
                        total_cost += 1  # Cost to drop the package
                else:
                    curr_loc = at_locations.get(obj)
                    if curr_loc and curr_loc != goal_loc:
                        d = self.distances.get(curr_loc, {}).get(goal_loc, 1000)
                        total_cost += d
                        total_cost += 2  # Cost to pick up and drop the package
                        
                        # Find the closest NON-FULL vehicle to this package
                        min_v_dist = 1000
                        for v, v_loc in vehicle_locations.items():
                            if v in full_vehicles:
                                continue
                            dist = self.distances.get(v_loc, {}).get(curr_loc, 1000)
                            if dist < min_v_dist:
                                min_v_dist = dist
                        
                        if min_v_dist < 1000 and min_v_dist > 0:
                            total_cost += min_v_dist
                            
        return total_cost
