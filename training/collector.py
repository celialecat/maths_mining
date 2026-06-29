import json
import logging
import os
from time import time

import config

logger = logging.getLogger(__name__)


class EpisodeCollector:
    """Collects MCTS episode data for training the value network.

    Each episode is a list of (proof_state, outcome) pairs from a single
    mining attempt. Episodes are stored as JSONL files in the training
    data directory.
    """

    def __init__(self, data_dir: str = config.TRAINING_DATA_DIR):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def save_episode(
        self,
        problem_id: int,
        theorem: str,
        trajectory: list[tuple[str, float]],
        success: bool,
    ):
        episode = {
            "timestamp": time(),
            "problem_id": problem_id,
            "theorem": theorem,
            "success": success,
            "trajectory": [
                {"proof_state": state, "outcome": outcome}
                for state, outcome in trajectory
            ],
        }
        filepath = os.path.join(self.data_dir, "episodes.jsonl")
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(episode) + "\n")
        except OSError as e:
            logger.error("Failed to save episode to %s: %s", filepath, e)

    def load_episodes(self) -> list[dict]:
        filepath = os.path.join(self.data_dir, "episodes.jsonl")
        if not os.path.exists(filepath):
            return []
        episodes = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        episodes.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        logger.warning(
                            "Skipping malformed line %d in %s: %s",
                            line_num, filepath, e,
                        )
        except OSError as e:
            logger.error("Failed to read episodes from %s: %s", filepath, e)
        return episodes

    @property
    def episode_count(self) -> int:
        return len(self.load_episodes())
