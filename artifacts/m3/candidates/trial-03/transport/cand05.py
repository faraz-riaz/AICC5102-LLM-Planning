from collections import deque
from heuristics.heuristic_base import Heuristic

def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()

class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Transport domain.

    # Summary
    This heuristic estimates the number of actions required to transport all goal-directed 
    packages to their respective destinations. It computes the minimal driving distance for 
    vehicles to reach packages, the distance to the goal, and the necessary pick-up and drop actions.

    # Assumptions
    - Vehicles can pick up and drop packages. Each such action takes 1 step.
    - Vehicles drive between locations along roads, and each drive takes 1 step.
    - Capacity constraints are relaxed in the heuristic computation (assuming vehicles 
      can always pick up a package when they reach it). Overestimating the distance by summing 
      over all packages still provides a strong gradient for greedy best-first search.
    - The graph of locations is static and all paths can be precomputed.

    # Heuristic Initialization
    - Parse static facts to build a graph of roads (`adj`).
    - Parse initial state facts to extract the set of valid vehicles.
    - Use Breadth-First Search (BFS) to precompute the all-pairs shortest path distances (`dist`).
    - Extract goal locations for packages (and potentially vehicles).

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find the locations of all vehicles and packages.
       Check if packages are `at` a location or `in` a vehicle.
    2. For each goal (typically a package at a target location):
       a. If it is already at the target location, the cost is 0.
       b. If the package is inside a vehicle:
          - The vehicle must drive to the goal location. Add `distance(vehicle_loc, goal_loc)`.
          - The package must be dropped. Add 1.
       c. If the package is at a location different from the goal:
          - A vehicle must drive to the package. Find the closest vehicle and add `min_v distance(v_loc, package_loc)`.
          - The package must be picked up. Add 1.
          - The vehicle must drive to the goal. Add `distance(package_loc, goal_loc)`.
          - The package must be dropped. Add 1.
       d. If the goal applies to a vehicle, simply add the distance from its current location to its goal location.
    3. Sum the estimated costs for all goals. If any location is unreachable, return infinity to indicate a dead end.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.static = task.static
        self.initial_state = task.initial_state

        # Identify vehicles from the initial state using 'capacity' facts.
        self.vehicles = set()
        for fact in self.initial_state:
            parts = get_parts(fact)
            if parts[0] == "capacity":
                self.vehicles.add(parts[1])

        self.locations = set()
        self.adj = {}

        # Add locations and connections from static road facts
        for fact in self.static:
            parts = get_parts(fact)
            if parts[0] == "road":
                l1, l2 = parts[1], parts[2]
                self.locations.add(l1)
                self.locations.add(l2)
                if l1 not in self.adj:
                    self.adj[l1] = []
                self.adj[l1].append(l2)

        # Add locations from initial state 'at' facts (in case there are isolated locations)
        for fact in self.initial_state:
            parts = get_parts(fact)
            if parts[0] == "at":
                self.locations.add(parts[2])

        # Ensure all locations exist in the adjacency list
        for loc in self.locations:
            if loc not in self.adj:
                self.adj[loc] = []

        # Precompute all-pairs shortest paths using BFS for efficiency
        self.dist = {}
        for loc in self.locations:
            self.dist[loc] = {loc: 0}
            queue = deque([loc])
            while queue:
                curr = queue.popleft()
                d = self.dist[loc][curr]
                for nxt in self.adj[curr]:
                    if nxt not in self.dist[loc]:
                        self.dist[loc][nxt] = d + 1
                        queue.append(nxt)

        # Extract goals that apply to specific objects
        self.object_goals = {}
        for fact in self.goals:
            parts = get_parts(fact)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                self.object_goals[obj] = loc

    def __call__(self, node):
        state = node.state

        obj_locations = {}
        in_vehicle = {}

        # Extract object locations and package statuses
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                obj_locations[obj] = loc
            elif parts[0] == "in":
                pkg, veh = parts[1], parts[2]
                in_vehicle[pkg] = veh

        # Retrieve locations of all available vehicles
        veh_locations = [obj_locations[v] for v in self.vehicles if v in obj_locations]

        total_cost = 0

        for obj, goal_loc in self.object_goals.items():
            if obj in self.vehicles:
                # Calculate cost for a vehicle to reach its own goal
                curr_loc = obj_locations.get(obj)
                if curr_loc and curr_loc != goal_loc:
                    d = self.dist.get(curr_loc, {}).get(goal_loc, float('inf'))
                    total_cost += d
            else:
                # Calculate cost for a package to reach its goal
                if obj in in_vehicle:
                    veh = in_vehicle[obj]
                    v_loc = obj_locations.get(veh)
                    if v_loc:
                        d = self.dist.get(v_loc, {}).get(goal_loc, float('inf'))
                        total_cost += 1 + d  # 1 action to drop
                    else:
                        total_cost += float('inf')
                else:
                    curr_loc = obj_locations.get(obj)
                    if curr_loc:
                        if curr_loc == goal_loc:
                            continue
                        else:
                            d_to_goal = self.dist.get(curr_loc, {}).get(goal_loc, float('inf'))
                            
                            # Find the distance of the closest vehicle to this package
                            min_v_dist = float('inf')
                            for v_loc in veh_locations:
                                d = self.dist.get(v_loc, {}).get(curr_loc, float('inf'))
                                if d < min_v_dist:
                                    min_v_dist = d
                                    
                            # 2 actions: 1 pick up + 1 drop
                            total_cost += 2 + d_to_goal + min_v_dist
                    else:
                        total_cost += float('inf')

        # Return computed cost or a representation of infinity if a goal is deemed unreachable
        return total_cost if total_cost != float('inf') else float('inf')
