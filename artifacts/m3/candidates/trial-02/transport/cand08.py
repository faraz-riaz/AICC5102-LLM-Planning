import collections
from heuristics.heuristic_base import Heuristic


def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()


class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Transport domain.

    # Summary
    This heuristic estimates the minimum number of actions required to transport 
    all target packages to their respective goal locations. It uses precomputed 
    all-pairs shortest paths for the road network to estimate travel distances.

    # Assumptions
    - Vehicles can pick up, transport, and drop off packages.
    - All action costs are assumed to be 1.
    - The capacity of the vehicles is relaxed; we assume any vehicle can 
      potentially pick up any package eventually.
    - Packages that are already at their goal locations require no further actions.
    - The shortest path distance between locations in the road network is a good 
      estimate for the number of `drive` actions.

    # Heuristic Initialization
    - Extract all vehicles from the initial state's `capacity` facts.
    - Parse the road network from the static facts (`road` predicates).
    - Collect all locations mentioned in the initial state and static facts.
    - Compute all-pairs shortest paths using Breadth-First Search (BFS) for all locations.
    - Extract the target goal location for each package from the task's goals.

    # Step-By-Step Thinking for Computing Heuristic
    For a given state, the heuristic computes the total estimated cost as follows:
    1. Parse the state to find the current locations of all packages and vehicles.
       Also track which packages are currently loaded inside which vehicles.
    2. Iterate over each package that has a specified goal location:
       - If the package is inside a vehicle:
         - Find the vehicle's current location.
         - The cost to deliver this package is the distance from the vehicle to 
           the package's goal location, plus 1 action to `drop` it.
       - If the package is at a location (not in a vehicle) and not at its goal:
         - The cost to deliver it includes:
           a) 1 `pick-up` action.
           b) The shortest path distance from its current location to its goal.
           c) 1 `drop` action.
           d) The distance required for the nearest vehicle to reach the package's 
              current location (to account for the vehicle's empty travel time).
       - If the package is already at its goal location, its cost is 0.
    3. Sum the estimated costs for all goal-directed packages.
    4. Return the total cost. If any required path is unreachable, return infinity.
    """

    def __init__(self, task):
        self.goals = task.goals
        static_facts = task.static
        initial_state = task.initial_state

        # Determine vehicles by looking for capacity predicates
        self.vehicles = set()
        for fact in initial_state | static_facts:
            parts = get_parts(fact)
            if parts[0] == "capacity":
                self.vehicles.add(parts[1])

        # Build road network and collect all unique locations
        self.roads = collections.defaultdict(list)
        self.locations = set()

        for fact in static_facts | initial_state:
            parts = get_parts(fact)
            if parts[0] == "road":
                _, l1, l2 = parts
                self.roads[l1].append(l2)
                self.locations.add(l1)
                self.locations.add(l2)
            elif parts[0] == "at":
                # Ensure we also capture locations that might not have roads connected
                self.locations.add(parts[2])

        # Compute all-pairs shortest paths using BFS (since all step costs are equal)
        self.dist = {}
        for start_loc in self.locations:
            self.dist[start_loc] = {start_loc: 0}
            queue = collections.deque([start_loc])
            while queue:
                curr = queue.popleft()
                for nxt in self.roads[curr]:
                    if nxt not in self.dist[start_loc]:
                        self.dist[start_loc][nxt] = self.dist[start_loc][curr] + 1
                        queue.append(nxt)

        # Extract goal locations for packages
        self.goal_locations = {}
        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == "at":
                pkg, loc = parts[1], parts[2]
                self.goal_locations[pkg] = loc

    def __call__(self, node):
        state = node.state
        
        current_locations = {}
        in_vehicle = {}
        vehicle_locations = []
        
        # 1. Parse the state mapping object locations and vehicle payloads
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                current_locations[obj] = loc
                if obj in self.vehicles:
                    vehicle_locations.append(loc)
            elif parts[0] == "in":
                pkg, veh = parts[1], parts[2]
                in_vehicle[pkg] = veh
                
        total_cost = 0
        
        # 2. Iterate over each package that must reach a goal location
        for pkg, goal_loc in self.goal_locations.items():
            if pkg in in_vehicle:
                veh = in_vehicle[pkg]
                veh_loc = current_locations.get(veh)
                
                if veh_loc:
                    # Cost = distance from vehicle to goal + 1 drop action
                    dist_to_goal = self.dist.get(veh_loc, {}).get(goal_loc, float('inf'))
                    total_cost += 1 + dist_to_goal  
            else:
                pkg_loc = current_locations.get(pkg)
                
                # If package is grounded and not at its goal
                if pkg_loc and pkg_loc != goal_loc:
                    dist_to_goal = self.dist.get(pkg_loc, {}).get(goal_loc, float('inf'))
                    
                    # Compute nearest vehicle to pick up the package
                    if vehicle_locations:
                        min_veh_dist = min((self.dist.get(v_loc, {}).get(pkg_loc, float('inf')) for v_loc in vehicle_locations))
                    else:
                        min_veh_dist = float('inf')
                        
                    # Cost = nearest vehicle distance + 1 pick-up + distance to goal + 1 drop
                    total_cost += 2 + dist_to_goal + min_veh_dist
                    
        return total_cost
