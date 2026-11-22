from heuristics.heuristic_base import Heuristic


def extract_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()


class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the transport domain.
    
    # Summary
    This heuristic estimates the total cost of delivering all packages to their 
    destinations. To provide excellent guidance and avoid plateaus during Greedy 
    Best-First Search, it scales the delivery costs by 2 and adds the unscaled 
    distance from the closest vehicle to each unpicked package. This 2:1 ratio 
    ensures that the heuristic strictly decreases for almost all useful actions,
    effectively minimizing the number of expanded nodes.
    
    # Assumptions
    - Each vehicle can transport packages.
    - All actions (drive, pick-up, drop) have a uniform cost of 1.
    - Vehicle capacity constraints are relaxed, allowing multiple packages to be 
      considered independently, which heavily incentivizes moving vehicles towards 
      clusters of packages.
    
    # Heuristic Initialization
    - The goal locations for all packages are extracted.
    - The set of vehicles is identified from the initial state facts (using the `capacity` predicate).
    - An All-Pairs Shortest Path (APSP) matrix is precomputed using Breadth-First 
      Search over the `road` facts to allow O(1) distance lookups during evaluation.
      
    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find the locations of all vehicles and packages.
       - A package can be `at` a location or `in` a vehicle.
       - A vehicle is always `at` a location.
    2. For each package that has a goal location:
       - If the package is already at its goal location, its cost is 0.
       - If the package is currently `in` a vehicle `v`:
           Cost = 2 * (1 + distance(loc(v), goal))
           (1 action to drop, plus the driving distance to the goal, scaled by 2).
       - If the package is `at` some location `l` (and not at its goal):
           Cost = 2 * (2 + distance(l, goal)) + min_{v} distance(loc(v), l)
           (2 actions for pick-up and drop, plus the driving distance to the goal, 
           scaled by 2, plus the unscaled distance for the closest vehicle to arrive).
    3. Sum the calculated costs for all goal packages.
    4. The 2:1 scaling ensures that when a loaded vehicle moves towards its destination, 
       the total heuristic strictly decreases, even if its distance to another waiting 
       package increases. This effectively eliminates plateaus and provides strong guidance.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.goal_locations = {}
        for goal in self.goals:
            parts = extract_parts(goal)
            if parts[0] == "at":
                self.goal_locations[parts[1]] = parts[2]
                
        # Identify all vehicles from the initial state
        self.vehicles = set()
        for fact in task.initial_state:
            parts = extract_parts(fact)
            if parts[0] == "capacity":
                self.vehicles.add(parts[1])
                
        # Build the road graph
        self.adj = {}
        for fact in task.static:
            parts = extract_parts(fact)
            if parts[0] == "road":
                l1, l2 = parts[1], parts[2]
                if l1 not in self.adj: self.adj[l1] = []
                if l2 not in self.adj: self.adj[l2] = []
                self.adj[l1].append(l2)
                
        # Compute All-Pairs Shortest Path (APSP) using Breadth-First Search
        self.distances = {}
        locations = list(self.adj.keys())
        for start_node in locations:
            dist = {start_node: 0}
            queue = [start_node]
            while queue:
                curr = queue.pop(0)
                d = dist[curr]
                for neighbor in self.adj.get(curr, []):
                    if neighbor not in dist:
                        dist[neighbor] = d + 1
                        queue.append(neighbor)
            self.distances[start_node] = dist

    def get_distance(self, l1, l2):
        if l1 == l2:
            return 0
        if l1 in self.distances and l2 in self.distances[l1]:
            return self.distances[l1][l2]
        return 10000  # Large penalty for disconnected components

    def __call__(self, node):
        state = node.state
        
        # Track current locations of packages and vehicles
        package_at = {}
        package_in = {}
        vehicle_at = {}
        
        for fact in state:
            parts = extract_parts(fact)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                if obj in self.vehicles:
                    vehicle_at[obj] = loc
                else:
                    package_at[obj] = loc
            elif parts[0] == "in":
                obj, veh = parts[1], parts[2]
                package_in[obj] = veh
                
        total_cost = 0
        
        for p, g in self.goal_locations.items():
            if p in package_at and package_at[p] == g:
                # Package is safely at its goal destination
                continue
                
            if p in package_in:
                # Package is currently inside a vehicle
                veh = package_in[p]
                veh_loc = vehicle_at.get(veh)
                if veh_loc:
                    dist = self.get_distance(veh_loc, g)
                    total_cost += 2 * (1 + dist)
                else:
                    total_cost += 10000  # Fallback for an invalid state
            elif p in package_at:
                # Package is waiting at a location
                loc = package_at[p]
                dist_to_goal = self.get_distance(loc, g)
                
                # Find the distance from the closest vehicle
                min_v_dist = 10000
                for v in self.vehicles:
                    v_loc = vehicle_at.get(v)
                    if v_loc:
                        v_dist = self.get_distance(v_loc, loc)
                        if v_dist < min_v_dist:
                            min_v_dist = v_dist
                            
                total_cost += 2 * (2 + dist_to_goal) + min_v_dist
                
        return total_cost
