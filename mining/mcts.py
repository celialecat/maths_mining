import math
import random
from dataclasses import dataclass, field

import config


@dataclass
class MCTSNode:
    proof_state: str
    parent: "MCTSNode | None" = None
    children: list["MCTSNode"] = field(default_factory=list)
    visits: int = 0
    value: float = 0.0
    is_terminal: bool = False
    is_solved: bool = False
    tactic_applied: str = ""

    def ucb1_score(self, exploration_c: float = config.MCTS_EXPLORATION_CONSTANT) -> float:
        if self.visits == 0:
            return float("inf")
        parent_visits = self.parent.visits if self.parent else 1
        exploitation = self.value / self.visits
        exploration = exploration_c * math.sqrt(
            math.log(parent_visits + 1) / self.visits
        )
        return exploitation + exploration

    def best_child(self) -> "MCTSNode":
        return max(self.children, key=lambda c: c.ucb1_score())

    def add_child(self, proof_state: str, tactic: str) -> "MCTSNode":
        child = MCTSNode(
            proof_state=proof_state,
            parent=self,
            tactic_applied=tactic,
        )
        self.children.append(child)
        return child

    def backpropagate(self, reward: float):
        node: MCTSNode | None = self
        while node is not None:
            node.visits += 1
            node.value += reward
            node = node.parent


def select(node: MCTSNode) -> MCTSNode:
    while node.children and not node.is_terminal:
        node = node.best_child()
    return node


def expand(node: MCTSNode, tactics: list[str]) -> list[MCTSNode]:
    new_children = []
    for tactic in tactics:
        new_state = f"{node.proof_state}\n  {tactic}"
        child = node.add_child(proof_state=new_state, tactic=tactic)
        new_children.append(child)
    return new_children


def pick_random_child(children: list[MCTSNode]) -> MCTSNode | None:
    if not children:
        return None
    return random.choice(children)


def traverse_tree(root: MCTSNode) -> list[MCTSNode]:
    """BFS traversal of the MCTS tree, returning all nodes."""
    nodes: list[MCTSNode] = []
    queue = [root]
    while queue:
        node = queue.pop()
        nodes.append(node)
        queue.extend(node.children)
    return nodes
