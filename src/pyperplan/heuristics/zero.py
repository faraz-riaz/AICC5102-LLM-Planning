#
# This file is part of pyperplan.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Zero heuristic for uniform-cost/A* correctness checks."""

from heuristics.heuristic_base import Heuristic


class ZeroHeuristic(Heuristic):
    """Return zero for every search node."""

    def __init__(self, task):
        self.task = task

    def __call__(self, node):
        return 0
