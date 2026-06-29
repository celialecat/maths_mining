---
name: testing-mathchain
description: Test the MathChain blockchain dashboard end-to-end. Use when verifying UI changes, auth flows, mining, transactions, or problem visibility.
---

# Testing MathChain

## Quick Start

```bash
cd /home/ubuntu/repos/maths_mining
pip install -r requirements.txt
python run.py
# Server at http://localhost:5000
```

## Environment

- **Mock mode** is default (no Lean 4 or OpenAI needed). The mock verifier accepts known tactics (`rfl`, `simp`, `omega`, `ring`, `norm_num`, `decide`, `trivial`) as valid proofs.
- Set `OPENAI_API_KEY` env var before `run.py` for LLM tactic suggestions, or configure via the dashboard's "OpenAI API Key" section at runtime.
- No database — everything is in-memory. Server restart clears all users, wallets, and blockchain state.

## Auth System

- **Register/Login**: Auth banner at top of page (below status bar). Username + password fields, Login and Register buttons.
- **JWT token**: Stored in `localStorage` as `mathchain_token`. Sent via `Authorization: Bearer <token>` header.
- **Protected endpoints**: `/mine`, `/wallet/new`, `/transactions/new`, `/solutions/submit` — all require login.
- **Public endpoints**: `/chain`, `/problems`, `/status`, `/validate`, `/problems/current` — no auth needed.
- **Button states**: Submit Solution, Auto-Mine (MCTS), Create Wallet, Send Transaction are `disabled` when not logged in.
- **Wallet**: One per user, linked to account. Created via "Create Wallet" button after login.

## Testing Checklist

1. **Fresh state**: Restart server (`fuser -k 5000/tcp; python run.py`) and clear `localStorage` (`localStorage.removeItem('mathchain_token')`) before testing auth flows.
2. **Not-logged-in state**: Verify all 4 action buttons have `disabled="true"` attribute in DOM, status bar shows "Not logged in".
3. **Registration**: Enter username (min 3 chars) + password (min 4 chars), click Register. Verify "Logged in as <name>" appears, buttons become enabled.
4. **Wallet creation**: Click "Create Wallet". Verify 32-char hex address appears in both the address field and auth banner.
5. **Mining**: Click "Auto-Mine (MCTS)". In mock mode, always succeeds in 1 iteration. Verify green success message, Block Explorer updates, Chain counter increments.
6. **Solution submission**: Type a proof in the textarea (e.g. "by omega"). Verify accepted proofs create a block, rejected proofs (e.g. "by sorry") show red error.
7. **Logout**: Click Logout. Verify auth form reappears, buttons disabled, wallet cleared.
8. **Re-login**: Login with same credentials. Verify wallet is restored (same address as before).
9. **Transaction**: Fill recipient + amount, click Send Transaction. Verify success message with transaction index.

## Key DOM Elements

- `#statusUser` — shows username or "Not logged in"
- `#authFormContainer` — login/register form (hidden when logged in)
- `#authUserInfo` — "Logged in as..." (hidden when logged out)
- `#submitBtn`, `#mineBtn`, `#createWalletBtn`, `#sendTxBtn` — action buttons with `disabled` attribute
- `#myAddress` — wallet address field
- `#authDisplayName` — username display in auth banner

## API Testing (curl)

```bash
# Register
curl -s localhost:5000/auth/register -X POST -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"pass1234"}'

# Login
curl -s localhost:5000/auth/login -X POST -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"pass1234"}'

# Check auth (use token from register/login response)
curl -s localhost:5000/auth/me -H "Authorization: Bearer <token>"

# Protected endpoint without token (should return 401)
curl -s localhost:5000/wallet/new

# Protected endpoint with token
curl -s localhost:5000/wallet/new -H "Authorization: Bearer <token>"
```

## Devin Secrets Needed

- None required for basic testing (mock mode)
- `OPENAI_API_KEY` — optional, for LLM-powered mining tactics
