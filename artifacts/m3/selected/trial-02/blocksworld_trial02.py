from heuristics.heuristic_base import Heuristic

class blocksworldLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the blocksworld domain.

    # Summary
    The heuristic estimates the number of actions required to reach the goal state from the current state.
    It identifies which blocks are already in their correct final positions (well-placed) and calculates 
    the minimum number of actions needed to move the misplaced blocks to their goal positions. 

    # Assumptions
    - A block is considered "well-placed" if it is in its goal position and all blocks below it are also well-placed.
    - If a block's goal position is underspecified, it is well-placed if its current position doesn't violate any other goals (e.g., resting on a block that needs to be clear).
    - Moving a block directly to its final destination takes 2 actions (unstack/pickup + putdown/stack).
    - If a block must be moved out of the way but its destination is not ready, it must be temporarily placed on the table, requiring 4 actions total (unstack, putdown, pickup, stack).
    - If the robot is currently holding a misplaced block, it saves 1 action from the total sequence.
    - A destination block is "ready" if it is well-placed and clear.

    # Heuristic Initialization
    - Extract goal relations: `goal_on` (mapping of block to its target block underneath), `goal_on_table` (blocks that must be on the table), `goal_clear` (blocks that must be clear), and `goal_under` (blocks that must have another block on top of them).
    - Identify blocks with specific `on` goals (`blocks_with_on_goal`) to distinguish them from blocks with underspecified destinations.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to determine where each block is (`on`, `on-table`), which blocks are `clear`, and if any block is currently `holding`.
    2. Define a recursive function `is_well_placed(b)` that determines if a block `b` is in a valid final position.
       - A held block is never well-placed.
       - A block on the table is well-placed if it doesn't have an explicit `on` goal.
       - A block on another block `c` is well-placed if `c` is well-placed, and the relationship matches the goal (or doesn't violate any goals if underspecified).
    3. For every block `b` that is NOT well-placed:
       - Determine if its destination is ready. A destination is ready if it's the table, or if the target block is well-placed and clear.
       - If `b` is held: cost is 1 if destination is ready, 3 if not.
       - If `b` is on the table: cost is 2 (only pickup and stack needed).
       - If `b` is on another block `c`: 
         - Cost is 2 if destination is ready (unstack and stack).
         - If destination is not ready, check if `b` MUST move to clear `c` (because `c` is not well-placed, or `c` needs to be clear/under another block). If yes, `b` must go to the table (cost 4). Otherwise, `b` can wait on `c` (cost 2).
    4. Sum the costs for all misplaced blocks to get the final heuristic value.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.static_facts = task.static

        self.goal_on = {}
        self.goal_on_table = set()
        self.goal_clear = set()
        self.goal_under = set()
        self.blocks_with_on_goal = set()

        # Extract goals into easily accessible mappings
        for goal in self.goals:
            parts = goal[1:-1].split()
            if parts[0] == "on":
                b, c = parts[1], parts[2]
                self.goal_on[b] = c
                self.goal_under.add(c)
                self.blocks_with_on_goal.add(b)
            elif parts[0] == "on-table":
                self.goal_on_table.add(parts[1])
            elif parts[0] == "clear":
                self.goal_clear.add(parts[1])

    def __call__(self, node):
        state = node.state

        state_on = {}
        state_on_table = set()
        state_clear = set()
        state_holding = None
        all_blocks = set()

        # Parse current state facts
        for fact in state:
            parts = fact[1:-1].split()
            if parts[0] == "on":
                state_on[parts[1]] = parts[2]
                all_blocks.add(parts[1])
                all_blocks.add(parts[2])
            elif parts[0] == "on-table":
                state_on_table.add(parts[1])
                all_blocks.add(parts[1])
            elif parts[0] == "clear":
                state_clear.add(parts[1])
                all_blocks.add(parts[1])
            elif parts[0] == "holding":
                state_holding = parts[1]
                all_blocks.add(parts[1])

        well_placed_cache = {}

        def is_well_placed(b, visited=None):
            if b is None:
                return False
            if b in well_placed_cache:
                return well_placed_cache[b]
                
            if visited is None:
                visited = set()
            if b in visited:
                return False # Cycle detected, blocks are not well-placed
            visited.add(b)

            if b == state_holding:
                ans = False
            elif b in state_on_table:
                # Well-placed on table if it doesn't explicitly need to be on a block
                ans = (b not in self.blocks_with_on_goal)
            else:
                c = state_on.get(b)
                if c is None:
                    ans = False
                elif b in self.blocks_with_on_goal:
                    if self.goal_on.get(b) == c:
                        ans = is_well_placed(c, visited)
                    else:
                        ans = False
                else:
                    # Target underspecified. Check if b being on c violates any other block's goal
                    if b in self.goal_on_table:
                        ans = False
                    elif c in self.goal_clear:
                        ans = False
                    elif c in self.goal_under:
                        ans = False
                    else:
                        ans = is_well_placed(c, visited)

            well_placed_cache[b] = ans
            return ans

        total_cost = 0

        # Evaluate the cost for every block to reach its final position
        for b in all_blocks:
            if is_well_placed(b):
                continue
            
            # Determine if the specific destination for this block is completely ready
            dest_ready = False
            if b in self.goal_on:
                dest = self.goal_on[b]
                if is_well_placed(dest) and (dest in state_clear):
                    dest_ready = True
            else:
                dest_ready = True # Table destination or no constraints

            # Assign heuristic costs based on current position and destination readiness
            if b == state_holding:
                if dest_ready:
                    total_cost += 1
                else:
                    total_cost += 3
            elif b in state_on_table:
                if dest_ready:
                    total_cost += 2
                else:
                    total_cost += 2
            else:
                if dest_ready:
                    total_cost += 2
                else:
                    c = state_on.get(b)
                    must_clear_c = False
                    
                    # Verify if it must be shifted to the table to make way for others
                    if c is None:
                        must_clear_c = True
                    elif not is_well_placed(c):
                        must_clear_c = True
                    elif c in self.goal_clear:
                        must_clear_c = True
                    elif c in self.goal_under:
                        must_clear_c = True
                        
                    if must_clear_c:
                        total_cost += 4
                    else:
                        total_cost += 2

        return total_cost
