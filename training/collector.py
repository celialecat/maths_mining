import json
import os
from time import time

import config


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
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(episode) + "\n")

    def load_episodes(self) -> list[dict]:
        filepath = os.path.join(self.data_dir, "episodes.jsonl")
        if not os.path.exists(filepath):
            return []
        episodes = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    episodes.append(json.loads(line))
        return episodes

    @property
    def episode_count(self) -> int:
        return len(self.load_episodes())
