from fnmatch import fnmatch
from heuristics.heuristic_base import Heuristic

def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting."""
    return fact[1:-1].split()

class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Transport domain.

    # Summary
    This heuristic estimates the total number of actions (drive, pick-up, drop) 
    required to deliver all packages to their respective goal locations. 

    # Assumptions
    - The heuristic treats each package independently, summing up their estimated individual delivery costs. While this may overestimate the cost if multiple packages are transported together, it provides a strong gradient for greedy best-first search, pulling vehicles towards locations with multiple unpicked packages and loaded vehicles towards their destinations.
    - Capacity constraints are relaxed; the heuristic assumes a vehicle will have or can make space to pick up the package.
    - Vehicles will drive along the shortest path in the road network.
    
    # Heuristic Initialization
    - Extract all vehicles from the initial state's and static's `capacity` facts.
    - Extract the road network graph from the static and initial facts.
    - Precompute all-pairs shortest paths using BFS to determine the minimum driving distance between any two locations.
    - Identify package and vehicle goals from the task goals.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find the locations of all packages and vehicles. 
       - Packages can be at a physical location or inside a vehicle.
    2. For each package that has a goal location:
       - If it is already at its goal location, its cost is 0.
       - If it is inside a vehicle, the cost is the driving distance from the vehicle's current location to the package's goal, plus 1 for the `drop` action.
       - If it is at a location different from its goal, the cost includes:
         - 1 for `pick-up`.
         - 1 for `drop`.
         - The driving distance from the package's current location to its goal.
         - The driving distance of the nearest vehicle to the package's current location (to account for the vehicle coming to fetch the package).
    3. For any vehicles with explicit goal locations, add the driving distance from their current location to their goal.
    4. Sum these estimated costs across all goals and return the total.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.static = task.static
        self.initial_state = task.initial_state

        # 1. Identify all vehicles. In the transport domain, vehicles always have a capacity fact.
        self.vehicles = set()
        for fact in self.initial_state | self.static:
            parts = get_parts(fact)
            if parts[0] == "capacity":
                self.vehicles.add(parts[1])

        # 2. Build the road network graph.
        self.adj = {}
        for fact in self.initial_state | self.static:
            parts = get_parts(fact)
            if parts[0] == "road":
                u, v = parts[1], parts[2]
                if u not in self.adj:
                    self.adj[u] = []
                if v not in self.adj:
                    self.adj[v] = []
                self.adj[u].append(v)

        # 3. Precompute all-pairs shortest paths (APSP) using Breadth-First Search.
        self.dist = {}
        for start_node in self.adj:
            self.dist[start_node] = {start_node: 0}
            queue = [start_node]
            while queue:
                curr = queue.pop(0)
                d = self.dist[start_node][curr]
                for neighbor in self.adj.get(curr, []):
                    if neighbor not in self.dist[start_node]:
                        self.dist[start_node][neighbor] = d + 1
                        queue.append(neighbor)

        # 4. Extract goal locations for packages and vehicles.
        self.package_goals = {}
        self.vehicle_goals = {}
        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == "at":
                entity, loc = parts[1], parts[2]
                if entity in self.vehicles:
                    self.vehicle_goals[entity] = loc
                else:
                    self.package_goals[entity] = loc

    def get_dist(self, u, v):
        """Return the precomputed shortest path distance between u and v."""
        if u == v:
            return 0
        if u in self.dist and v in self.dist[u]:
            return self.dist[u][v]
        return 10000  # Large penalty if unreachable to prevent infinite values but still penalize heavily.

    def __call__(self, node):
        state = node.state

        # Map entities to their current physical or vehicle locations.
        loc = {}
        in_veh = {}

        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                loc[parts[1]] = parts[2]
            elif parts[0] == "in":
                in_veh[parts[1]] = parts[2]

        total_cost = 0

        # Calculate cost for vehicle goals (if there are any explicit vehicle goals).
        for v, g in self.vehicle_goals.items():
            v_loc = loc.get(v)
            if v_loc:
                total_cost += self.get_dist(v_loc, g)

        # Calculate cost for package goals.
        for p, g in self.package_goals.items():
            if p in in_veh:
                # Package is currently inside a vehicle.
                v = in_veh[p]
                v_loc = loc.get(v)
                if v_loc:
                    # Cost = drop action (1) + driving distance from vehicle to goal.
                    total_cost += 1 + self.get_dist(v_loc, g)
            else:
                # Package is currently at some location.
                p_loc = loc.get(p)
                if p_loc and p_loc != g:
                    # Find the distance to the nearest vehicle.
                    min_v_dist = 10000
                    for v in self.vehicles:
                        v_loc = loc.get(v)
                        if v_loc:
                            d = self.get_dist(v_loc, p_loc)
                            if d < min_v_dist:
                                min_v_dist = d
                    
                    # Cost = pick-up (1) + drop (1) + driving to goal + vehicle driving to package.
                    total_cost += 2 + self.get_dist(p_loc, g) + min_v_dist

        return total_cost
