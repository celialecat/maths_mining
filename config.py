"""Shared constants and configuration for MathChain."""

# --- Problem Database ---
PROBLEM_DB = [
    {"id": 0, "statement": "theorem add_zero_custom (n : Nat) : n + 0 = n :="},
    {"id": 1, "statement": "theorem eq_self (a : Nat) : a = a :="},
]

# --- LLM Settings ---
LLM_MODEL = "gpt-3.5-turbo"
LLM_MAX_TOKENS = 50
LLM_TEMPERATURE = 0.7
LLM_FALLBACK_TACTICS = ["rfl", "simp", "sorry"]

# --- MCTS Parameters ---
MCTS_EXPLORATION_CONSTANT = 1.41
MCTS_DEFAULT_MAX_ITERATIONS = 5
MCTS_WEB_MAX_ITERATIONS = 4

# --- Lean Verification ---
LEAN_TIMEOUT_SECONDS = 10
LEAN_IMPORT_HEADER = "import Mathlib"

# --- Blockchain ---
MINING_REWARD_AMOUNT = 1
GENESIS_PROOF = "by rfl"
GENESIS_PREVIOUS_HASH = "1"
