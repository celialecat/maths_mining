"""MCTS utility functions.

Extracts the UCB1 score calculation used during the tree selection phase,
making it reusable and testable independently of the mining logic.
"""

import math

from config import MCTS_EXPLORATION_CONSTANT


def ucb1_score(child_value, child_visits, parent_visits, exploration=None):
    """Compute the UCB1 score for MCTS node selection.

    UCB1 balances exploitation (high average value) with exploration
    (less-visited nodes).

    Args:
        child_value: Cumulative value of the child node.
        child_visits: Number of times the child has been visited.
        parent_visits: Number of times the parent has been visited.
        exploration: Exploration constant (defaults to config value).

    Returns:
        The UCB1 score as a float.
    """
    if exploration is None:
        exploration = MCTS_EXPLORATION_CONSTANT
    epsilon = 1e-6
    exploitation = child_value / (child_visits + epsilon)
    explore_term = exploration * math.sqrt(
        math.log(parent_visits + 1) / (child_visits + epsilon)
    )
    return exploitation + explore_term
