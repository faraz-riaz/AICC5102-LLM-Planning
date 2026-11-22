from collections import deque
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
    - Each package must be picked up, transported, and dropped at its goal.
    - Capacity constraints are relaxed (ignored) for the purpose of the heuristic, 
      assuming each package could theoretically be delivered independently.
    - The road network provides the minimum travel distance between any two locations.
    - If a package is already in a vehicle, the pick-up action is already completed.
    
    # Heuristic Initialization
    - Identifies all vehicles and their initial locations from the initial state.
    - Identifies the goal locations for all packages (and vehicles, if any).
    - Extracts the road network and computes the all-pairs shortest paths using BFS.
      This allows O(1) lookups for the minimum number of drive actions between any two locations.

    # Step-By-Step Thinking for Computing Heuristic
    1. Check the current location of each package that has a goal.
    2. If the package is at its goal location, its added cost is 0.
    3. If the package is at a different location (not yet in a vehicle):
       - It requires at least 1 pick-up action.
       - It requires at least 1 drop action at the goal.
       - It requires drive actions equal to the shortest path from its current location to its goal.
       - Track this location as a "pickup location" because a vehicle needs to drive there.
    4. If the package is currently in a vehicle:
       - It requires 1 drop action.
       - It requires drive actions equal to the shortest path from the vehicle's current location to the goal.
    5. For all tracked "pickup locations", find the distance to the closest vehicle and add it to the cost. 
       This accounts for the fact that a vehicle must travel to the package before picking it up.
    6. Return the total summed cost. If any goal is unreachable based on the road network, add a high penalty.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.static = task.static

        self.locations = set()
        self.roads = []
        
        # Extract locations and roads from static facts
        for fact in self.static:
            parts = get_parts(fact)
            if parts[0] == "road":
                l1, l2 = parts[1], parts[2]
                self.roads.append((l1, l2))
                self.locations.add(l1)
                self.locations.add(l2)

        # Identify vehicles from initial state (they have a capacity predicate)
        self.vehicles = set()
        for fact in task.initial_state:
            parts = get_parts(fact)
            if parts[0] == "capacity":
                self.vehicles.add(parts[1])
            elif parts[0] == "at":
                # Ensure all dynamic locations are captured
                self.locations.add(parts[2])

        # Separate package goals and vehicle goals
        self.package_goals = {}
        self.vehicle_goals = {}
        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                if obj in self.vehicles:
                    self.vehicle_goals[obj] = loc
                else:
                    self.package_goals[obj] = loc

        # Build adjacency list for the road network
        self.adj = {l: [] for l in self.locations}
        for l1, l2 in self.roads:
            self.adj[l1].append(l2)

        # Compute All-Pairs Shortest Paths (APSP) using BFS
        self.dist = {}
        for l in self.locations:
            self.dist[l] = {loc: float('inf') for loc in self.locations}
            self.dist[l][l] = 0
            
            queue = deque([l])
            while queue:
                curr = queue.popleft()
                d = self.dist[l][curr]
                for nxt in self.adj[curr]:
                    if self.dist[l][nxt] == float('inf'):
                        self.dist[l][nxt] = d + 1
                        queue.append(nxt)

    def __call__(self, node):
        state = node.state
        
        # Track locations of packages and vehicles
        obj_locations = {}
        in_vehicle = {}
        vehicle_locations = {}
        
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                obj, loc = parts[1], parts[2]
                obj_locations[obj] = loc
                if obj in self.vehicles:
                    vehicle_locations[obj] = loc
            elif parts[0] == "in":
                pkg, veh = parts[1], parts[2]
                in_vehicle[pkg] = veh
                
        total_cost = 0
        pickup_locations = set()
        
        # Compute cost for package goals
        for pkg, goal_loc in self.package_goals.items():
            if pkg in obj_locations:
                current_loc = obj_locations[pkg]
                if current_loc != goal_loc:
                    d = self.dist.get(current_loc, {}).get(goal_loc, float('inf'))
                    if d != float('inf'):
                        total_cost += d + 2  # 1 pick-up + 1 drop + travel distance
                        pickup_locations.add(current_loc)
                    else:
                        total_cost += 1000  # Penalty for unreachable goal
            elif pkg in in_vehicle:
                veh = in_vehicle[pkg]
                veh_loc = vehicle_locations.get(veh)
                if veh_loc:
                    d = self.dist.get(veh_loc, {}).get(goal_loc, float('inf'))
                    if d != float('inf'):
                        total_cost += d + 1  # 1 drop + travel distance
                    else:
                        total_cost += 1000

        # Compute cost for vehicles reaching their respective pickup locations
        for loc in pickup_locations:
            min_dist = float('inf')
            for veh, veh_loc in vehicle_locations.items():
                d = self.dist.get(veh_loc, {}).get(loc, float('inf'))
                if d < min_dist:
                    min_dist = d
            if min_dist != float('inf'):
                total_cost += min_dist
            else:
                total_cost += 1000

        # Compute cost for vehicle specific goals (if any)
        for veh, goal_loc in self.vehicle_goals.items():
            veh_loc = vehicle_locations.get(veh)
            if veh_loc and veh_loc != goal_loc:
                d = self.dist.get(veh_loc, {}).get(goal_loc, float('inf'))
                if d != float('inf'):
                    total_cost += d
                else:
                    total_cost += 1000

        return total_cost
