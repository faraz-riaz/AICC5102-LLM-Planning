from heuristics.heuristic_base import Heuristic


def get_parts(fact):
    """
    Extract the components of a PDDL fact by removing parentheses and splitting the string.
    """
    return fact[1:-1].split()


class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Transport domain.
    
    # Summary
    This heuristic estimates the minimum number of required actions (drive, pick-up, drop) to transport all target packages to their goal locations. By computing the shortest path distances between locations in the road network, it aggregates the cost for each package based on its current position and vehicle status.
    
    # Assumptions
    - Only vehicles and packages are locatable objects. Vehicles have 'capacity', and packages can be inside vehicles ('in') or at locations ('at').
    - The shortest path distance provides an effective gradient for estimating the 'drive' action costs.
    - Capacity constraints can be relaxed in the heuristic calculation. To strongly encourage the search to approach unpicked packages and batch them into vehicles, we apply a greedy TSP for packages already in transit, and sum minimum approach distances for packages waiting at locations.
    
    # Heuristic Initialization
    - Extract the road network from both the initial state and static facts to build a directed adjacency list.
    - Identify all locations and initialize statically known vehicles.
    - Compute all-pairs shortest path distances using Breadth-First Search (BFS).
    - Extract the goal locations for each package.
    
    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to determine the locations of all vehicles and packages, and map which packages are inside which vehicles. We dynamically identify vehicles by observing `capacity` facts.
    2. For packages currently inside a vehicle:
       - The vehicle must eventually drive to the goals of all its loaded packages.
       - We approximate this driving cost using a Greedy Traveling Salesperson (TSP) approach, starting from the vehicle's current location and visiting all unique goals of its loaded packages.
       - We add 1 action for dropping each loaded package.
    3. For packages currently waiting at a location (not yet at their goal):
       - We add the shortest distance from the package's current location to its goal.
       - We add 2 actions (1 for pick-up, 1 for drop).
       - We add the distance of the closest vehicle to the package's current location to simulate the cost of a vehicle traveling to pick it up. Adding this for *each* unpicked package creates a steep gradient that strongly attracts vehicles towards packages, heavily reducing node expansions in Greedy Best-First Search.
    4. Return the sum of all these costs. If all packages are at their goals, the heuristic appropriately returns 0.
    """

    def __init__(self, task):
        self.goals = task.goals
        
        self.static_vehicles = set()
        self.adj = {}
        self.locations = set()
        
        # Combine static facts and initial state to reliably extract constants like roads and starting elements
        all_facts = task.static | task.initial_state
        
        for fact in all_facts:
            parts = get_parts(fact)
            if parts[0] == "capacity":
                self.static_vehicles.add(parts[1])
            elif parts[0] == "road":
                l1, l2 = parts[1], parts[2]
                self.adj.setdefault(l1, set()).add(l2)
                self.locations.add(l1)
                self.locations.add(l2)
            elif parts[0] == "at":
                self.locations.add(parts[2])
                
        # Extract goals for packages
        self.package_goals = {}
        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == "at":
                p, l = parts[1], parts[2]
                self.package_goals[p] = l
                self.locations.add(l)
                
        # Compute all-pairs shortest paths using BFS
        self.distances = {}
        for start in self.locations:
            self.distances[start] = self._bfs(start)

    def _bfs(self, start):
        """
        Compute shortest path distances from a start location to all reachable locations.
        Assumes uniform edge cost (1 drive action per road).
        """
        distances = {start: 0}
        queue = [start]
        while queue:
            curr = queue.pop(0)
            for neighbor in self.adj.get(curr, set()):
                if neighbor not in distances:
                    distances[neighbor] = distances[curr] + 1
                    queue.append(neighbor)
        return distances

    def __call__(self, node):
        state = node.state
        
        vehicles = set(self.static_vehicles)
        package_locations = {}
        vehicle_locations = {}
        package_in_vehicle = {}
        
        # 1. First pass: Identify all current vehicles based on their capacity fluents
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "capacity":
                vehicles.add(parts[1])
                
        # 2. Second pass: Retrieve entity positions using the parsed vehicle set
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                x, l = parts[1], parts[2]
                if x in vehicles:
                    vehicle_locations[x] = l
                else:
                    package_locations[x] = l
            elif parts[0] == "in":
                p, v = parts[1], parts[2]
                package_in_vehicle[p] = v
                
        cost = 0
        
        # 3. Calculate heuristic cost for packages already in transit
        vehicle_packages = {}
        for p, v in package_in_vehicle.items():
            if p in self.package_goals:
                vehicle_packages.setdefault(v, []).append(p)
                
        for v, p_list in vehicle_packages.items():
            v_loc = vehicle_locations.get(v)
            if v_loc is None:
                continue
            
            # Greedy TSP to approximate vehicle routing for delivering loaded packages
            goals = list(set(self.package_goals[p] for p in p_list))
            curr_loc = v_loc
            unvisited = set(goals)
            while unvisited:
                closest = min(unvisited, key=lambda g: self.distances.get(curr_loc, {}).get(g, 10000))
                cost += self.distances.get(curr_loc, {}).get(closest, 10000)
                curr_loc = closest
                unvisited.remove(closest)
                
            # Add action costs for dropping each package
            cost += len(p_list) 
            
        # 4. Calculate heuristic cost for packages waiting at a location
        for p, g in self.package_goals.items():
            if p in package_in_vehicle:
                continue
                
            p_loc = package_locations.get(p)
            if p_loc is not None and p_loc != g:
                # Minimum driving distance to goal + 1 pick-up action + 1 drop action
                cost += self.distances.get(p_loc, {}).get(g, 10000) + 2
                
                # Minimum distance for *some* vehicle to come and pick this package up
                if vehicles:
                    min_v_dist = min((self.distances.get(vehicle_locations.get(v), {}).get(p_loc, 10000) 
                                      for v in vehicles if vehicle_locations.get(v) is not None), default=10000)
                    cost += min_v_dist
                    
        return cost
