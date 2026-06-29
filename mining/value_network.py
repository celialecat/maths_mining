import json
import logging
import os
from typing import Optional

import config
from mining.heuristic import rule_based_heuristic

logger = logging.getLogger(__name__)


class ProofValueNetwork:
    """Trainable value estimator for MCTS proof search.

    Estimates the probability that a partial proof state leads to a complete,
    valid proof. Falls back to the rule-based heuristic when no trained model
    is available.

    Training data is collected from MCTS episodes via the training.collector
    module. Once enough data is gathered, run `python -m training.trainer`
    to train the network.
    """

    def __init__(self, model_path: Optional[str] = None):
        self._model = None
        self._model_path = model_path or config.VALUE_NETWORK_MODEL_PATH
        if self._model_path and os.path.exists(self._model_path):
            self._load_model(self._model_path)

    @property
    def is_trained(self) -> bool:
        return self._model is not None

    def evaluate(self, proof_state: str) -> float:
        if self._model is not None:
            return self._model_predict(proof_state)
        return rule_based_heuristic(proof_state)

    def _load_model(self, path: str):
        """Load a trained model from disk.

        Placeholder: replace with actual model loading (e.g. torch.load)
        when a trained model is available.
        """
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Could not load value network from %s: %s", path, e)
            return

        if data.get("type") == "lookup_table":
            self._model = data.get("table", {})
            logger.info("Loaded lookup-table model from %s", path)
        else:
            logger.warning(
                "Unknown model type '%s' in %s, using heuristic",
                data.get("type"),
                path,
            )

    def _model_predict(self, proof_state: str) -> float:
        """Predict value using the loaded model.

        Placeholder: replace with actual model inference.
        Currently supports a simple lookup-table model for testing.
        """
        if isinstance(self._model, dict):
            normalized = proof_state.strip()
            if normalized in self._model:
                return float(self._model[normalized])
        return rule_based_heuristic(proof_state)

    def train_on_episode(self, trajectory: list[tuple[str, float]]):
        """Train on a single MCTS episode.

        Args:
            trajectory: list of (proof_state, outcome) pairs where outcome
                        is 1.0 for states on a successful proof path and
                        0.0 for failed paths.

        Placeholder: replace with actual training loop (SGD on an MLP/transformer).
        """
        pass
