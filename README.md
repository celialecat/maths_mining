# MathChain (maths_mining)

A blockchain where proof-of-work is replaced by solving real mathematical theorems. Miners use an MCTS + LLM approach (inspired by AlphaProof) to discover proofs, which are formally verified by the Lean 4 compiler.

## How it works

1. **Transaction** — Users record data/transfers on the blockchain
2. **Mining** — To add a block, a miner must solve a math problem assigned deterministically from the previous block's hash
3. **Proof search** — MCTS tree search explores proof tactics suggested by an LLM (OpenAI) or fallback heuristics
4. **Verification** — Each candidate proof is verified by the Lean 4 compiler (or a mock verifier in demo mode)
5. **Reward** — Successful miners receive a block reward

## Quick start

```bash
git clone https://github.com/celialecat/maths_mining.git
cd maths_mining
pip install -r requirements.txt

# (Optional) Enable LLM-powered mining
export OPENAI_API_KEY="sk-..."

python run.py
# Open http://localhost:5000
```

The app works out of the box in **mock mode** (no Lean installation required). Install Lean 4 for real proof verification.

## Project structure

```
config.py                  # Configuration (env vars, constants)
run.py                     # Entrypoint

blockchain/
  block.py                 # Block model
  transaction.py           # Transaction model + validation
  chain.py                 # Blockchain: chain management, validation

mining/
  mcts.py                  # MCTS tree search
  lean_verifier.py         # Lean 4 proof verification (real + mock)
  llm_prover.py            # LLM tactic generation (OpenAI + fallback)
  heuristic.py             # Rule-based proof value heuristic
  value_network.py         # Trainable value estimator (scaffold)
  miner.py                 # AlphaProofMiner: orchestrates MCTS + LLM + Lean

problems/
  problems.json            # Math problem database
  problem_db.py            # Problem selection logic

training/
  collector.py             # Episode data collection
  trainer.py               # Value network training script

api/
  routes.py                # Flask API endpoints
  validators.py            # Input validation

templates/
  index.html               # Web dashboard
```

## Configuration (environment variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(empty)* | OpenAI API key for LLM mining. Falls back to hardcoded tactics if unset. |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | OpenAI model to use |
| `LEAN_MOCK_MODE` | `auto` | `auto` (mock if Lean not found), `true`, or `false` |
| `MCTS_MAX_ITERATIONS` | `8` | Max MCTS iterations per mining attempt |
| `FLASK_PORT` | `5000` | Server port |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |

## Training the value network

After running several mining episodes, train the value estimator:

```bash
python -m training.trainer
```

Then set `VALUE_NETWORK_MODEL_PATH` to the output model file.

## Prerequisites

- **Python 3.10+**
- **Lean 4** (optional, for real proof verification): [Installation guide](https://leanprover.github.io/lean4/doc/setup.html)
- **OpenAI API key** (optional, for LLM-powered mining)
