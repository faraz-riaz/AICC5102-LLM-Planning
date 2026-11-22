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
    This heuristic estimates the number of actions required to transport all packages to their goal locations. 
    It computes the shortest path distance for each package from its current location (or the location of the vehicle carrying it) 
    to its destination, adding necessary pick-up and drop actions.

    # Assumptions
    - Vehicle capacity constraints and package sizes are relaxed (a vehicle is assumed to be able to carry an arbitrary number of packages).
    - The cost of delivering multiple packages is approximated by summing their independent delivery costs.
    - Each distinct location with at least one package needing pick-up requires a vehicle to travel to it. 
      The distance from the closest vehicle to this location is added to the total cost.

    # Heuristic Initialization
    - Parses static facts (`road`) to construct a road network graph.
    - Computes all-pairs shortest paths between locations using Breadth-First Search (BFS), mapping correctly to the number of `drive` actions.
    - Identifies all vehicles in the domain from the initial state by checking for the `capacity` predicate.
    - Extracts goal locations for all objects (typically packages) from the task's goals. 
      Any non-location goals are also stored to ensure the heuristic strictly returns 0 only in goal states.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find the exact location of all objects (`at` facts) and which packages are currently in vehicles (`in` facts).
    2. Initialize the total estimated cost to 0 and a set of locations needing a vehicle for pick-up.
    3. Loop through every parsed goal condition:
       a. If the goal is an unsupported predicate (e.g., not `at`), check if it's currently satisfied. If not, add a large penalty.
       b. If the goal object is currently in a vehicle:
          - Add the distance from the vehicle's current location to the goal location.
          - Add 1 action for dropping the object at the goal.
       c. If the goal object is at a location and not yet at its goal:
          - If the object is a vehicle (rare but possible), simply add the driving distance to its goal.
          - If the object is a package, add 2 actions (1 for pick-up, 1 for drop) plus the driving distance from its current location to the goal.
          - Mark the package's current location as needing a vehicle for pick-up.
    4. For each distinct location that has packages needing pick-up, find the minimum distance from any current vehicle's location to this location, and add it to the total cost.
    5. Return the accumulated total cost.
    """

    def __init__(self, task):
        self.goals = task.goals
        static_facts = task.static

        # Construct the adjacency list for the road network.
        self.adj = {}
        locations = set()
        
        for fact in static_facts:
            parts = get_parts(fact)
            if parts[0] == "road":
                l1, l2 = parts[1], parts[2]
                if l1 not in self.adj:
                    self.adj[l1] = []
                self.adj[l1].append(l2)
                locations.add(l1)
                locations.add(l2)
                
        # Compute all-pairs shortest paths using BFS (since all edge weights are 1 action).
        self.dist = {}
        for start_node in locations:
            self.dist[start_node] = {start_node: 0}
            queue = [start_node]
            while queue:
                curr = queue.pop(0)
                for neighbor in self.adj.get(curr, []):
                    if neighbor not in self.dist[start_node]:
                        self.dist[start_node][neighbor] = self.dist[start_node][curr] + 1
                        queue.append(neighbor)
                        
        # Identify all vehicles by finding objects that have a defined capacity in the initial state.
        self.vehicles = set()
        for fact in task.initial_state:
            parts = get_parts(fact)
            if parts[0] == "capacity":
                self.vehicles.add(parts[1])
                
        # Parse goals into location-specific goals and other generic goals.
        self.goal_locations = {}
        self.other_goals = set()
        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == "at":
                self.goal_locations[parts[1]] = parts[2]
            else:
                self.other_goals.add(goal)

    def __call__(self, node):
        state = node.state
        
        at_loc = {}
        in_veh = {}
        
        # Parse the current state to track object and vehicle locations.
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "at":
                at_loc[parts[1]] = parts[2]
            elif parts[0] == "in":
                in_veh[parts[1]] = parts[2]
                
        total_cost = 0
        locations_needing_pickup = set()
        
        # Penalize for any unsatisfied non-standard goals to guarantee 0 is only returned for absolute goal states.
        for goal in self.other_goals:
            if goal not in state:
                total_cost += 1000

        # Calculate heuristic costs based on distance to location-specific goals.
        for obj, goal_loc in self.goal_locations.items():
            if obj in in_veh:
                # The object is currently being carried by a vehicle.
                veh = in_veh[obj]
                veh_loc = at_loc.get(veh)
                if veh_loc is not None:
                    # Cost = driving distance to goal + 1 action for dropping.
                    total_cost += self.dist.get(veh_loc, {}).get(goal_loc, 1000) + 1
                else:
                    total_cost += 1000
                    
            elif obj in at_loc:
                # The object is currently resting at some location on the map.
                loc = at_loc[obj]
                if loc != goal_loc:
                    if obj in self.vehicles:
                        # If a vehicle itself has a location goal, just drive it there.
                        total_cost += self.dist.get(loc, {}).get(goal_loc, 1000)
                    else:
                        # For packages: 1 action to pick-up, driving distance to goal, 1 action to drop.
                        total_cost += self.dist.get(loc, {}).get(goal_loc, 1000) + 2
                        locations_needing_pickup.add(loc)
            else:
                # Fallback penalty if an object is entirely missing from the tracked state.
                total_cost += 1000
                
        # Estimate the cost of moving available vehicles to the pick-up locations.
        for loc in locations_needing_pickup:
            # Find the minimum distance from any current vehicle to this pick-up location.
            veh_dists = [self.dist.get(at_loc.get(v), {}).get(loc, 1000) for v in self.vehicles if v in at_loc]
            if veh_dists:
                total_cost += min(veh_dists)
            else:
                total_cost += 1000
                
        return total_cost
