import collections
from heuristics.heuristic_base import Heuristic

def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()

class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Transport domain.

    # Summary
    This heuristic estimates the number of actions required to deliver all packages to their goal locations. It relaxes the problem by ignoring vehicle capacities (similar to delete-relaxation), providing a smooth and highly informative gradient for greedy best-first search.

    # Assumptions
    - The problem is relaxed by assuming vehicles have infinite capacity. This avoids heuristic jumps when vehicles become temporarily full.
    - Each package is evaluated independently.
    - The estimated cost to deliver a single package is the sum of:
      - Moving the nearest vehicle to the package (if the package is not yet picked up).
      - Picking up the package (1 action).
      - Driving from the package's location to its goal location.
      - Dropping the package at the goal (1 action).

    # Heuristic Initialization
    - Parses the static and initial state facts to build a directed graph of roads.
    - Computes all-pairs shortest path distances between all locations using Breadth-First Search (BFS).
    - Identifies all vehicles from the initial state by looking for `capacity` facts.
    - Extracts the goal locations for all packages.

    # Step-By-Step Thinking for Computing Heuristic
    1. Identify the current location of all vehicles and packages from the state.
    2. For each package that has a goal location:
       a. If the package is currently at its goal location, its cost contribution is 0.
       b. If the package is at some location (and not its goal):
          - Find the minimum distance from any vehicle's current location to the package's location.
          - Add this minimum distance, plus 1 (for pick-up), plus the driving distance from the package to its goal, plus 1 (for drop).
       c. If the package is currently inside a vehicle:
          - Add the driving distance from the vehicle's current location to the package's goal, plus 1 (for drop).
    3. Sum the estimated costs for all goal packages and return this total.
    """

    def __init__(self, task):
        self.goals = task.goals
        
        # Parse road network
        self.adj = collections.defaultdict(list)
        locations = set()
        
        for fact in list(task.static) + list(task.initial_state):
            parts = get_parts(fact)
            if parts[0] == "road":
                l1, l2 = parts[1], parts[2]
                self.adj[l1].append(l2)
                locations.add(l1)
                locations.add(l2)
                
        # Precompute all-pairs shortest paths using BFS
        self.distances = {}
        for node in locations:
            self.distances[node] = {}
            queue = collections.deque([(node, 0)])
            visited = set([node])
            while queue:
                curr, dist = queue.popleft()
                self.distances[node][curr] = dist
                
                for neighbor in self.adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, dist + 1))
                        
        # Identify all vehicles (vehicles are the only locatables with capacity)
        self.vehicles = set()
        for fact in list(task.static) + list(task.initial_state):
            parts = get_parts(fact)
            if parts[0] == "capacity":
                self.vehicles.add(parts[1])
                
        # Identify goal locations for packages
        self.goal_locations = {}
        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == "at":
                self.goal_locations[parts[1]] = parts[2]
                
    def get_distance(self, l1, l2):
        """Return the precomputed shortest path distance between two locations."""
        if l1 == l2:
            return 0
        return self.distances.get(l1, {}).get(l2, 10000)

    def __call__(self, node):
        state = node.state
        
        at_loc = {}
        in_vehicle = {}
        
        # Parse current state
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                at_loc[parts[1]] = parts[2]
            elif parts[0] == "in":
                in_vehicle[parts[1]] = parts[2]
                
        # Extract vehicle locations
        vehicle_locations = []
        for v in self.vehicles:
            if v in at_loc:
                vehicle_locations.append(at_loc[v])
                
        total_cost = 0
        
        # Calculate cost for each package that has a goal
        for p, g_loc in self.goal_locations.items():
            if p in at_loc:
                p_loc = at_loc[p]
                
                if p_loc == g_loc:
                    # Package is already at its goal location
                    continue
                
                # Minimum distance to get a vehicle to the package
                if vehicle_locations:
                    min_v_dist = min(self.get_distance(v_loc, p_loc) for v_loc in vehicle_locations)
                else:
                    min_v_dist = 10000
                    
                drive_dist = self.get_distance(p_loc, g_loc)
                total_cost += min_v_dist + 1 + drive_dist + 1
                
            elif p in in_vehicle:
                v = in_vehicle[p]
                v_loc = at_loc.get(v, None)
                if v_loc:
                    drive_dist = self.get_distance(v_loc, g_loc)
                    total_cost += drive_dist + 1
                else:
                    total_cost += 10000
            else:
                # Package is in an unknown state (should not happen in valid states)
                total_cost += 10000
                
        return total_cost
