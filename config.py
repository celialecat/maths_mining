import os


# --- LLM ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")

# --- Lean 4 ---
LEAN_BINARY = os.environ.get("LEAN_BINARY", "lean")
LEAN_TIMEOUT_SECONDS = int(os.environ.get("LEAN_TIMEOUT_SECONDS", "30"))
LEAN_MOCK_MODE = os.environ.get("LEAN_MOCK_MODE", "auto")  # "auto", "true", "false"

# --- MCTS ---
MCTS_MAX_ITERATIONS = int(os.environ.get("MCTS_MAX_ITERATIONS", "8"))
MCTS_EXPLORATION_CONSTANT = float(os.environ.get("MCTS_EXPLORATION_CONSTANT", "1.41"))
MCTS_MAX_TACTICS_PER_NODE = int(os.environ.get("MCTS_MAX_TACTICS_PER_NODE", "3"))

# --- Blockchain ---
MINING_REWARD = float(os.environ.get("MINING_REWARD", "1.0"))
COINBASE_ADDRESS = "0"

# --- Flask ---
FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5000"))
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

# --- Training ---
TRAINING_DATA_DIR = os.environ.get("TRAINING_DATA_DIR", "training_data")
VALUE_NETWORK_MODEL_PATH = os.environ.get("VALUE_NETWORK_MODEL_PATH", "")
