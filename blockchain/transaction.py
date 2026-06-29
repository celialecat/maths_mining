from dataclasses import dataclass, field
from time import time


@dataclass
class Transaction:
    sender: str
    recipient: str
    amount: float
    data: str = ""
    timestamp: float = field(default_factory=time)

    def validate(self) -> tuple[bool, str]:
        if not self.sender or not isinstance(self.sender, str):
            return False, "Invalid sender address"
        if not self.recipient or not isinstance(self.recipient, str):
            return False, "Invalid recipient address"
        if not isinstance(self.amount, (int, float)):
            return False, "Amount must be a number"
        if self.amount <= 0:
            return False, "Amount must be positive"
        if self.sender == self.recipient:
            return False, "Sender and recipient must be different"
        return True, ""

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "data": self.data,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Transaction":
        return cls(
            sender=d["sender"],
            recipient=d["recipient"],
            amount=d["amount"],
            data=d.get("data", ""),
            timestamp=d.get("timestamp", time()),
        )
