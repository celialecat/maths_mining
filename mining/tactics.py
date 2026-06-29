"""Shared Lean 4 tactic definitions.

Single source of truth for the tactic sets used across the mining subsystem:
heuristic scoring, mock verification, and LLM fallback generation.
"""

STRONG_TACTICS: set[str] = {"rfl", "simp", "omega", "ring", "norm_num", "decide"}

VALID_TACTICS: set[str] = STRONG_TACTICS | {"trivial"}

FALLBACK_TACTICS: list[str] = [
    "rfl",
    "simp",
    "omega",
    "ring",
    "norm_num",
    "decide",
    "trivial",
    "simp [Nat.add_comm]",
    "simp [Nat.mul_comm]",
    "simp [Nat.add_assoc]",
]
