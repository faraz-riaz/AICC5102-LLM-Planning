from heuristics.heuristic_base import Heuristic


def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()


class blocksworldLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the blocksworld domain.

    # Summary
    This heuristic computes an estimate of the number of actions required to reach the goal 
    from the current state. It identifies blocks that are already in their final, correct 
    positions ("done" blocks). For all other blocks, it assigns a base cost of 2 actions 
    (unstack/pickup + stack/putdown), or 1 action if the block is currently held. It also 
    detects deadlocks where a block must be temporarily placed on the table because its 
    target destination is not ready, adding a penalty of 2 actions for each such case.

    # Assumptions
    - The goals specify desired positions such as `(on ?x ?y)`, `(on-table ?x)`, 
      `(clear ?x)`, or `(holding ?x)`.
    - If a block's position is not specified in the goal, it can be anywhere as long as 
      it does not violate other blocks' goals.
    - A block in its correct position will never need to be moved again.
    - A state is considered a goal state when all blocks are in their "done" positions.

    # Heuristic Initialization
    - Parses the goal facts to extract target destinations (`goal_on`, `goal_on_table`, 
      `goal_clear`, `goal_holding`).
    - Builds a reverse mapping (`goal_on_rev`) to quickly find blocks that need to be 
      placed on a given block.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to build mappings of `curr_on`, `curr_on_table`, 
       `curr_clear`, and `curr_holding`.
    2. Determine which blocks are "done" using a bottom-up approach:
       - A block on the table is done if it doesn't need to be on another block or held.
       - A block on another block `y` is done if `y` is done, its goal doesn't conflict 
         with being on `y`, and no other block needs to be on `y`.
       - A held block is done if the goal explicitly requires it to be held.
    3. For every block that is not done:
       - If it is currently held, the base cost is 1. If its target is not ready (not done 
         or not clear), it must be put on the table first, adding 2 to the cost.
       - If it is not held, the base cost is 2. We trace its goal dependency chain. If it 
         is currently stacked above any block that its target depends on, it must be 
         moved to the table to break the deadlock, adding 2 to the cost.
    4. The total heuristic value is the sum of these costs.
    """

    def __init__(self, task):
        """Initialize the heuristic by extracting goal conditions."""
        self.goals = task.goals
        # Static facts are not applicable to the blocksworld domain.

        self.goal_on = {}
        self.goal_on_table = set()
        self.goal_clear = set()
        self.goal_holding = set()

        for goal in self.goals:
            parts = get_parts(goal)
            if parts[0] == "on":
                self.goal_on[parts[1]] = parts[2]
            elif parts[0] == "on-table":
                self.goal_on_table.add(parts[1])
            elif parts[0] == "clear":
                self.goal_clear.add(parts[1])
            elif parts[0] == "holding":
                self.goal_holding.add(parts[1])
        
        # Build reverse mapping for quick lookup: which blocks want to be on 'y'?
        self.goal_on_rev = {}
        for x, y in self.goal_on.items():
            if y not in self.goal_on_rev:
                self.goal_on_rev[y] = set()
            self.goal_on_rev[y].add(x)

    def __call__(self, node):
        """Estimate the minimum cost (number of actions) to solve the task from the current state."""
        state = node.state
        
        curr_on = {}
        curr_on_table = set()
        curr_clear = set()
        curr_holding = None
        
        all_blocks = set()

        # 1. Parse current state
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "on":
                curr_on[parts[1]] = parts[2]
                all_blocks.add(parts[1])
                all_blocks.add(parts[2])
            elif parts[0] == "on-table":
                curr_on_table.add(parts[1])
                all_blocks.add(parts[1])
            elif parts[0] == "clear":
                curr_clear.add(parts[1])
                all_blocks.add(parts[1])
            elif parts[0] == "holding":
                curr_holding = parts[1]
                all_blocks.add(parts[1])
                
        # 2. Determine "done" blocks bottom-up
        done_blocks = set()
        changed = True
        while changed:
            changed = False
            for x in all_blocks:
                if x in done_blocks:
                    continue
                
                is_done = False
                
                if x in curr_on_table:
                    # A block on the table is done if its goal does not require it to be on another block or held
                    if x not in self.goal_on and x not in self.goal_holding:
                        is_done = True
                        
                elif x in curr_on:
                    y = curr_on[x]
                    # A block on `y` is done if:
                    # - `y` is done
                    # - Being on `y` does not violate its own goals
                    # - Being on `y` does not violate `y`'s clear goal
                    # - No other block needs to be placed on `y`
                    if y in done_blocks:
                        if (self.goal_on.get(x, y) == y and
                            x not in self.goal_on_table and
                            x not in self.goal_holding and
                            y not in self.goal_clear):
                            
                            other_wants_y = False
                            for z in self.goal_on_rev.get(y, []):
                                if z != x:
                                    other_wants_y = True
                                    break
                            
                            if not other_wants_y:
                                is_done = True
                                
                elif x == curr_holding:
                    # A held block is only done if the goal explicitly demands holding it
                    if x in self.goal_holding:
                        is_done = True
                
                if is_done:
                    done_blocks.add(x)
                    changed = True

        # 3. Calculate heuristic cost based on misplaced blocks and deadlocks
        cost = 0
        not_done = all_blocks - done_blocks
        
        for x in not_done:
            if x == curr_holding:
                cost += 1
                target = self.goal_on.get(x)
                if target is not None:
                    target_is_done = (target in done_blocks)
                    target_is_clear = (target in curr_clear)
                    # If target is not ready, we must put down the block on the table temporarily
                    if not (target_is_done and target_is_clear):
                        cost += 2
            else:
                cost += 2
                target = self.goal_on.get(x)
                if target is not None:
                    # Resolve goal dependency chain for the target
                    depends = set()
                    curr_dep = target
                    while curr_dep:
                        if curr_dep in depends:  # Safety break for impossible goal cycles
                            break
                        depends.add(curr_dep)
                        curr_dep = self.goal_on.get(curr_dep)
                    
                    # Check for deadlocks: block x is currently stacked above a block its target depends on
                    curr_below = curr_on.get(x)
                    while curr_below:
                        if curr_below in depends:
                            # x must be moved to the table to break the deadlock dependency
                            cost += 2
                            break
                        curr_below = curr_on.get(curr_below)
                
        return cost
