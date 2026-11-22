from heuristics.heuristic_base import Heuristic

class blocksworldLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the blocksworld domain.

    # Summary
    This heuristic estimates the minimum number of actions required to reach the goal state from the current state.
    It identifies blocks that are already in their correct final position and those that are not (wrong blocks).
    It then estimates the cost of moving all wrong blocks, including penalties for holding blocks and deadlocks (cycles).

    # Assumptions
    - Each block is either on the table, on another block, or held by the robotic arm.
    - A block is considered "correct" if it and all blocks below it match their goal positions, and they don't violate any other block's goal or clear condition.
    - A block that is not correct must be moved at least once.
    - Moving a block typically costs 2 actions (e.g., unstack + putdown, or pickup + stack), unless it is currently held (costs 1 action to place it).
    - Cycles in dependencies (e.g., block A needs to move to block B, but block B cannot be cleared until A moves) require an extra trip to the table, costing +2 actions.

    # Heuristic Initialization
    - The goal state is parsed to extract the `goal_on` mapping (which block should be on which, or 'table') and the `goal_clear` set.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to extract the `current_on` mapping and identify all blocks.
    2. Iteratively determine the set of `correct_blocks`. A block is correct if:
       - It is not held.
       - Its bottom is 'table' or another `correct_block`.
       - It matches its `goal_on` condition.
       - Its bottom doesn't violate any `goal_clear` condition.
       - No other block wants to be on its bottom.
    3. Identify `wrong_blocks` (all blocks not in `correct_blocks`). If none, the cost is 0 (goal reached).
    4. Calculate the base cost:
       - 2 actions for each unheld wrong block (needs to be picked up and placed).
       - 1 action for a held wrong block (needs to be placed).
       - If a held block's target is not ready (it is a wrong block or not clear), add a penalty of +2 actions, as it must go to the table temporarily.
    5. Build a dependency graph of `wrong_blocks` to detect deadlocks (cycles):
       - Target edge: A block depends on its target being resolved.
       - Cover edge: A block depends on the block currently covering it to move.
    6. Find Strongly Connected Components (SCCs) using Tarjan's algorithm. Each SCC of size > 1 represents a cycle that requires at least one block to go to the table, adding a penalty of +2 actions.
    7. Return the total estimated cost.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.goal_on = {}
        self.goal_clear = set()
        
        for goal in self.goals:
            parts = goal[1:-1].split()
            if parts[0] == 'on':
                self.goal_on[parts[1]] = parts[2]
            elif parts[0] == 'on-table':
                self.goal_on[parts[1]] = 'table'
            elif parts[0] == 'clear':
                self.goal_clear.add(parts[1])

    def __call__(self, node):
        state = node.state
        
        current_on = {}
        all_blocks = set()
        
        # 1. Parse current state
        for fact in state:
            parts = fact[1:-1].split()
            if parts[0] == 'on':
                current_on[parts[1]] = parts[2]
                all_blocks.add(parts[1])
                all_blocks.add(parts[2])
            elif parts[0] == 'on-table':
                current_on[parts[1]] = 'table'
                all_blocks.add(parts[1])
            elif parts[0] == 'holding':
                current_on[parts[1]] = 'held'
                all_blocks.add(parts[1])
                
        # 2. Iteratively find all correctly placed blocks
        correct_blocks = set()
        while True:
            changed = False
            for x in all_blocks:
                if x in correct_blocks:
                    continue
                
                c_on = current_on.get(x)
                if c_on == 'held':
                    continue
                    
                bottom = c_on
                
                # Condition 1: bottom must be correct (or table)
                if bottom != 'table' and bottom not in correct_blocks:
                    continue
                    
                # Condition 2: matches goal
                if x in self.goal_on and self.goal_on[x] != bottom:
                    continue
                    
                # Condition 3: does not violate a clear goal
                if bottom in self.goal_clear:
                    continue
                    
                # Condition 4: does not violate someone else's goal_on
                if bottom != 'table':
                    if any(self.goal_on.get(z) == bottom for z in all_blocks if z != x):
                        continue
                        
                correct_blocks.add(x)
                changed = True
                
            if not changed:
                break
                
        # 3. Identify wrong blocks
        wrong_blocks = all_blocks - correct_blocks
        if not wrong_blocks:
            return 0
            
        # 4 & 5. Calculate base cost and build dependency graph
        cost = 0
        covered_blocks = {current_on[b] for b in all_blocks if current_on.get(b) not in ('table', 'held', None)}
        clear_blocks = all_blocks - covered_blocks
        
        edges = {x: [] for x in wrong_blocks}
        
        for x in wrong_blocks:
            c_on = current_on.get(x)
            
            # Base cost
            if c_on == 'held':
                cost += 1
                target = self.goal_on.get(x)
                # If target is not ready, must go to table temporarily (+2 actions)
                if target and target != 'table':
                    if target in wrong_blocks or target not in clear_blocks:
                        cost += 2
            else:
                cost += 2
                
            # Target edge for dependency graph
            target = self.goal_on.get(x)
            if target in wrong_blocks:
                edges[x].append(target)
                
            # Cover edge for dependency graph (the block 'c_on' depends on 'x' to move)
            if c_on in wrong_blocks:
                edges[c_on].append(x)
                
        # 6. Find SCCs using Tarjan's algorithm
        index = 0
        indices = {}
        lowlink = {}
        on_stack = set()
        stack = []
        scc_count = 0

        def strongconnect(v):
            nonlocal index, scc_count
            indices[v] = index
            lowlink[v] = index
            index += 1
            stack.append(v)
            on_stack.add(v)

            for w in edges.get(v, []):
                if w not in indices:
                    strongconnect(w)
                    lowlink[v] = min(lowlink[v], lowlink[w])
                elif w in on_stack:
                    lowlink[v] = min(lowlink[v], indices[w])

            if lowlink[v] == indices[v]:
                scc_size = 0
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc_size += 1
                    if w == v:
                        break
                # A cycle is found (SCC size > 1), which requires a temporary table drop (+2 actions)
                if scc_size > 1:
                    scc_count += 1

        for v in wrong_blocks:
            if v not in indices:
                strongconnect(v)
                
        # 7. Add penalties for each cycle and return total cost
        cost += 2 * scc_count
        return cost
