import collections
from heuristics.heuristic_base import Heuristic

def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()

class transportLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the transport domain.

    # Summary
    This heuristic estimates the minimum number of actions required to transport all goal-directed 
    packages to their respective destinations. It provides a heavily guided, monotonically decreasing 
    cost estimate for Greedy Best-First Search by properly weighting the different stages of delivery 
    (picking up, transporting, and dropping).

    # Assumptions
    - Packages that need to be delivered are specified in the goal conditions.
    - Vehicles can carry one or more packages, as determined by their capacity.
    - The road network allows calculating shortest path distances between locations.
    - All movements (driving) cost 1 action per road segment. 
    - Picking up and dropping off packages each cost 1 action.

    # Heuristic Initialization
    - The goal locations for each package are parsed and stored.
    - The entire road network is extracted from the static facts and the initial state.
    - An All-Pairs Shortest Path (APSP) algorithm computes the optimal driving distance between all locations.
    - A set of all available vehicles is gathered by identifying objects with a `capacity` predicate in the initial state.

    # Step-By-Step Thinking for Computing Heuristic
    1. Check the current state of each package that has a goal location.
    2. If the package is already at its goal, it requires 0 additional actions.
    3. If the package is currently in a vehicle:
       - It must eventually be dropped off (cost of 1).
       - The vehicle must drive from its current location to the package's goal.
       - To strongly encourage the search to move loaded vehicles towards goals, the distance is multiplied by a weight of 3.
    4. If the package is at a location other than its goal:
       - It must be picked up (cost of 1), dropped off (cost of 1), and an additional penalty is added to encourage picking it up (total base cost 3).
       - The distance from its current location to the goal is also added, multiplied by a weight of 3.
       - The location is marked as an 'unmet location' because a vehicle needs to visit it.
    5. For each unmet location with waiting packages:
       - Find the minimum distance from any available vehicle to this location.
       - Add this distance multiplied by 2 to the heuristic. This properly penalizes states where vehicles are driving away from waiting packages, but since the vehicle moving distance is weighted by 3, making progress with a loaded vehicle always yields a net decrease in the heuristic.
    """

    def __init__(self, task):
        self.goals = task.goals
        
        # Store goal locations for packages
        self.goal_locations = {}
        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == 'at':
                self.goal_locations[parts[1]] = parts[2]
                
        # Parse the road network
        self.adj = collections.defaultdict(list)
        for fact in task.static | task.initial_state:
            parts = get_parts(fact)
            if parts[0] == 'road':
                self.adj[parts[1]].append(parts[2])
                
        # Identify all unique locations to compute shortest paths
        nodes = list(self.adj.keys())
        for fact in task.initial_state | task.goals:
            parts = get_parts(fact)
            if parts[0] in ['at', 'road']:
                if len(parts) > 2:
                    nodes.append(parts[2])
                if parts[0] == 'road':
                    nodes.append(parts[1])
        nodes = list(set(nodes))
        
        # Compute All-Pairs Shortest Path (APSP) using BFS (all edges have weight 1)
        self.dist = {}
        for node in nodes:
            self.dist[node] = {node: 0}
            queue = collections.deque([node])
            while queue:
                curr = queue.popleft()
                d = self.dist[node][curr]
                for nxt in self.adj[curr]:
                    if nxt not in self.dist[node]:
                        self.dist[node][nxt] = d + 1
                        queue.append(nxt)
                        
        # Identify all vehicles
        self.vehicles = set()
        for fact in task.initial_state | task.static:
            parts = get_parts(fact)
            if parts[0] == 'capacity':
                self.vehicles.add(parts[1])

    def __call__(self, node):
        state = node.state
        
        # Current locations of locatables (packages or vehicles)
        at_loc = {}
        # Tracks which package is in which vehicle
        in_veh = {}
        # Keep track of active vehicles (redundant safety check)
        vehicles = set(self.vehicles)
        
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == 'at':
                at_loc[parts[1]] = parts[2]
            elif parts[0] == 'in':
                in_veh[parts[1]] = parts[2]
                vehicles.add(parts[2])
                
        total_cost = 0
        unmet_locations = set()
        
        for pkg, goal_loc in self.goal_locations.items():
            if pkg in at_loc:
                curr_loc = at_loc[pkg]
                if curr_loc == goal_loc:
                    continue  # Package is successfully delivered
                else:
                    dist = self.dist.get(curr_loc, {}).get(goal_loc, 10000)
                    total_cost += 3 + 3 * dist
                    unmet_locations.add(curr_loc)
            elif pkg in in_veh:
                veh = in_veh[pkg]
                veh_loc = at_loc.get(veh)
                if veh_loc:
                    dist = self.dist.get(veh_loc, {}).get(goal_loc, 10000)
                    total_cost += 1 + 3 * dist
                else:
                    total_cost += 10000  # Failsafe if vehicle location is lost
            else:
                # Failsafe if a package simply vanished
                total_cost += 10000
                
        # Consider the movement required by vehicles to pick up unmet packages
        for loc in unmet_locations:
            min_dist = 10000
            for v in vehicles:
                v_loc = at_loc.get(v)
                if v_loc:
                    d = self.dist.get(v_loc, {}).get(loc, 10000)
                    if d < min_dist:
                        min_dist = d
            total_cost += 2 * min_dist
            
        return total_cost
