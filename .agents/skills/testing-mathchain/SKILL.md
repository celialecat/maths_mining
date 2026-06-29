---
name: testing-mathchain
description: Test the MathChain blockchain dashboard end-to-end. Use when verifying dashboard UI, mining, transactions, or wallet features.
---

# Testing MathChain Dashboard

## Quick Start

```bash
cd /home/ubuntu/repos/maths_mining
pip install -r requirements.txt
python run.py
# Dashboard at http://localhost:5000
```

The server prints startup diagnostics showing Lean/LLM availability. If port 5000 is in use, kill the existing process first (`pkill -f 'python run.py'`).

## Mock Mode

Without Lean 4 installed or an OpenAI API key, the app runs in **mock mode**:
- Mining uses hardcoded Lean tactics (`rfl`, `simp`, `omega`, `ring`) instead of LLM-generated ones
- Proof verification is simulated (checks known proofs from `problems.json`)
- The status bar shows "Lean: Mock Mode" (yellow) and "LLM: Fallback" (yellow)
- Mining still succeeds and produces valid blocks — it just skips real formal verification

Mock mode is the default for testing without external dependencies.

## Devin Secrets Needed

- `OPENAI_API_KEY` (optional) — enables LLM-based tactic generation for smarter mining. Without it, fallback tactics are used.
- Lean 4 installation (optional) — enables real formal proof verification. Without it, mock verifier is used.

Neither secret is required for basic E2E testing.

## Key Test Flows

### Primary E2E Flow (wallet → TX → mine → verify)
1. **Page load**: Status bar should show Chain: 1, Pending TX: 0, Lean: Mock Mode, LLM: Fallback. Block Explorer shows Block #0 "Genesis Block".
2. **Create wallet**: Click "Create Wallet" → address field populates with 32-char hex string.
3. **Invalid TX**: Send transaction with short recipient (< 8 chars) → red error "Recipient: Address too short".
4. **Valid TX**: Send transaction with valid recipient (16+ chars) and positive amount → green text "Transaction pending for block N", status bar updates Pending TX count.
5. **Mine block**: Click "Start Mining" → success card with green header "Block #N mined successfully! [Mock Mode]", shows theorem name, Lean statement, proof tactic, iteration count. Status bar updates Chain count, Pending TX drops to 0.
6. **Block explorer**: Blocks shown newest-first. New block shows problem #, proof text, transfer TX, and reward TX. Genesis block shows "Genesis Block" with all-zero hash.

### API Endpoints (for non-UI verification)
- `GET /status` — system info (chain_length, mock_mode, llm_available, etc.)
- `GET /chain` — full blockchain data
- `GET /problems` — list of 10 math theorems
- `POST /wallet/new` — generate address
- `POST /transactions/new` — submit transaction (body: `{"sender": ..., "recipient": ..., "amount": ..., "data": ...}`)
- `POST /mine` — mine a block (body: `{"address": ...}`)

## Common Issues

- **Port 5000 already in use**: A previous server instance might still be running. Kill it with `pkill -f 'python run.py'` before starting.
- **Mining might fail on harder theorems**: In mock mode, only known proofs from `problems.json` are accepted. If the deterministically-assigned problem doesn't have a matching hardcoded tactic, mining may fail. This is expected behavior — retry or restart the server (which resets the chain and problem assignment).
- **No persistence**: The blockchain is in-memory. Restarting the server resets everything to genesis.
