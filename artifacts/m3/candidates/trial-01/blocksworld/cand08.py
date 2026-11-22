from fnmatch import fnmatch
from heuristics.heuristic_base import Heuristic

class blocksworldLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Blocksworld domain.

    # Summary
    This heuristic estimates the minimum number of actions required to reach 
    a goal state from the current state. It counts the number of misplaced 
    blocks and adds penalties for holding a block or for blocks involved in 
    cyclic dependencies (deadlocks).

    # Assumptions
    - Blocks can be on the table, on other blocks, or held by the robotic arm.
    - An action consists of unstacking/picking up a block and stacking/putting it down.
    - Goal states specify target positions for blocks (on another block or on the table), 
      or require blocks to be clear.

    # Heuristic Initialization
    - Parses the goal conditions to extract `goal_on`, `goal_on_table`, and `goal_clear`.
    - Computes `goal_under` to track which block is required to be on top of another.

    # Step-By-Step Thinking for Computing Heuristic
    1. Check if the current state satisfies all goals. If so, return 0.
    2. Parse the current state to identify the positions of all blocks (on, on-table, holding, clear).
    3. Identify `well_placed` blocks. A block is well-placed if it is in its final goal position 
       and all blocks below it are also well-placed. Blocks with no specific goals are well-placed 
       if they rest on well-placed blocks and do not violate any `clear` or `goal_under` conditions.
    4. Blocks not well-placed are considered `misplaced`.
    5. Compute a base action cost:
       - If a block is held, it requires at least 1 action (to place it). If its target is not ready, 
         it requires 3 actions (put down, pick up later, stack).
       - Other misplaced blocks require at least 2 actions (pick up/unstack + put down/stack).
    6. Construct a dependency graph for the misplaced blocks to detect deadlocks:
       - Rule 1: Target dependency. If block X must go on block Y, Y must be in place before X.
       - Rule 2: Clear target dependency. If X must go on Y, and Z is currently on Y, Z must be moved before X.
       - Rule 3: Above dependency. If X is on Z, X must be moved before Z can be moved.
    7. Find Strongly Connected Components (SCCs) using Tarjan's algorithm. Each SCC with more than 
       1 block represents a cyclic dependency (deadlock) that requires temporarily placing at least 
       one block on the table. Add 2 actions for each such cycle.
    8. Return the total computed cost.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.goal_on = {}
        self.goal_on_table = set()
        self.goal_clear = set()
        self.goal_under = {}
        
        for goal in self.goals:
            parts = goal[1:-1].split()
            if parts[0] == "on":
                self.goal_on[parts[1]] = parts[2]
                self.goal_under[parts[2]] = parts[1]
            elif parts[0] == "on-table":
                self.goal_on_table.add(parts[1])
            elif parts[0] == "clear":
                self.goal_clear.add(parts[1])

    def __call__(self, node):
        state = node.state
        
        # 1. Goal state check
        if self.goals.issubset(state):
            return 0
        
        # 2. Parse current state
        on = {}
        on_table = set()
        clear = set()
        holding = None
        all_blocks = set()
        
        for fact in state:
            parts = fact[1:-1].split()
            if parts[0] == "on":
                on[parts[1]] = parts[2]
                all_blocks.add(parts[1])
                all_blocks.add(parts[2])
            elif parts[0] == "on-table":
                on_table.add(parts[1])
                all_blocks.add(parts[1])
            elif parts[0] == "clear":
                clear.add(parts[1])
                all_blocks.add(parts[1])
            elif parts[0] == "holding":
                holding = parts[1]
                all_blocks.add(parts[1])
                
        # 3. Identify well-placed blocks
        well_placed = set()
        for x in on_table:
            if x not in self.goal_on:
                well_placed.add(x)
                
        changed = True
        while changed:
            changed = False
            for x, y in on.items():
                if x not in well_placed and y in well_placed:
                    if x in self.goal_on:
                        if self.goal_on[x] == y:
                            well_placed.add(x)
                            changed = True
                    elif x in self.goal_on_table:
                        continue
                    else:
                        if y in self.goal_clear:
                            continue
                        if y in self.goal_under and self.goal_under[y] != x:
                            continue
                        well_placed.add(x)
                        changed = True
                        
        # 4 & 5. Compute base action cost for misplaced blocks
        cost = 0
        misplaced = set()
        
        if holding:
            misplaced.add(holding)
            can_place = True
            if holding in self.goal_on:
                target = self.goal_on[holding]
                if target not in well_placed or target in on.values():
                    can_place = False
            if can_place:
                cost += 1
            else:
                cost += 3
                
        for x in all_blocks:
            if x not in well_placed and x != holding:
                misplaced.add(x)
                cost += 2
                
        # 6. Construct dependency graph for deadlocks
        adj = {m: [] for m in misplaced}
        for x in misplaced:
            if x == holding:
                continue
            
            # Rule 1: Target dependency (Y must be well-placed before X)
            if x in self.goal_on:
                y = self.goal_on[x]
                if y in misplaced and y != holding:
                    adj[y].append(x)
                    
            # Rule 2: Clear target dependency (U must move before X can go on W)
            if x in self.goal_on:
                w = self.goal_on[x]
                if w in well_placed:
                    for u, w_curr in on.items():
                        if w_curr == w and u in misplaced and u != holding:
                            adj[u].append(x)
                            
            # Rule 3: Above dependency (X must move before V can move)
            if x in on:
                v = on[x]
                if v in misplaced and v != holding:
                    adj[x].append(v)
                    
        # 7. Find Strongly Connected Components (SCCs) to penalize cycles
        index_counter = [0]
        index = {}
        lowlink = {}
        stack = []
        on_stack = set()
        sccs = []
        
        def strongconnect(node):
            index[node] = index_counter[0]
            lowlink[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack.add(node)
            
            for w in adj.get(node, []):
                if w not in index:
                    strongconnect(w)
                    lowlink[node] = min(lowlink[node], lowlink[w])
                elif w in on_stack:
                    lowlink[node] = min(lowlink[node], index[w])
                    
            if lowlink[node] == index[node]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc.append(w)
                    if w == node:
                        break
                sccs.append(scc)
                
        for node in adj:
            if node not in index:
                strongconnect(node)
                
        # Each cycle forces at least one block to be placed on the table temporarily (2 extra actions)
        for scc in sccs:
            if len(scc) > 1:
                cost += 2
                
        # 8. Return final estimate
        return cost
