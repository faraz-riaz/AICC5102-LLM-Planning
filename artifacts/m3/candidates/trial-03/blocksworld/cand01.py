from fnmatch import fnmatch
from heuristics.heuristic_base import Heuristic


def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()


class blocksworldLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the blocksworld domain.

    # Summary
    This heuristic estimates the minimum number of actions required to reach the goal state. 
    It computes the heuristic by determining which blocks are out of place and evaluates 
    the necessary unstack/pickup and stack/putdown actions. It also detects tower deadlocks 
    where a block must be placed on another block that is currently below it.

    # Assumptions
    - Blocks can be stacked on each other (at most one on top of another) or on the table.
    - The robot arm can hold at most one block at a time.
    - A valid state contains no cyclic supports (towers end at the table or are held).
    - The goal specifies target relationships, such as `on`, `on-table`, `clear`, or `holding`.

    # Heuristic Initialization
    - The task goals are parsed into distinct data structures: `goal_on`, `goal_on_table`, `goal_clear`, 
      and `goal_holding`.
    - A reverse mapping `goal_child_of` is created to know which block is expected to be 
      on top of a given block, allowing efficient blocking-check.
    - Static facts are collected, although the blocksworld domain does not contain any.

    # Step-By-Step Thinking for Computing Heuristic
    1. Check if the current state satisfies all goals. If it does, return 0 immediately.
    2. Parse the current state to populate `current_on` (mapping blocks to their support), 
       identify `current_held`, and extract all blocks into a set.
    3. Recursively determine for each block whether it "needs to move". A block must be moved if:
       - It is currently held, and the goal doesn't require it to be held.
       - It is supported by a block that needs to move.
       - It is not on its required goal support (another block or the table).
       - It is on a block that must be clear.
       - It is on a block that is supposed to have a different block on it.
    4. Calculate the base action cost for every block that needs to move:
       - If it is already held, or its final destination is to be held, it takes 1 action.
       - Otherwise, it takes 2 actions (unstack/pickup + putdown/stack).
    5. Check for deadlocks: if a block `x` needs to move and must be placed on `z`, but `x` 
       is currently stacked somewhere above `z`, it cannot go directly to `z`. It must be 
       placed on the table temporarily, costing 2 extra actions.
    6. The final heuristic value is the sum of these costs.
    """

    def __init__(self, task):
        self.goals = task.goals
        self.static_facts = task.static

        # Extract goals into easily accessible mappings
        self.goal_on = {}
        self.goal_on_table = set()
        self.goal_clear = set()
        self.goal_holding = None
        self.goal_child_of = {}

        for goal in self.goals:
            parts = get_parts(goal)
            pred = parts[0]
            if pred == 'on':
                self.goal_on[parts[1]] = parts[2]
                self.goal_child_of[parts[2]] = parts[1]
            elif pred == 'on-table':
                self.goal_on_table.add(parts[1])
            elif pred == 'clear':
                self.goal_clear.add(parts[1])
            elif pred == 'holding':
                self.goal_holding = parts[1]

    def __call__(self, node):
        state = node.state
        
        # Ensure the heuristic is strictly 0 for goal states
        if self.goals <= state:
            return 0
            
        current_on = {}
        current_held = None
        blocks = set()
        
        # Parse the current state
        for fact in state:
            parts = get_parts(fact)
            pred = parts[0]
            if pred == 'on':
                current_on[parts[1]] = parts[2]
                blocks.add(parts[1])
                blocks.add(parts[2])
            elif pred == 'on-table':
                current_on[parts[1]] = 'table'
                blocks.add(parts[1])
            elif pred == 'holding':
                current_held = parts[1]
                blocks.add(parts[1])
            elif pred == 'clear':
                blocks.add(parts[1])
                
        memo = {}
        
        def get_needs_to_move(x):
            """Evaluate if block x needs to be moved from its current location."""
            if x in memo:
                return memo[x]
                
            if x == 'table':
                return False
                
            if x == current_held:
                if self.goal_holding == x:
                    memo[x] = False
                    return False
                memo[x] = True
                return True
                
            y = current_on.get(x)
            if y is None:
                # Fallback safeguard against malformed data structures
                memo[x] = True 
                return True
                
            # If the block it is resting on needs to move, this block must move as well
            if get_needs_to_move(y):
                memo[x] = True
                return True
                
            # Contradicts its own `on` goal
            if x in self.goal_on and self.goal_on[x] != y:
                memo[x] = True
                return True
                
            # Contradicts its own `on-table` goal
            if x in self.goal_on_table and y != 'table':
                memo[x] = True
                return True
                
            # If the block's eventual goal is to end up in the arm
            if x == self.goal_holding:
                memo[x] = True
                return True
                
            if y != 'table':
                # Obstructs a block that is supposed to be clear
                if y in self.goal_clear:
                    memo[x] = True
                    return True
                    
                # Obstructs a block that is supposed to have a different block on it
                if y in self.goal_child_of and self.goal_child_of[y] != x:
                    memo[x] = True
                    return True
                    
            memo[x] = False
            return False

        def is_above(x, z):
            """Check if block x is positioned somewhere in the tower above block z."""
            curr = current_on.get(x)
            while curr is not None and curr != 'table':
                if curr == z:
                    return True
                curr = current_on.get(curr)
            return False

        total_cost = 0
        
        # Calculate cost for every block that has to move
        for x in blocks:
            if get_needs_to_move(x):
                if x == current_held:
                    # Just putdown/stack needed
                    total_cost += 1
                elif x == self.goal_holding:
                    # Just pickup/unstack needed to fulfill the holding goal
                    total_cost += 1
                else:
                    # Full pickup/unstack + putdown/stack cycle
                    total_cost += 2
                    
                    z = self.goal_on.get(x)
                    if z is not None and is_above(x, z):
                        # Block x must go on block z, but block x is currently blocking z.
                        # Meaning x has to go to the table temporarily.
                        total_cost += 2
                        
        return total_cost
