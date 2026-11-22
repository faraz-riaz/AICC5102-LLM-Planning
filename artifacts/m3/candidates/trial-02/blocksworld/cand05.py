from fnmatch import fnmatch
from heuristics.heuristic_base import Heuristic

def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()

class blocksworldLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the blocksworld domain.

    # Summary
    This heuristic estimates the number of actions to reach the goal by identifying 
    "well-placed" blocks and counting the misplaced ones, with extra penalties for 
    deadlocks (e.g., when a block's target is not yet ready).

    # Assumptions
    - Standard blocksworld dynamics: blocks can be on the table, on other blocks, or held.
    - A block is well-placed if its entire chain of supports down to the table matches 
      (or doesn't contradict) the goal, and no block below it needs to be moved.
    - Misplaced blocks generally take 2 actions to fix (pickup/unstack + putdown/stack).
    - Held blocks take 1 action to fix (stack or putdown).
    - An additional penalty (+2 actions) is applied if a block needs to be moved out of the 
      way but its goal destination is not yet well-placed or clear, heavily encouraging 
      bottom-up construction.

    # Heuristic Initialization
    - Parse the goal state to extract desired `on`, `on-table`, `clear`, `holding`, 
      and `arm-empty` conditions.
    - Build a reverse mapping of `goal_on` to easily check if a block must be on another.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to find `on`, `on-table`, `clear`, and `holding`.
    2. Determine the set of `well_placed` blocks from bottom up:
       - A block on the table is well-placed if it doesn't violate any goals.
       - A block on another well-placed block is well-placed if it matches goal 
         conditions and doesn't block another goal.
       - The held block is well-placed only if holding it is exactly the goal.
    3. Identify `misplaced` blocks as all blocks not in `well_placed`.
    4. Compute base cost: +2 for each misplaced block, or +1 if it is currently held.
    5. Add deadlock penalty: For each misplaced block (not held and not on table), 
       if it must be moved to free the block below it, but its target destination 
       is not ready (either not well-placed or not clear), add +2. This creates a 
       strong gradient to build foundations first.
    6. Ensure the heuristic evaluates to exactly 0 if and only if all goal conditions are met.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.static = task.static
        
        self.goal_on = {}
        self.goal_ontable = set()
        self.goal_clear = set()
        self.goal_holding = None
        self.goal_arm_empty = False
        
        # Extract goal information into accessible data structures
        for fact in self.goals:
            parts = get_parts(fact)
            if parts[0] == "on":
                self.goal_on[parts[1]] = parts[2]
            elif parts[0] == "on-table":
                self.goal_ontable.add(parts[1])
            elif parts[0] == "clear":
                self.goal_clear.add(parts[1])
            elif parts[0] == "holding":
                self.goal_holding = parts[1]
            elif parts[0] == "arm-empty":
                self.goal_arm_empty = True
                
        # Reverse lookup to quickly see if a block requires another block on top of it
        self.goal_on_rev = {}
        for top, bottom in self.goal_on.items():
            self.goal_on_rev[bottom] = top

    def __call__(self, node):
        state = node.state
        
        state_on = {}
        state_ontable = set()
        state_clear = set()
        holding = None
        
        # Parse current state facts
        for fact in state:
            parts = get_parts(fact)
            if parts[0] == "on":
                state_on[parts[1]] = parts[2]
            elif parts[0] == "on-table":
                state_ontable.add(parts[1])
            elif parts[0] == "clear":
                state_clear.add(parts[1])
            elif parts[0] == "holding":
                holding = parts[1]
                
        # Identify all blocks in the domain
        all_blocks = state_ontable.union(state_on.keys()).union(state_on.values())
        if holding:
            all_blocks.add(holding)
            
        well_placed = set()
        # If the goal explicitly asks to hold this block, it is well-placed
        if holding and self.goal_holding == holding:
            well_placed.add(holding)
            
        # Iteratively build the set of well-placed blocks from the table upwards
        changed = True
        while changed:
            changed = False
            
            # 1. Blocks on the table
            for b in state_ontable:
                if b not in well_placed:
                    # To be well-placed on the table, it shouldn't need to be on another block,
                    # and shouldn't be the block we're required to hold.
                    if b not in self.goal_on and b != self.goal_holding:
                        well_placed.add(b)
                        changed = True
                        
            # 2. Blocks on other blocks
            for b, c in state_on.items():
                if b not in well_placed and c in well_placed:
                    # b is on c, and c is well-placed. b is well-placed if:
                    # - we don't need to hold it
                    # - it doesn't need to be on the table
                    # - it doesn't need to be on some other block
                    # - c doesn't need to be clear
                    # - no OTHER block needs to be on c
                    if b != self.goal_holding and b not in self.goal_ontable:
                        if b not in self.goal_on or self.goal_on[b] == c:
                            if c not in self.goal_clear:
                                if c not in self.goal_on_rev or self.goal_on_rev[c] == b:
                                    well_placed.add(b)
                                    changed = True
                                    
        # Blocks that are not well-placed must be moved
        misplaced = all_blocks - well_placed
        
        cost = 0
        for b in misplaced:
            if b == holding:
                # 1 action to place the held block
                cost += 1
                
                # Check for deadlock: target is not ready
                if b in self.goal_on:
                    c = self.goal_on[b]
                    c_ready = (c in well_placed) and (c in state_clear)
                    if not c_ready:
                        cost += 2
            else:
                # 2 actions to move an unheld misplaced block
                cost += 2
                
                # Check for deadlock: b needs to move to free x, but b's target c is not ready
                if b in state_on:
                    x = state_on[b]
                    if x not in well_placed:
                        if b in self.goal_on:
                            c = self.goal_on[b]
                            c_ready = (c in well_placed) and (c in state_clear)
                            if not c_ready:
                                cost += 2
                                
        # Strictly ensure heuristic is 0 if and only if all goals are satisfied
        if cost == 0 and not (self.goals <= state):
            return 1
            
        return cost
