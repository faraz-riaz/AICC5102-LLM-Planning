from heuristics.heuristic_base import Heuristic

class blocksworldLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the Blocksworld domain.

    # Summary
    This heuristic estimates the number of required actions to reach the goal state. 
    It classifies blocks as either "well-placed" (already in their final correct position 
    and not blocking any other goals) or "misplaced". Misplaced blocks are assigned 
    a cost based on their current position (in hand, on table, or on another block) 
    and whether their target support is ready to receive them. 

    # Assumptions
    - Blocks that are not well-placed must be moved at least once.
    - An optimal plan generally moves blocks directly to their final positions when possible, 
      or temporarily to the table if their target support is not yet ready.
    - The table has infinite capacity.

    # Heuristic Initialization
    - Extract goal relations: which block must be on which (`goal_on`), 
      which must be on the table (`goal_on_table`), and which must be clear (`goal_clear`).
    - Build a reverse mapping (`goal_has_on`) to easily check if a block needs another block on top.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find the position of all blocks (on the table, on another block, or held).
    2. Iteratively determine the set of `well_placed` blocks from the bottom up:
       - A block on the table is well-placed if it doesn't have a goal to be on another block.
       - A block `x` on `y` is well-placed if `y` is well-placed, AND either `x` is required to be on `y`, 
         or `x` is a "don't care" block that isn't violating any clear goals or space required by another block.
    3. For every block that is NOT well-placed, assign an action cost:
       - If the block is held and its target goal support is ready (well-placed and currently clear), cost = 1.
       - If the block is held but its target goal support is NOT ready, cost = 3.
       - If the block is on the table, it must be picked up and stacked later, cost = 2.
       - If the block is on another block, it must be unstacked first, cost = 4.
    4. The total heuristic value is the sum of these costs. This elegantly guides the greedy search 
       to prioritize unstacking blocks, moving them to the table if necessary, and immediately placing 
       them on their final goal supports when ready.
    """
    
    def __init__(self, task):
        self.goals = task.goals
        self.goal_on = {}
        self.goal_on_table = set()
        self.goal_clear = set()
        
        # Extract individual goals
        for goal in self.goals:
            parts = goal[1:-1].split()
            if parts[0] == "on":
                self.goal_on[parts[1]] = parts[2]
            elif parts[0] == "on-table":
                self.goal_on_table.add(parts[1])
            elif parts[0] == "clear":
                self.goal_clear.add(parts[1])
                
        # Reverse mapping to know what block is supposed to be on top of 'y'
        self.goal_has_on = {y: x for x, y in self.goal_on.items()}

    def __call__(self, node):
        state = node.state
        
        current_on = {}
        current_on_table = set()
        current_clear = set()
        holding = None
        all_blocks = set()

        # 1. Parse the current state properties
        for fact in state:
            parts = fact[1:-1].split()
            predicate = parts[0]
            if predicate == "on":
                current_on[parts[1]] = parts[2]
                all_blocks.add(parts[1])
                all_blocks.add(parts[2])
            elif predicate == "on-table":
                current_on_table.add(parts[1])
                all_blocks.add(parts[1])
            elif predicate == "clear":
                current_clear.add(parts[1])
                all_blocks.add(parts[1])
            elif predicate == "holding":
                holding = parts[1]
                all_blocks.add(parts[1])

        # 2. Iteratively discover which blocks are well-placed
        well_placed = set()
        
        # Base case: well-placed on the table
        for x in current_on_table:
            if x not in self.goal_on:
                well_placed.add(x)

        # Inductive step: propagate well-placed upwards
        changed = True
        while changed:
            changed = False
            for x, y in current_on.items():
                if x not in well_placed and y in well_placed:
                    if self.goal_on.get(x) == y:
                        # Required to be on 'y' by the goal
                        well_placed.add(x)
                        changed = True
                    elif x not in self.goal_on and x not in self.goal_on_table:
                        # Not explicitly required, but acts as a "don't care" block safely resting on 'y'
                        y_needs_clear = (y in self.goal_clear)
                        y_needs_other_child = (y in self.goal_has_on and self.goal_has_on[y] != x)
                        if not y_needs_clear and not y_needs_other_child:
                            well_placed.add(x)
                            changed = True

        # 3. Compute heuristic costs based on placements and goal readiness
        total_cost = 0
        for b in all_blocks:
            # If well-placed, the block costs 0 to reach the goal layout
            if b in well_placed:
                continue
            
            # If the block is misplaced, penalize it gracefully
            if b == holding:
                # Decide if the block can go directly to its final support in the next action
                if b in self.goal_on:
                    c = self.goal_on[b]
                    goal_ready = (c in well_placed) and (c in current_clear)
                else:
                    # If goal is table or don't care, it's always ready
                    goal_ready = True
                
                # Being held while goal is ready encourages direct stacking (1 action)
                if goal_ready:
                    total_cost += 1
                else:
                    # Otherwise, it must be put down (1), then picked up later (2), costing 3 actions
                    total_cost += 3
                    
            elif b in current_on_table:
                # Misplaced block resting on table (needs pickup and placement: 2 actions)
                total_cost += 2
                
            elif b in current_on:
                # Misplaced block on another block (needs unstacking, then placement)
                # It heavily incentivizes getting blocks safely cleared to the table
                total_cost += 4

        return total_cost
