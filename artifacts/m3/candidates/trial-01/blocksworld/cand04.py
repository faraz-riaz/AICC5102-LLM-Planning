from fnmatch import fnmatch
from heuristics.heuristic_base import Heuristic

class blocksworldLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the blocksworld domain.

    # Summary
    This heuristic estimates the number of actions required to reach a goal state by analyzing 
    the current positions of blocks compared to their goal positions. It identifies "correct" 
    blocks that are already in their final position, and "misplaced" blocks that need to be moved. 
    It calculates a base cost for moving misplaced blocks and adds penalties for cyclic dependencies 
    (e.g., when a block's destination is below it in the same stack).

    # Assumptions
    - A block is in a correct position if it is on its goal destination, the destination itself 
      is correct, and there are no conflicting goals.
    - Misplaced blocks generally take a base of 2 actions to move (pickup/unstack + putdown/stack).
    - If a block is currently held by the robotic arm, placing it costs 1 action if its destination 
      is completely ready; otherwise, it requires 3 actions (put down on table, then pick up and stack later).
    - If a misplaced block's destination is currently located below it in the same stack, the block 
      must temporarily be moved out of the way to the table, requiring an extra 2 actions.

    # Heuristic Initialization
    - Parses the goal conditions to build mappings for each block's target destination (`goal_pos`) 
      and whether a block is required to be explicitly clear (`goal_clear`).
    - Pre-extracts all mentioned blocks from the goal state to avoid repeated work.

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to determine the `current_pos` of each block, identify the `held_block` 
       (if the arm is not empty), and gather the set of `clear_blocks`.
    2. Determine the set of `correct_blocks`. Start with blocks correctly placed on the table, then 
       iteratively add blocks that are correctly placed on top of other correct blocks.
    3. If the state fully satisfies the goal conditions (`self.goals <= state`), return 0.
    4. Calculate the cost for the `held_block` (if applicable). If its destination is the table or 
       a correct, clear block, add 1. Otherwise, add 3.
    5. For each misplaced block (that is not currently held), add a base cost of 2.
    6. For each misplaced block, trace downwards through its current stack. If its goal destination 
       is found below it, add a deadlock penalty of 2 actions.
    7. Sum all these costs to produce the final heuristic estimate.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.goal_pos = {}
        self.goal_clear = {}
        self.all_blocks = set()

        # Parse goal facts to determine the intended position and clear status for each block
        for goal in self.goals:
            parts = goal[1:-1].split()
            predicate = parts[0]
            if predicate == "on":
                b1, b2 = parts[1], parts[2]
                self.goal_pos[b1] = b2
                self.all_blocks.update([b1, b2])
            elif predicate == "on-table":
                b = parts[1]
                self.goal_pos[b] = 'table'
                self.all_blocks.add(b)
            elif predicate == "clear":
                b = parts[1]
                self.goal_clear[b] = True
                self.all_blocks.add(b)

    def __call__(self, node):
        state = node.state
        
        # Heuristic is strictly 0 for goal states
        if self.goals <= state:
            return 0
            
        current_pos = {}
        clear_blocks = set()
        held_block = None

        # Dynamically discover any blocks not mentioned in the goals but present in the state
        all_blocks = set(self.all_blocks)

        # Extract current state information
        for fact in state:
            parts = fact[1:-1].split()
            predicate = parts[0]
            if predicate == "on":
                b1, b2 = parts[1], parts[2]
                current_pos[b1] = b2
                all_blocks.update([b1, b2])
            elif predicate == "on-table":
                b = parts[1]
                current_pos[b] = 'table'
                all_blocks.add(b)
            elif predicate == "holding":
                b = parts[1]
                held_block = b
                current_pos[b] = 'arm'
                all_blocks.add(b)
            elif predicate == "clear":
                b = parts[1]
                clear_blocks.add(b)
                all_blocks.add(b)

        # Determine which blocks are already correctly placed
        correct_blocks = set()
        
        # Base case: Blocks correctly on the table
        for b in all_blocks:
            if current_pos.get(b) == 'table':
                if self.goal_pos.get(b, 'table') == 'table':
                    correct_blocks.add(b)

        # Inductive step: Blocks correctly placed on top of other correct blocks
        changed = True
        while changed:
            changed = False
            for b in all_blocks:
                if b not in correct_blocks and current_pos.get(b) in correct_blocks:
                    c = current_pos[b]
                    if self.goal_pos.get(b, c) == c:
                        # Ensure the supporting block 'c' is not required to be clear
                        if not self.goal_clear.get(c, False):
                            # Ensure no other block MUST strictly be on 'c'
                            other_must_be_on_c = False
                            for z in all_blocks:
                                if z != b and self.goal_pos.get(z) == c:
                                    other_must_be_on_c = True
                                    break
                            if not other_must_be_on_c:
                                correct_blocks.add(b)
                                changed = True

        misplaced = all_blocks - correct_blocks
        
        total_cost = 0

        # Account for the block currently held by the robot (if any)
        if held_block:
            dest = self.goal_pos.get(held_block, 'table')
            if dest == 'table':
                total_cost += 1
            else:
                # The destination block must be correctly placed itself and currently have nothing on it
                if dest in correct_blocks and dest in clear_blocks:
                    total_cost += 1
                else:
                    total_cost += 3  # Place on table, then pick up and stack later

        # Calculate cost for the unheld misplaced blocks
        for b in misplaced:
            if b == held_block:
                continue
            
            # Base cost: 1 action to pick up/unstack, 1 action to stack/put down
            total_cost += 2
            
            # Check for cyclic dependencies: if a block's destination is below it in the current stack
            dest = self.goal_pos.get(b, 'table')
            if dest != 'table':
                curr = current_pos.get(b)
                visited = set()
                while curr not in ('table', 'arm', None) and curr not in visited:
                    if curr == dest:
                        # Requires putting the block on the table temporarily
                        total_cost += 2
                        break
                    visited.add(curr)
                    curr = current_pos.get(curr)

        return total_cost
