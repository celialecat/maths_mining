"""Training script for the proof value network.

Usage:
    python -m training.trainer

Reads episode data collected by EpisodeCollector and trains the value
network. Currently outputs a simple lookup-table model; replace with
neural network training when enough data is available.
"""

import json
import os
from collections import defaultdict

import config
from training.collector import EpisodeCollector


def train_lookup_table(data_dir: str = config.TRAINING_DATA_DIR) -> dict:
    """Train a simple lookup-table model from collected episodes.

    For each proof_state seen across episodes, computes the average
    outcome. This is a baseline; replace with a proper neural network
    for better generalisation.
    """
    collector = EpisodeCollector(data_dir)
    episodes = collector.load_episodes()

    if not episodes:
        print("No training data found. Run some mining episodes first.")
        return {}

    state_outcomes: dict[str, list[float]] = defaultdict(list)
    for episode in episodes:
        for entry in episode.get("trajectory", []):
            state = entry["proof_state"].strip()
            outcome = float(entry["outcome"])
            state_outcomes[state].append(outcome)

    table = {}
    for state, outcomes in state_outcomes.items():
        table[state] = sum(outcomes) / len(outcomes)

    print(f"Trained on {len(episodes)} episodes, {len(table)} unique states")
    return table


def save_model(table: dict, output_path: str = ""):
    if not output_path:
        output_path = os.path.join(config.TRAINING_DATA_DIR, "value_model.json")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    model = {"type": "lookup_table", "table": table}
    with open(output_path, "w") as f:
        json.dump(model, f, indent=2)
    print(f"Model saved to {output_path}")


def main():
    table = train_lookup_table()
    if table:
        save_model(table)


if __name__ == "__main__":
    main()
