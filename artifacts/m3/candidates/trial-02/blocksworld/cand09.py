from heuristics.heuristic_base import Heuristic

def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()

class blocksworldLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the blocksworld domain.
    
    # Summary
    This heuristic estimates the number of actions required to transform the current state 
    into the goal state. It does this by classifying blocks as "well-placed" (already in 
    their final correct position) or "misplaced". It then estimates the cost to move 
    each misplaced block to its goal position based on its current state and the readiness 
    of its destination.

    # Assumptions
    - The domain follows standard blocksworld rules: one block can be held, blocks can be 
      on the table or on other blocks, and only clear blocks can be moved.
    - A block needs at least 2 actions (pickup/unstack + putdown/stack) to be moved 
      to its final position, unless it is already being held (in which case it needs 1 action).
    - If a block's target position is not ready (e.g., covered by another block, or 
      the target itself is not well-placed), the block might need to be moved to the 
      table temporarily, incurring an additional cost.

    # Heuristic Initialization
    - Parses the goal state to map out the desired configuration: which block should 
      be on which (`goal_on`), which should be on the table (`goal_on_table`), and 
      which must be clear (`goal_clear`).
    - Collects all blocks mentioned in the goals.
    - Extracts static facts (though empty in standard blocksworld, this follows the template).

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to identify the positions of all blocks (on table, on 
       other blocks, holding, and clear). Also discover any additional blocks.
    2. Determine which blocks are "well-placed". A block is well-placed if:
       - It is on the table, and the goal doesn't require it to be on another block.
       - It is on a well-placed block, it is supposed to be there (or has no specific 
         goal but isn't violating any clear goals or blocking other blocks), and it 
         isn't supposed to be on the table.
    3. Iterate through all blocks to calculate the estimated cost:
       - Well-placed blocks contribute 0 to the cost.
       - A held block contributes 1 action if its destination is ready, or 3 actions 
         if it must be placed on the table first.
       - A misplaced block on the table contributes 2 actions (pickup + stack).
       - A misplaced block on another block contributes 2 actions if its destination 
         is ready, or 4 actions if its destination is not ready (unstack, putdown, 
         pickup, stack).
    4. Return the sum of costs for all blocks.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.goal_on = {}
        self.goal_on_table = set()
        self.goal_clear = set()
        self.all_blocks = set()
        
        # Extract goal facts into easily queryable structures
        for goal in self.goals:
            parts = get_parts(goal)
            pred = parts[0]
            if pred == "on":
                self.goal_on[parts[1]] = parts[2]
                self.all_blocks.add(parts[1])
                self.all_blocks.add(parts[2])
            elif pred == "on-table":
                self.goal_on_table.add(parts[1])
                self.all_blocks.add(parts[1])
            elif pred == "clear":
                self.goal_clear.add(parts[1])
                self.all_blocks.add(parts[1])
                
        # Extract static facts (empty in blocksworld, but included for completeness)
        self.static_facts = task.static

    def __call__(self, node):
        state = node.state
        
        all_blocks = set(self.all_blocks)
        state_on = {}
        state_on_table = set()
        state_clear = set()
        state_holding = None
        
        # Parse the current state
        for fact in state:
            parts = get_parts(fact)
            pred = parts[0]
            if pred == "on":
                state_on[parts[1]] = parts[2]
                all_blocks.add(parts[1])
                all_blocks.add(parts[2])
            elif pred == "on-table":
                state_on_table.add(parts[1])
                all_blocks.add(parts[1])
            elif pred == "clear":
                state_clear.add(parts[1])
                all_blocks.add(parts[1])
            elif pred == "holding":
                state_holding = parts[1]
                all_blocks.add(parts[1])
        
        # Determine which blocks are "well-placed" (in their final correct position)
        well_placed = set()
        
        # Base case: blocks on the table
        for b in state_on_table:
            if b not in self.goal_on:
                well_placed.add(b)

        # Recursive case: towers built on well-placed blocks
        changed = True
        while changed:
            changed = False
            for b, under_b in state_on.items():
                if b not in well_placed and under_b in well_placed:
                    if b in self.goal_on_table:
                        continue
                    
                    if b in self.goal_on:
                        if self.goal_on[b] == under_b:
                            well_placed.add(b)
                            changed = True
                    else:
                        # Block has no specific `on` goal.
                        # It can be considered well-placed if the block under it
                        # doesn't need to be clear, and no other block needs to go there.
                        if under_b in self.goal_clear:
                            continue
                        
                        other_has_goal = False
                        for z, targ in self.goal_on.items():
                            if z != b and targ == under_b:
                                other_has_goal = True
                                break
                        
                        if other_has_goal:
                            continue
                        
                        well_placed.add(b)
                        changed = True

        # Calculate heuristic cost based on actions needed for each misplaced block
        total_cost = 0
        for b in all_blocks:
            if b in well_placed:
                continue
            
            target = self.goal_on.get(b)
            
            # Determine if the block's target is "ready" to receive it
            target_ready = False
            if target is None:
                # If a block has no specific target, its target is effectively the table,
                # which is always ready.
                target_ready = True
            else:
                # A target block is ready if it is well-placed and has nothing on top of it.
                if target in well_placed and target in state_clear:
                    target_ready = True

            # Evaluate cost depending on the block's current status
            if b == state_holding:
                if target_ready:
                    total_cost += 1  # 1 action: stack / putdown
                else:
                    total_cost += 3  # 3 actions: putdown, wait, pickup, stack
            elif b in state_on_table:
                total_cost += 2      # 2 actions: pickup, stack
            else:
                # b is on another block
                if target_ready:
                    total_cost += 2  # 2 actions: unstack, stack / putdown
                else:
                    total_cost += 4  # 4 actions: unstack, putdown, wait, pickup, stack
                    
        return total_cost
