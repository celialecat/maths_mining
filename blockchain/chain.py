import threading
from time import time

from blockchain.block import Block
from blockchain.transaction import Transaction
from mining.lean_verifier import verify_lean_proof
from problems.problem_db import ProblemDB
import config


class Blockchain:
    def __init__(self):
        self.chain: list[Block] = []
        self.pending_transactions: list[Transaction] = []
        self._lock = threading.Lock()
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis = Block(
            index=0,
            timestamp=time(),
            transactions=[],
            proof="genesis",
            previous_hash="0" * 64,
            problem_id=-1,
        )
        self.chain.append(genesis)

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    @property
    def length(self) -> int:
        return len(self.chain)

    def add_transaction(self, transaction: Transaction) -> int:
        is_valid, error = transaction.validate()
        if not is_valid:
            raise ValueError(error)
        with self._lock:
            self.pending_transactions.append(transaction)
            return self.last_block.index + 1

    def add_reward_transaction(self, recipient: str):
        reward_tx = Transaction(
            sender=config.COINBASE_ADDRESS,
            recipient=recipient,
            amount=config.MINING_REWARD,
            data="Block Reward",
        )
        with self._lock:
            self.pending_transactions.append(reward_tx)

    def create_block(self, proof: str, problem_id: int) -> Block:
        with self._lock:
            previous_hash = self.last_block.compute_hash()
            block = Block(
                index=len(self.chain),
                timestamp=time(),
                transactions=list(self.pending_transactions),
                proof=proof,
                previous_hash=previous_hash,
                problem_id=problem_id,
            )
            self.pending_transactions = []
            self.chain.append(block)
            return block

    def validate_chain(self, problem_db: "ProblemDB | None" = None) -> tuple[bool, str]:
        errors: list[str] = []
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current.previous_hash != previous.compute_hash():
                errors.append(f"Block {i}: previous_hash mismatch")
                continue
            if problem_db is not None and current.problem_id >= 0:
                problem = problem_db.get_problem(current.problem_id)
                if problem is None:
                    errors.append(f"Block {i}: unknown problem_id {current.problem_id}")
                    continue
                result = verify_lean_proof(problem["statement"], current.proof)
                if not result.is_complete:
                    errors.append(
                        f"Block {i}: proof verification failed for problem {current.problem_id}"
                    )
        if errors:
            return False, "; ".join(errors)
        return True, ""

    def get_solved_problem_ids(self) -> set[int]:
        solved = set()
        for block in self.chain:
            if block.problem_id >= 0:
                solved.add(block.problem_id)
        return solved

    def get_chain_data(self) -> dict:
        return {
            "chain": [block.to_dict() for block in self.chain],
            "length": len(self.chain),
            "pending_transactions": [
                tx.to_dict() for tx in self.pending_transactions
            ],
            "solved_problems": list(self.get_solved_problem_ids()),
        }
