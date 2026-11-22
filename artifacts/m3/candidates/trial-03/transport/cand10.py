from collections import defaultdict, deque
from fnmatch import fnmatch
from heuristics.heuristic_base import Heuristic

def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()

class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Transport domain.

    # Summary
    This heuristic estimates the minimum number of actions required to transport all 
    packages to their respective goal locations. It computes shortest path distances 
    between all locations and uses them to guide vehicles to unpicked packages, and 
    carried packages to their final destinations, avoiding local minima.

    # Assumptions
    - Action costs are uniform (pick-up, drop, and drive each cost 1 step).
    - Capacity constraints are relaxed in the heuristic computation to ensure 
      smooth gradients without having to track exact vehicle capacities or sizes. 
    - Graph connectivity is static and explicitly defined by `road` predicates.

    # Heuristic Initialization
    - Parses both `static` facts and `initial_state` to extract all locations and 
      the directed road network.
    - Uses Breadth-First Search (BFS) to compute the All-Pairs Shortest Path (APSP) 
      distances between all locations.
    - Identifies all vehicles based on the presence of `capacity` predicates.
    - Extracts the goal locations for all objects (mostly packages).

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to identify the exact locations of all vehicles and 
       packages. Note that packages can either be at a location on the ground or 
       inside a vehicle.
    2. Evaluate the base cost for each goal-oriented package:
       - If the package is currently at its goal location, its cost is 0.
       - If it is at a non-goal location, add the distance to its goal plus 2 
         (representing one `pick-up` and one `drop` action). Mark it as "unpicked".
       - If it is inside a vehicle, add the distance from the vehicle's current 
         location to the goal plus 1 (representing the final `drop` action).
    3. Guide Vehicles to Unpicked Packages:
       - For each "unpicked" package, find the shortest distance to any available 
         vehicle. Summing these minimum approach distances across all unpicked 
         packages generates a strictly non-increasing gradient. 
       - This elegant mathematical property ensures vehicles are eagerly driven 
         towards packages without creating heuristic jumps (local minima) when a 
         vehicle picks up a package or when a vehicle temporarily drives away from 
         other unpicked packages to fulfill a delivery.
    4. Return the aggregated total cost. Unsolvable/disconnected configurations are 
       safely penalized with a large arbitrary constant (10000).
    """

    def __init__(self, task):
        self.goal_locations = {}
        for goal in task.goals:
            parts = get_parts(goal)
            if parts[0] == "at":
                self.goal_locations[parts[1]] = parts[2]

        # Extract all locations and roads
        roads = defaultdict(list)
        locations = set()
        
        for fact in task.static:
            parts = get_parts(fact)
            if parts[0] == "road":
                roads[parts[1]].append(parts[2])
                locations.add(parts[1])
                locations.add(parts[2])
            elif parts[0] == "at":
                locations.add(parts[2])

        for fact in task.initial_state:
            parts = get_parts(fact)
            if parts[0] == "road":
                roads[parts[1]].append(parts[2])
                locations.add(parts[1])
                locations.add(parts[2])
            elif parts[0] == "at":
                locations.add(parts[2])

        # Extract vehicles
        self.vehicles = set()
        for fact in task.static:
            parts = get_parts(fact)
            if parts[0] == "capacity":
                self.vehicles.add(parts[1])
                
        for fact in task.initial_state:
            parts = get_parts(fact)
            if parts[0] == "capacity":
                self.vehicles.add(parts[1])

        # Compute All-Pairs Shortest Paths (APSP) with BFS
        self.distances = defaultdict(dict)
        for start_node in locations:
            self.distances[start_node][start_node] = 0
            queue = deque([start_node])
            while queue:
                curr = queue.popleft()
                dist = self.distances[start_node][curr]
                for neighbor in roads[curr]:
                    if neighbor not in self.distances[start_node]:
                        self.distances[start_node][neighbor] = dist + 1
                        queue.append(neighbor)

    def __call__(self, node):
        state = node.state

        package_locations = {}
        vehicle_locations = {}
        package_in_vehicle = {}

        # Parse locations of all elements in the current state
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                if obj in self.vehicles:
                    vehicle_locations[obj] = loc
                else:
                    package_locations[obj] = loc
            elif parts[0] == "in":
                obj, veh = parts[1], parts[2]
                package_in_vehicle[obj] = veh

        total_cost = 0
        unpicked_packages = []

        # Step 1: Base costs of completing each goal
        for obj, g_loc in self.goal_locations.items():
            if obj in self.vehicles:
                # If a vehicle itself has a specific goal location
                v_loc = vehicle_locations.get(obj)
                if v_loc and v_loc != g_loc:
                    total_cost += self.distances.get(v_loc, {}).get(g_loc, 10000)
            else:
                if obj in package_locations:
                    p_loc = package_locations[obj]
                    if p_loc != g_loc:
                        # Ground package: Needs 1 pick-up + distance to goal + 1 drop
                        total_cost += self.distances.get(p_loc, {}).get(g_loc, 10000) + 2
                        unpicked_packages.append(p_loc)
                elif obj in package_in_vehicle:
                    veh = package_in_vehicle[obj]
                    v_loc = vehicle_locations.get(veh)
                    if v_loc:
                        # In vehicle package: Needs distance to goal + 1 drop
                        total_cost += self.distances.get(v_loc, {}).get(g_loc, 10000) + 1
                    else:
                        total_cost += 10000
                else:
                    # Missing or untracked element defaults to heavy penalty
                    total_cost += 10000

        # Step 2: Tie-breaking gradient to drive vehicles towards unpicked packages
        if unpicked_packages:
            if vehicle_locations:
                for p_loc in unpicked_packages:
                    # Safely map out the distance from the closest vehicle to this particular unpicked package
                    min_d = min(
                        self.distances.get(v_loc, {}).get(p_loc, 10000)
                        for v_loc in vehicle_locations.values()
                    )
                    total_cost += min_d
            else:
                # If there are unpicked packages but no vehicles available
                total_cost += 10000 * len(unpicked_packages)

        return total_cost
