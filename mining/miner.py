import logging
from dataclasses import dataclass

import config
from mining.lean_verifier import VerificationResult, verify_lean_proof
from mining.llm_prover import LLMProver
from mining.mcts import MCTSNode, expand, pick_random_child, select
from mining.value_network import ProofValueNetwork

logger = logging.getLogger(__name__)


@dataclass
class MiningResult:
    success: bool
    proof: str
    iterations_used: int
    problem_id: int
    theorem: str
    logs: list[str]
    mock_mode: bool = False


class AlphaProofMiner:
    def __init__(self):
        self.llm = LLMProver()
        self.value_net = ProofValueNetwork()
        self._episode_trajectory: list[tuple[str, float]] = []

    def mine(
        self,
        theorem_statement: str,
        problem_id: int,
        max_iterations: int = config.MCTS_MAX_ITERATIONS,
    ) -> MiningResult:
        logs: list[str] = []
        root = MCTSNode(proof_state="by")
        self._episode_trajectory = []
        mock_mode = False
        llm_failures = 0

        for i in range(max_iterations):
            logs.append(f"Iteration {i + 1}/{max_iterations}")

            # 1. Selection
            node = select(root)

            # 2. Expansion
            if not node.is_terminal:
                try:
                    tactics = self.llm.suggest_tactics(
                        theorem_statement,
                        node.proof_state,
                        n=config.MCTS_MAX_TACTICS_PER_NODE,
                    )
                except RuntimeError as e:
                    llm_failures += 1
                    logs.append(f"  LLM error (attempt {llm_failures}): {e}")
                    logger.warning("LLM failed on iteration %d: %s", i + 1, e)
                    if llm_failures >= max_iterations:
                        raise RuntimeError(
                            "LLM API failed on all iterations; cannot mine"
                        ) from e
                    continue
                new_children = expand(node, tactics)
                logs.append(f"  Expanded with tactics: {tactics}")
                node = pick_random_child(new_children) or node

            # 3. Simulation / Verification
            result: VerificationResult = verify_lean_proof(
                theorem_statement, node.proof_state
            )
            mock_mode = result.mock

            reward = 0.0
            if not result.is_valid:
                node.is_terminal = True
                reward = -1.0
                logs.append(f"  Invalid proof: {result.output}")
            elif result.is_complete:
                node.is_terminal = True
                node.is_solved = True
                reward = 1.0
                logs.append(f"  Proof found! {node.proof_state}")
                self._record_trajectory(root, reward=1.0)
                return MiningResult(
                    success=True,
                    proof=node.proof_state,
                    iterations_used=i + 1,
                    problem_id=problem_id,
                    theorem=theorem_statement,
                    logs=logs,
                    mock_mode=mock_mode,
                )
            else:
                reward = self.value_net.evaluate(node.proof_state)
                logs.append(f"  Partial proof, heuristic score: {reward:.3f}")

            # 4. Backpropagation
            node.backpropagate(reward)
            self._episode_trajectory.append((node.proof_state, reward))

        # Failed to find proof
        self._record_trajectory(root, reward=0.0)
        best = self._find_best_attempt(root)
        logs.append("Mining failed: no complete proof found")
        return MiningResult(
            success=False,
            proof=best,
            iterations_used=max_iterations,
            problem_id=problem_id,
            theorem=theorem_statement,
            logs=logs,
            mock_mode=mock_mode,
        )

    def _find_best_attempt(self, root: MCTSNode) -> str:
        best_node = root
        best_score = -float("inf")
        queue = [root]
        while queue:
            node = queue.pop()
            if node.visits > 0:
                avg = node.value / node.visits
                if avg > best_score and not node.is_terminal:
                    best_score = avg
                    best_node = node
            queue.extend(node.children)
        return best_node.proof_state

    def _record_trajectory(self, root: MCTSNode, reward: float):
        trajectory: list[tuple[str, float]] = []
        queue = [root]
        while queue:
            node = queue.pop()
            if node.visits > 0:
                trajectory.append((node.proof_state, reward if node.is_solved else 0.0))
            queue.extend(node.children)
        if trajectory:
            self.value_net.train_on_episode(trajectory)
