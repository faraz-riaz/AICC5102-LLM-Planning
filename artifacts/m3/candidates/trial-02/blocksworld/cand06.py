from heuristics.heuristic_base import Heuristic

class blocksworldLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the blocksworld domain.

    # Summary
    This heuristic estimates the minimum number of actions required to reach a goal state 
    by determining which blocks are currently "well-placed" and which are "misplaced".
    It assigns base action costs to misplaced blocks and adds exact penalties for deadlocks 
    (cyclic dependencies) and for holding blocks that cannot be immediately placed on their targets.

    # Assumptions
    - A block is well-placed if it is in its goal position (on the table or on another 
      well-placed block) and does not need to be moved to clear another block.
    - Blocks with no specified goal are well-placed as long as they rest on a well-placed block 
      or the table, provided they are not usurping a position targeted by another block.
    - Misplaced blocks generally require 2 actions to reach their goal (unstack/pickup + 
      putdown/stack).
    - A block currently held by the robotic arm requires 1 action (putdown or stack) if its 
      target is ready, or 3 actions if its target is unready (put on table, wait, then pick up and stack).
    - If a cyclic dependency exists between blocks (e.g., block A needs to go on B, but B is under A), 
      at least one block in the cycle must be temporarily placed on the table, requiring 2 extra actions.

    # Heuristic Initialization
    - Extract the goal positions for each block (`goal_on`).
    - Extract blocks that must be clear in the goal (`goal_clear`).
    - Build a mapping of which block is targeted by which block (`targeted_by`) to prevent 
      un-targeted blocks from incorrectly squatting on required spots.
    - Save static facts (even though blocksworld doesn't typically utilize static facts).

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find `current_on`, `current_held`, and collect all `blocks`.
    2. Iteratively determine the set of `well_placed` blocks from the bottom up.
       A block is well-placed if its current position matches its goal position (or it has no goal), 
       the entity it is on is also well-placed, and it is not blocking a goal requirement.
    3. Identify `misplaced` blocks (any block not in `well_placed`). If there are none, return 0.
    4. Calculate a base cost:
       - 1 for a held block if its target is ready, 3 if not ready.
       - 2 for all other misplaced blocks.
    5. Construct a dependency graph among the misplaced, unheld blocks:
       - Edge `u -> v`: block `u` must be moved before `v` can be placed.
       - Rule 1: If `u` is currently on `v`, `u` must move before `v`.
       - Rule 2: If `v` wants to be on `z` (and `z` is a block):
         - If `z` is misplaced, `z` must move before `v`.
         - If any block `w` is currently on `z`, `w` must move before `v`.
    6. Find Strongly Connected Components (SCCs) in the dependency graph using Tarjan's Algorithm. 
       Each SCC with size > 1 represents a deadlock cycle, costing an additional 2 actions to resolve.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.static_facts = task.static

        self.goal_on = {}
        self.goal_clear = set()
        self.targeted_by = {}

        for goal in self.goals:
            parts = goal[1:-1].split()
            if parts[0] == "on":
                self.goal_on[parts[1]] = parts[2]
                self.targeted_by[parts[2]] = parts[1]
            elif parts[0] == "on-table":
                self.goal_on[parts[1]] = "table"
            elif parts[0] == "clear":
                self.goal_clear.add(parts[1])

    def __call__(self, node):
        state = node.state

        current_on = {}
        current_held = None
        blocks = set()

        # Step 1: Parse the current state
        for fact in state:
            parts = fact[1:-1].split()
            if parts[0] == "on":
                current_on[parts[1]] = parts[2]
                blocks.add(parts[1])
                blocks.add(parts[2])
            elif parts[0] == "on-table":
                current_on[parts[1]] = "table"
                blocks.add(parts[1])
            elif parts[0] == "holding":
                current_held = parts[1]
                blocks.add(parts[1])
            elif parts[0] == "clear":
                blocks.add(parts[1])

        # Step 2: Determine well-placed blocks iteratively
        well_placed = set()
        changed = True
        while changed:
            changed = False
            for b in blocks:
                if b in well_placed or b == current_held:
                    continue
                
                on_entity = current_on.get(b)
                is_wp = False
                
                if on_entity == "table":
                    if self.goal_on.get(b, "table") == "table":
                        is_wp = True
                elif on_entity in well_placed:
                    if self.goal_on.get(b, on_entity) == on_entity:
                        if on_entity not in self.goal_clear:
                            if on_entity in self.targeted_by:
                                if self.targeted_by[on_entity] == b:
                                    is_wp = True
                            else:
                                is_wp = True
                            
                if is_wp:
                    well_placed.add(b)
                    changed = True

        misplaced = blocks - well_placed
        if not misplaced:
            return 0  # Goal state reached (or at least no blocks are misplaced)

        cost = 0
        misplaced_not_held = set()

        # Step 3 & 4: Calculate base cost
        for b in misplaced:
            if b == current_held:
                z = self.goal_on.get(b, "table")
                if z == "table":
                    cost += 1
                else:
                    if z in well_placed:
                        z_has_blocks = any(current_on.get(x) == z for x in blocks)
                        if not z_has_blocks:
                            cost += 1
                        else:
                            cost += 3
                    else:
                        cost += 3
            else:
                cost += 2
                misplaced_not_held.add(b)

        # Step 5: Build dependency graph for unheld misplaced blocks
        adj = {b: [] for b in misplaced_not_held}
        for v in misplaced_not_held:
            # Rule 1: block u currently on v -> u must move before v
            for u in misplaced_not_held:
                if current_on.get(u) == v:
                    adj[u].append(v)
            
            # Rule 2: target z of v
            z = self.goal_on.get(v)
            if z in blocks:
                if z in misplaced_not_held:
                    adj[z].append(v)
                for w in misplaced_not_held:
                    if current_on.get(w) == z:
                        adj[w].append(v)

        # Step 6: Find SCCs using Tarjan's algorithm to penalize cycles (deadlocks)
        index_counter = 0
        index = {}
        lowlink = {}
        stack = []
        on_stack = set()
        sccs = []

        def strongconnect(v):
            nonlocal index_counter
            index[v] = index_counter
            lowlink[v] = index_counter
            index_counter += 1
            stack.append(v)
            on_stack.add(v)
            
            for w in adj[v]:
                if w not in index:
                    strongconnect(w)
                    lowlink[v] = min(lowlink[v], lowlink[w])
                elif w in on_stack:
                    lowlink[v] = min(lowlink[v], index[w])
                    
            if lowlink[v] == index[v]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc.append(w)
                    if w == v:
                        break
                sccs.append(scc)

        for v in misplaced_not_held:
            if v not in index:
                strongconnect(v)

        # Each cyclic deadlock requires at least one block to be placed on the table temporarily
        for scc in sccs:
            if len(scc) > 1:
                cost += 2

        return cost
