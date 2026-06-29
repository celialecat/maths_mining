import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class ProblemDB:
    def __init__(self, problems_file: Optional[str] = None):
        if problems_file is None:
            problems_file = os.path.join(
                os.path.dirname(__file__), "problems.json"
            )
        try:
            with open(problems_file, "r", encoding="utf-8") as f:
                self.problems: list[dict] = json.load(f)
        except FileNotFoundError:
            raise RuntimeError(
                f"Problems database not found: {problems_file}"
            )
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Problems database is malformed JSON: {problems_file}: {e}"
            )
        if not self.problems:
            raise RuntimeError(
                f"Problems database is empty: {problems_file}"
            )
        logger.info("Loaded %d problems from %s", len(self.problems), problems_file)

    def get_problem(self, problem_id: int) -> Optional[dict]:
        for p in self.problems:
            if p["id"] == problem_id:
                return p
        return None

    def get_problem_for_block(self, previous_hash: str) -> dict:
        seed = int(previous_hash[:16], 16)
        idx = seed % len(self.problems)
        return self.problems[idx]

    def list_problems(self) -> list[dict]:
        return list(self.problems)

    @property
    def count(self) -> int:
        return len(self.problems)
