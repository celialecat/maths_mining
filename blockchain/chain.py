import threading
from time import time

from blockchain.block import Block
from blockchain.transaction import Transaction
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

    def validate_chain(self) -> tuple[bool, str]:
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current.previous_hash != previous.compute_hash():
                return False, f"Block {i}: previous_hash mismatch"
        return True, ""

    def get_chain_data(self) -> dict:
        return {
            "chain": [block.to_dict() for block in self.chain],
            "length": len(self.chain),
            "pending_transactions": [
                tx.to_dict() for tx in self.pending_transactions
            ],
        }
