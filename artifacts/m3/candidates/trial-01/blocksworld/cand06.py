from heuristics.heuristic_base import Heuristic

class blocksworldLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the blocksworld domain.

    # Summary
    This heuristic estimates the number of actions needed to reach the goal state from the current state.
    It identifies which blocks are already in their correct final position ("well-placed") and calculates the cost
    for moving the misplaced blocks. It distinguishes between blocks that can be directly moved to their 
    target and those that must be temporarily placed on the table to avoid deadlocks.

    # Assumptions
    - Blocks can be picked up from the table or unstacked from other blocks.
    - Blocks can be put down on the table or stacked on other blocks.
    - Every movement action (pickup, putdown, stack, unstack) costs 1 action.
    - A block is considered well-placed if it is in its goal position, all blocks below it are well-placed,
      and it doesn't need to be moved to clear another block or satisfy other goals.
    - If a state fully satisfies the goal conditions, the cost is 0.

    # Heuristic Initialization
    - Parses the goals to determine the target position for each block (`goal_on`, `goal_holding`, etc.).
    - Extracts all block objects present in the task's initial state to iterate over them efficiently.
    - Precomputes inverse mappings (e.g., `goal_has_on`) for fast lookup of dependencies (what block must be on another).
    - Extracts static facts from the task, even though the blocksworld domain does not rely on static facts.

    # Step-By-Step Thinking for Computing Heuristic
    1. Check if the current state satisfies all goal conditions. If so, return 0.
    2. Parse the current state to find all blocks on the table, the currently held block, and block-on-block relationships.
    3. Determine the set of `well_placed` blocks by tracing upwards from the table. A block is well-placed if:
       - It is on a well-placed block (or the table).
       - It matches its explicit goal position (if it has one).
       - It does not violate any `clear` goal for the block underneath it.
       - No other block has an explicit goal to be placed on the block underneath it.
    4. For each block that is not well-placed, estimate the required number of actions:
       - If the block is currently held:
         - Costs 1 action if it can be directly placed on its target or on the table.
         - Costs 3 actions if its target is another block that is not yet well-placed (must be put on the table first).
       - If the block is not held:
         - Costs 2 actions (e.g., unstack + putdown, or pickup + stack) if its target is the table or is already well-placed.
         - Costs 2 actions if it can safely wait on its current support until its target becomes well-placed.
         - Costs 4 actions (unstack, putdown, pickup, stack) if it cannot wait on its current support and its target is not yet well-placed.
    5. Sum up the estimated action costs for all misplaced blocks to obtain the final heuristic value.
    """
    
    def __init__(self, task):
        self.goals = task.goals
        static_facts = task.static  # Extracted for consistency with the checklist, though unused in blocksworld
        
        self.goal_on = {}
        self.goal_clear = set()
        self.goal_holding = None
        self.goal_has_on = {}
        
        # Extract goals into easily accessible dictionaries and sets
        for goal in self.goals:
            parts = goal[1:-1].split()
            if parts[0] == "on":
                self.goal_on[parts[1]] = parts[2]
                self.goal_has_on[parts[2]] = parts[1]
            elif parts[0] == "on-table":
                self.goal_on[parts[1]] = "table"
            elif parts[0] == "clear":
                self.goal_clear.add(parts[1])
            elif parts[0] == "holding":
                self.goal_holding = parts[1]
                
        # Discover all blocks present in the problem
        self.all_blocks = set()
        for fact in task.initial_state:
            parts = fact[1:-1].split()
            if len(parts) > 1:
                self.all_blocks.add(parts[1])
            if len(parts) > 2:
                self.all_blocks.add(parts[2])

    def __call__(self, node):
        # Quick check for goal states
        if self.goals <= node.state:
            return 0
            
        state = node.state
        
        on_table_blocks = []
        on_block = {}
        current_holding = None
        
        # Parse current state facts
        for fact in state:
            parts = fact[1:-1].split()
            if parts[0] == "on-table":
                on_table_blocks.append(parts[1])
            elif parts[0] == "on":
                on_block[parts[1]] = parts[2]  # parts[1] is on top of parts[2]
            elif parts[0] == "holding":
                current_holding = parts[1]
                
        # Mapping from bottom block to top block to easily trace stacks upwards
        under_block = {bottom: top for top, bottom in on_block.items()}
        
        # Find all correctly positioned (well-placed) blocks
        well_placed = set(["table"])
        
        for start_b in on_table_blocks:
            current = start_b
            under = "table"
            
            while current is not None:
                wp = False
                if under in well_placed:
                    # Condition 3: matches explicit goal position or has no goal positional constraints
                    if current == self.goal_holding:
                        cond3 = False
                    else:
                        cond3 = (current not in self.goal_on) or (self.goal_on[current] == under)
                    
                    # Condition 4: check that the current block doesn't hinder goals of the block underneath it
                    cond4 = True
                    if under != "table":
                        if under in self.goal_clear:
                            cond4 = False
                        elif under in self.goal_has_on and self.goal_has_on[under] != current:
                            cond4 = False
                            
                    if cond3 and cond4:
                        wp = True
                
                if wp:
                    well_placed.add(current)
                    under = current
                    current = under_block.get(current)
                else:
                    # If this block isn't well-placed, none of the blocks on top of it are well-placed either
                    break
                    
        total_cost = 0
        
        # Estimate the cost of placing the remaining misplaced blocks
        for x in self.all_blocks:
            if x in well_placed:
                continue
            
            if x == current_holding:
                if x == self.goal_holding:
                    # If there are other blocks that must be moved, we have to put down the currently held block.
                    if len(self.all_blocks) > (len(well_placed) - 1) + 1:
                        total_cost += 2
                else:
                    y = self.goal_on.get(x, "table")
                    # It's currently held; if its destination is ready, just place it (1 action)
                    if y == "table" or y in well_placed:
                        total_cost += 1
                    else:
                        # Destination not ready. Must drop on table and wait (1 putdown + 1 pickup + 1 stack)
                        total_cost += 3
            else:
                if x == self.goal_holding:
                    # Only needs to be picked up eventually
                    total_cost += 1
                else:
                    y = self.goal_on.get(x, "table")
                    # If its target is ready or it just needs to be placed on the table
                    if y == "table" or y in well_placed:
                        total_cost += 2
                    else:
                        z = on_block.get(x, "table")
                        if z == "table":
                            # Currently on the table, can safely wait for target to be ready
                            total_cost += 2
                        else:
                            # It is on another block `z`. Check if it can wait on `z`.
                            if (z in well_placed and 
                                z not in self.goal_clear and 
                                z not in self.goal_has_on):
                                # It can safely wait for target to be ready
                                total_cost += 2
                            else:
                                # Target not ready, and it must move to free `z`.
                                # Requires 4 actions (unstack, putdown on table, pickup, stack on target)
                                total_cost += 4
                                
        return total_cost
