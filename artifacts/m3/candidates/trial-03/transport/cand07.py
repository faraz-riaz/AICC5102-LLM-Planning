from collections import deque
from fnmatch import fnmatch
from heuristics.heuristic_base import Heuristic


def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()


def match(fact, *args):
    """Check if a PDDL fact matches a given pattern."""
    parts = get_parts(fact)
    return all(fnmatch(part, arg) for part, arg in zip(parts, args))


class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Transport domain.
    
    # Summary
    This heuristic estimates the minimum number of actions required to transport
    all packages to their respective goal locations. It uses a relaxed distance 
    measure that effectively tracks the remaining steps for each package and 
    provides a strictly decreasing gradient to guide the search.
    
    # Assumptions
    - Packages need to be picked up, transported, and dropped at their goals.
    - Capacity constraints of vehicles are relaxed (we assume any vehicle can 
      transport the package without needing to track its precise capacity).
    - Costs are scaled (by a factor of 2 for most actions) to create a strictly 
      decreasing gradient when a vehicle moves towards a package. This prevents 
      plateaus in the heuristic surface when an empty vehicle needs to drive to 
      a package.

    # Heuristic Initialization
    - Parses `road` facts to build a directed graph of locations.
    - Computes all-pairs shortest paths using BFS to determine the minimum number
      of `drive` actions between any two locations.
    - Identifies all vehicles based on `capacity` facts from the initial state 
      and static facts.
    - Extracts the goal locations for all packages.
    
    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find the locations of all vehicles and packages.
       Also, track which packages are currently inside which vehicles (`in` facts).
    2. For each package that has a goal location:
       a. If the package is already at its goal location, its cost is 0.
       b. If the package is currently inside a vehicle:
          - It requires 1 `drop` action.
          - The vehicle must `drive` to the goal location.
          - To maintain integer arithmetic and a strict gradient, this is scaled 
            as `2 + 2 * distance_to_goal`.
       c. If the package is at a location (not in a vehicle) and not at the goal:
          - It requires 1 `pick-up` action, 1 `drop` action, and a `drive` to the goal.
          - Additionally, the closest vehicle needs to `drive` to the package's location.
          - This is computed as `4 + 2 * distance_to_goal + distance_from_closest_vehicle`.
    3. Sum the computed costs for all packages. The scaling ensures that moving a 
       vehicle towards an unfulfilled package strictly decreases the overall heuristic 
       value, avoiding aimless wandering during the search.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.static = task.static

        # 1. Build the road graph
        locations = set()
        for fact in list(self.static) + list(task.initial_state):
            parts = get_parts(fact)
            if parts[0] == "road":
                locations.add(parts[1])
                locations.add(parts[2])

        self.adj = {l: [] for l in locations}
        for fact in list(self.static) + list(task.initial_state):
            parts = get_parts(fact)
            if parts[0] == "road":
                self.adj[parts[1]].append(parts[2])

        # 2. Compute all-pairs shortest path distances
        self.dist = {}
        for start_node in locations:
            self.dist[start_node] = {start_node: 0}
            queue = deque([start_node])
            while queue:
                curr = queue.popleft()
                d = self.dist[start_node][curr]
                for nxt in self.adj[curr]:
                    if nxt not in self.dist[start_node]:
                        self.dist[start_node][nxt] = d + 1
                        queue.append(nxt)

        # 3. Identify all vehicles
        self.vehicles = set()
        for fact in list(self.static) + list(task.initial_state):
            parts = get_parts(fact)
            if parts[0] == "capacity":
                self.vehicles.add(parts[1])

        # 4. Extract goal locations
        self.goal_locations = {}
        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == "at":
                self.goal_locations[parts[1]] = parts[2]

    def __call__(self, node):
        state = node.state
        
        obj_loc = {}
        in_vehicle = {}
        
        # Parse current state facts
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                obj_loc[parts[1]] = parts[2]
            elif parts[0] == "in":
                in_vehicle[parts[1]] = parts[2]
                
        # Find locations of all vehicles
        v_locs = [obj_loc[v] for v in self.vehicles if v in obj_loc]
        
        total_cost = 0
        
        # Compute cost for each package based on its goal
        for p, g in self.goal_locations.items():
            if p in in_vehicle:
                # Package is currently in a vehicle
                v = in_vehicle[p]
                v_loc = obj_loc.get(v)
                if v_loc:
                    dist_to_goal = self.dist.get(v_loc, {}).get(g, 1000)
                    total_cost += 2 + 2 * dist_to_goal
            else:
                # Package is at some physical location (not in a vehicle)
                l = obj_loc.get(p)
                if l == g:
                    continue  # Goal reached for this package
                if l:
                    dist_to_goal = self.dist.get(l, {}).get(g, 1000)
                    closest_v_dist = min([self.dist.get(vl, {}).get(l, 1000) for vl in v_locs]) if v_locs else 1000
                    total_cost += 4 + 2 * dist_to_goal + closest_v_dist
                    
        return total_cost
