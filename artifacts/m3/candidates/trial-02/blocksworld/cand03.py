from heuristics.heuristic_base import Heuristic


class blocksworldLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Blocksworld domain.

    # Summary
    The heuristic estimates the number of actions required to reach the goal state
    by identifying "solid" blocks (blocks that are already in their correct, final 
    positions) and calculating the necessary actions to move the remaining blocks 
    into their target positions.

    # Assumptions
    - The table is infinitely large, allowing any number of blocks to be placed on it.
    - A block is considered "solid" if it is in a valid final position and all blocks 
      beneath it are also solid and correct according to the goals.
    - Any block that is not solid must be moved at least once.

    # Heuristic Initialization
    - Parses the goal conditions to extract specific target positions for each block 
      (`on`, `on-table`), required clear blocks, and any block that must be held.
    - Creates mappings for inverse target positions to quickly check if a block 
      is expected to support another specific block.

    # Step-By-Step Thinking for Computing Heuristic
    1. Check if the current state satisfies all goals. If so, return 0.
    2. Extract the current state into structured mappings (`cur_on`, `on_top`, `cur_holding`).
    3. Iteratively determine the set of "solid" blocks. A block is solid if it is 
       on the table or on another solid block, and its placement does not violate any goals.
    4. Identify the set `M` of all blocks that are not solid.
    5. Calculate base costs for moving blocks in `M`:
       - If a block is currently held, check if its target position is ready 
         (solid and clear). If ready, it costs 1 action (stack/putdown). If not, 
         it costs 3 actions (putdown, pickup, stack).
       - For all other non-solid blocks, they require at least 2 actions (pickup/unstack 
         and putdown/stack).
    6. Build a dependency graph among the blocks in `M` to identify cycles of dependencies 
       (e.g., block A needs to go where block B is, and block B needs to go where block A is).
       An edge from block `b` to block `x` is added if `x` must be moved before `b` can be 
       placed in its final target position.
    7. Use Tarjan's algorithm to find Strongly Connected Components (SCCs) in the dependency graph. 
       Each SCC of size > 1 represents a cycle that requires at least one block to be 
       temporarily placed on the table, adding 2 extra actions per cycle.
    8. Return the total computed cost.
    """

    def __init__(self, task):
        self.goals = task.goals
        
        self.goal_on = {}
        self.goal_on_inverse = {}
        self.goal_on_table = set()
        self.goal_clear = set()
        self.goal_holding = set()
        
        for goal in self.goals:
            parts = goal[1:-1].split()
            predicate = parts[0]
            if predicate == 'on':
                self.goal_on[parts[1]] = parts[2]
                self.goal_on_inverse[parts[2]] = parts[1]
            elif predicate == 'on-table':
                self.goal_on_table.add(parts[1])
            elif predicate == 'clear':
                self.goal_clear.add(parts[1])
            elif predicate == 'holding':
                self.goal_holding.add(parts[1])

    def __call__(self, node):
        state = node.state
        
        # The heuristic must be 0 for goal states.
        if self.goals <= state:
            return 0
            
        cur_on = {}
        on_top = {}
        cur_holding = None
        blocks = set()
        
        # Extract the current state into easily accessible mappings
        for fact in state:
            parts = fact[1:-1].split()
            predicate = parts[0]
            if predicate == 'on':
                b, c = parts[1], parts[2]
                cur_on[b] = c
                on_top[c] = b
                blocks.add(b)
                blocks.add(c)
            elif predicate == 'on-table':
                b = parts[1]
                cur_on[b] = 'table'
                blocks.add(b)
            elif predicate == 'clear':
                blocks.add(parts[1])
            elif predicate == 'holding':
                b = parts[1]
                cur_holding = b
                blocks.add(b)

        # Iteratively determine which blocks are "solid" (in their final correct position)
        solid = {}
        changed = True
        while changed:
            changed = False
            for b in blocks:
                if b in solid or b == cur_holding:
                    continue
                
                if cur_on.get(b) == 'table':
                    if b in self.goal_on or b in self.goal_holding:
                        continue
                    solid[b] = True
                    changed = True
                elif cur_on.get(b) in blocks:
                    c = cur_on[b]
                    if c in solid:
                        if b in self.goal_on_table or b in self.goal_holding:
                            continue
                        if b in self.goal_on and self.goal_on[b] != c:
                            continue
                        if b not in self.goal_on:
                            # Verify if c is reserved for another block or must be clear
                            if c in self.goal_on_inverse:
                                continue
                            if c in self.goal_clear:
                                continue
                        solid[b] = True
                        changed = True

        # `M` defines the set of blocks that are not solid (and must be moved at least once)
        M = {b for b in blocks if b not in solid}
        total_cost = 0
        G = {b: [] for b in M}

        for b in M:
            target = self.goal_on.get(b) if b in self.goal_on else ('table' if b in self.goal_on_table else 'any')
            
            # Base action costs calculation
            if b == cur_holding:
                target_ready = False
                if target in ('table', 'any'):
                    target_ready = True
                else:
                    c = target
                    c_clear = c not in on_top
                    if c not in M and c_clear:
                        target_ready = True
                
                if target_ready:
                    total_cost += 1
                else:
                    total_cost += 3
            else:
                total_cost += 2
                
            # Build dependency graph
            x = on_top.get(b)
            if x in M:
                G[b].append(x)
                
            if target not in ('table', 'any'):
                c = target
                if c in M:
                    G[b].append(c)
                else:
                    x = on_top.get(c)
                    if x in M:
                        G[b].append(x)

        # Detect cyclic dependencies using Tarjan's SCC algorithm
        index = 0
        indices = {}
        lowlink = {}
        stack = []
        on_stack = set()
        sccs = []

        def strongconnect(v):
            nonlocal index
            indices[v] = index
            lowlink[v] = index
            index += 1
            stack.append(v)
            on_stack.add(v)
            
            for w in G.get(v, []):
                if w not in indices:
                    strongconnect(w)
                    lowlink[v] = min(lowlink[v], lowlink[w])
                elif w in on_stack:
                    lowlink[v] = min(lowlink[v], indices[w])
                    
            if lowlink[v] == indices[v]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc.append(w)
                    if w == v:
                        break
                sccs.append(scc)

        for v in M:
            if v not in indices:
                strongconnect(v)

        # Each cyclic dependency block requires temporarily putting at least one block on the table (+2 actions)
        num_cycles = sum(1 for scc in sccs if len(scc) > 1)
        total_cost += 2 * num_cycles

        return total_cost
