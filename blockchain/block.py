import hashlib
import json
from dataclasses import dataclass, field
from time import time

from blockchain.transaction import Transaction


@dataclass
class Block:
    index: int
    timestamp: float
    transactions: list[Transaction]
    proof: str
    previous_hash: str
    problem_id: int = -1

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "proof": self.proof,
            "previous_hash": self.previous_hash,
            "problem_id": self.problem_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Block":
        return cls(
            index=d["index"],
            timestamp=d["timestamp"],
            transactions=[Transaction.from_dict(tx) for tx in d["transactions"]],
            proof=d["proof"],
            previous_hash=d["previous_hash"],
            problem_id=d.get("problem_id", -1),
        )

    def compute_hash(self) -> str:
        block_dict = self.to_dict()
        block_string = json.dumps(block_dict, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
