from fnmatch import fnmatch
from heuristics.heuristic_base import Heuristic


def get_parts(fact):
    """Extract the components of a PDDL fact by removing parentheses and splitting the string."""
    return fact[1:-1].split()


class blocksworldLLMHeuristic(Heuristic):
    """
    A domain-dependent heuristic for the blocksworld domain.

    # Summary
    This heuristic estimates the minimum number of actions required to reach a goal state from the current state.
    It identifies which blocks are correctly placed and which are not. For each incorrectly placed block,
    it assigns a base cost of 2 actions (unstack/pickup + stack/putdown), unless the block is currently held,
    in which case it only requires 1 action (stack/putdown).
    Furthermore, it constructs a dependency graph among the incorrect blocks to detect deadlocks—cycles where blocks
    block each other from reaching their goals. Each Strongly Connected Component (SCC) of size > 1 represents 
    a deadlock that requires at least one block to be temporarily placed on the table, adding 2 extra actions.

    # Assumptions
    - Blocks correctly placed on the table or on other correctly placed blocks do not need to move.
    - All other blocks must move at least once.
    - Deadlocks (dependency cycles) require at least one extra table trip (+2 actions).

    # Heuristic Initialization
    - Extract `goal_on`, `goal_clear`, `goal_holding`, and `goal_has_on` conditions from the goals.
    - These mappings establish the exact conditions for a block to be considered "correctly placed".

    # Step-By-Step Thinking for Computing Heuristic
    1. Parse the current state to map the physical position of each block (`current_on`), identify if any block is held (`holding`), and collect all blocks.
    2. Identify all towers starting from the table and evaluate the correctness of each block bottom-up.
       A block is correct if its position satisfies the goal, the block below it is correct,
       and it does not violate any `clear` or `on` goal conditions of other blocks.
    3. Determine the set of incorrect blocks (blocks that must be moved). If there are no incorrect blocks, the heuristic is 0 (goal state reached).
    4. Compute a base cost: 1 action for a held incorrect block, 2 actions for all other incorrect blocks.
    5. Construct a dependency graph among incorrect blocks with the following rules:
       - Rule 1: $X \to Y$ if $X$ is currently on $Y$ (X must move before Y can move).
       - Rule 2: $Y \to X$ if the goal requires $X$ to be on $Y$ (Y must be placed before X can be placed on it).
       - Rule 3: $X \to Z$ if $X$ is currently on some block $W$, and $Z$ is destined to be on $W$ (X must move before W is clear for Z).
    6. Find all Strongly Connected Components (SCCs) in this graph using Tarjan's algorithm. For each SCC with size > 1,
       add 2 to the total cost to account for the necessary temporary table trip to break the deadlock cycle.
    """

    def __init__(self, task):
        """
        Initialize the heuristic by extracting goal conditions.
        """
        self.goals = task.goals
        
        self.goal_on = {}
        self.goal_clear = set()
        self.goal_holding = None
        
        for goal in self.goals:
            parts = get_parts(goal)
            predicate = parts[0]
            if predicate == "on":
                self.goal_on[parts[1]] = parts[2]
            elif predicate == "on-table":
                self.goal_on[parts[1]] = "table"
            elif predicate == "clear":
                self.goal_clear.add(parts[1])
            elif predicate == "holding":
                self.goal_holding = parts[1]
                
        # Helper to quickly check if a block is supposed to have a specific block on it
        self.goal_has_on = {c: b for b, c in self.goal_on.items() if c != "table"}

    def __call__(self, node):
        """Compute an estimate of the minimal number of required actions to solve the blocksworld task."""
        state = node.state
        
        current_on = {}
        holding = None
        all_blocks = set()
        
        # 1. Parse current state
        for fact in state:
            parts = get_parts(fact)
            predicate = parts[0]
            if predicate == "on":
                current_on[parts[1]] = parts[2]
                all_blocks.add(parts[1])
                all_blocks.add(parts[2])
            elif predicate == "on-table":
                current_on[parts[1]] = "table"
                all_blocks.add(parts[1])
            elif predicate == "holding":
                holding = parts[1]
                all_blocks.add(parts[1])
            elif predicate == "clear":
                all_blocks.add(parts[1])
                
        current_has_on = {c: b for b, c in current_on.items() if c != "table"}
        
        correct_blocks = set()
        
        # 2. Check correctness starting from blocks on the table
        for b, c in current_on.items():
            if c == "table":
                curr = b
                while curr is not None:
                    if current_on[curr] == "table":
                        is_correct = (self.goal_on.get(curr, "table") == "table")
                    else:
                        under = current_on[curr]
                        # A block is correct if:
                        # 1. The block under it is correct
                        # 2. It does not violate its own goal position
                        # 3. It does not violate the goal position of another block that should be on `under`
                        # 4. `under` is not required to be clear
                        is_correct = (under in correct_blocks) and \
                                     (self.goal_on.get(curr, under) == under) and \
                                     (self.goal_has_on.get(under, curr) == curr) and \
                                     (under not in self.goal_clear)
                    
                    if is_correct:
                        correct_blocks.add(curr)
                        curr = current_has_on.get(curr)
                    else:
                        break # if curr is incorrect, everything above it is incorrect
        
        # Handle the rare case where holding a specific block is an explicit goal
        if holding and holding == self.goal_holding:
            correct_blocks.add(holding)
                        
        # 3. Determine incorrect blocks
        incorrect_blocks = all_blocks - correct_blocks
        
        if not incorrect_blocks:
            return 0
            
        # 4. Calculate base cost
        base_cost = 0
        for b in incorrect_blocks:
            if b == holding:
                base_cost += 1
            else:
                base_cost += 2
                
        # 5. Build dependency graph for cycle detection
        adj = {b: [] for b in incorrect_blocks}
        for b in incorrect_blocks:
            if b == holding:
                continue
            
            # Rule 1: b must move before its current base can move
            under = current_on.get(b)
            if under in incorrect_blocks:
                adj[b].append(under)
                
            # Rule 2: b's target base must be in place before b can be placed
            target = self.goal_on.get(b)
            if target in incorrect_blocks:
                adj[target].append(b)
                
        # Rule 3: The block currently on Y must move before the block destined for Y can be placed
        for Y, curr_on_Y in current_has_on.items():
            target_on_Y = self.goal_has_on.get(Y)
            if target_on_Y and curr_on_Y != target_on_Y:
                if curr_on_Y in incorrect_blocks and target_on_Y in incorrect_blocks:
                    adj[curr_on_Y].append(target_on_Y)
                
        # 6. Tarjan's algorithm for finding Strongly Connected Components (SCCs)
        index = 0
        indices = {}
        lowlinks = {}
        stack = []
        on_stack = set()
        scc_count = 0

        def strongconnect(v):
            nonlocal index, scc_count
            indices[v] = index
            lowlinks[v] = index
            index += 1
            stack.append(v)
            on_stack.add(v)

            for w in adj.get(v, []):
                if w not in indices:
                    strongconnect(w)
                    lowlinks[v] = min(lowlinks[v], lowlinks[w])
                elif w in on_stack:
                    lowlinks[v] = min(lowlinks[v], indices[w])

            if lowlinks[v] == indices[v]:
                scc_size = 0
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc_size += 1
                    if w == v:
                        break
                if scc_size > 1:
                    scc_count += 1

        for v in adj:
            if v not in indices:
                strongconnect(v)
                
        return base_cost + 2 * scc_count
