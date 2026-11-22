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
    required to transport all packages to their respective goal locations.

    # Assumptions
    - Each package is routed to its goal via the shortest path of road connections.
    - Capacity constraints are relaxed; the heuristic assumes vehicles can carry 
      any number of packages simultaneously. Overestimating the total drives by summing individual 
      package distances is acceptable and provides a strong gradient for Greedy Best-First Search.
    - The nearest vehicle to any required pick-up location accurately represents 
      the minimal initial approach cost.

    # Heuristic Initialization
    - Parses static `road` facts to construct a directed graph of locations.
    - Computes all-pairs shortest paths using Breadth-First Search (BFS) to cache 
      minimal `drive` distances between any two locations.
    - Examines the `initial_state` to classify objects as either vehicles (if they 
      have a `capacity` fact) or packages.
    - Extracts goal locations for all packages and potential vehicle goals.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to identify the physical location of all vehicles (`at`) 
       and packages (either `at` a location or `in` a vehicle).
    2. For each package that has not yet reached its goal:
       - If it is at a location: Add 2 actions (1 for pick-up and 1 for drop) plus the 
         shortest drive distance from its current location to its goal. Record 
         its location as needing a pick-up.
       - If it is inside a vehicle: Add 1 action (for drop) plus the shortest 
         drive distance from the vehicle's current location to the package's goal.
    3. For all packages waiting at a location, compute the minimum distance from 
       any vehicle to any of these pick-up locations. Add this minimal approach 
       distance to the total cost to quickly guide vehicles towards packages.
    4. For any vehicle that has a specific goal location, add the distance from 
       its current location to its goal.
    5. Return the computed total cost. If the goal is fully reached, the cost evaluates to 0.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.static = task.static

        # 1. Build the road network from static facts
        roads = collections.defaultdict(list)
        locations = set()
        for fact in task.static:
            parts = get_parts(fact)
            if parts[0] == "road":
                l1, l2 = parts[1], parts[2]
                roads[l1].append(l2)
                locations.add(l1)
                locations.add(l2)

        # 2. Precompute all-pairs shortest paths using BFS
        self.distances = {}
        for start_loc in locations:
            queue = collections.deque([(start_loc, 0)])
            visited = {start_loc}
            while queue:
                curr, dist = queue.popleft()
                self.distances[(start_loc, curr)] = dist
                for nxt in roads[curr]:
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append((nxt, dist + 1))

        # 3. Classify objects into vehicles and packages based on initial state
        self.vehicles = set()
        for fact in task.initial_state:
            parts = get_parts(fact)
            if parts[0] == "capacity":
                # Only vehicles have capacity facts in the initial state
                self.vehicles.add(parts[1])

        self.packages = set()
        for fact in task.initial_state:
            parts = get_parts(fact)
            if parts[0] == "at":
                if parts[1] not in self.vehicles:
                    self.packages.add(parts[1])
            elif parts[0] == "in":
                # Packages can technically start inside vehicles
                self.packages.add(parts[1])

        # 4. Extract goal locations
        self.package_goals = {}
        self.vehicle_goals = {}
        for goal in task.goals:
            parts = get_parts(goal)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                if obj in self.packages:
                    self.package_goals[obj] = loc
                elif obj in self.vehicles:
                    self.vehicle_goals[obj] = loc

    def __call__(self, node):
        state = node.state

        # Track the current positions of vehicles and packages
        vehicle_locations = {}
        package_locations = {}
        package_in_vehicle = {}

        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                if obj in self.vehicles:
                    vehicle_locations[obj] = loc
                elif obj in self.packages:
                    package_locations[obj] = loc
            elif parts[0] == "in":
                pkg, veh = parts[1], parts[2]
                package_in_vehicle[pkg] = veh

        total_cost = 0
        packages_to_pickup_at = set()

        # Compute cost for packages
        for pkg, goal_loc in self.package_goals.items():
            if pkg in package_locations:
                curr_loc = package_locations[pkg]
                if curr_loc != goal_loc:
                    total_cost += 2  # 1 pick-up + 1 drop
                    total_cost += self.distances.get((curr_loc, goal_loc), 100000)
                    packages_to_pickup_at.add(curr_loc)
            
            elif pkg in package_in_vehicle:
                veh = package_in_vehicle[pkg]
                veh_loc = vehicle_locations.get(veh)
                if veh_loc:
                    total_cost += 1  # 1 drop
                    if veh_loc != goal_loc:
                        total_cost += self.distances.get((veh_loc, goal_loc), 100000)

        # Compute cost for vehicle goals (if any exist)
        for veh, goal_loc in self.vehicle_goals.items():
            veh_loc = vehicle_locations.get(veh)
            if veh_loc and veh_loc != goal_loc:
                total_cost += self.distances.get((veh_loc, goal_loc), 100000)

        # Guide vehicles towards the nearest package that needs a pick-up
        if packages_to_pickup_at and vehicle_locations:
            min_dist_to_any_pickup = 100000
            for loc in packages_to_pickup_at:
                for v_loc in vehicle_locations.values():
                    d = self.distances.get((v_loc, loc), 100000)
                    if d < min_dist_to_any_pickup:
                        min_dist_to_any_pickup = d
            
            if min_dist_to_any_pickup < 100000:
                total_cost += min_dist_to_any_pickup

        return total_cost
