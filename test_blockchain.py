import hashlib
import json
import math
import os
from unittest.mock import patch, MagicMock

import pytest

from blockchain import MCTSNode, AlphaProofMiner, Blockchain, app, PROBLEM_DB


# ── MCTSNode ────────────────────────────────────────────────────────────────

class TestMCTSNode:
    def test_init_defaults(self):
        node = MCTSNode(proof_state="by rfl")
        assert node.proof_state == "by rfl"
        assert node.parent is None
        assert node.children == []
        assert node.visits == 0
        assert node.value == 0.0
        assert node.is_terminal is False
        assert node.is_solved is False

    def test_init_with_parent(self):
        parent = MCTSNode(proof_state="by")
        child = MCTSNode(proof_state="by\n  rfl", parent=parent)
        assert child.parent is parent
        assert child.proof_state == "by\n  rfl"

    def test_children_relationship(self):
        root = MCTSNode(proof_state="by")
        c1 = MCTSNode(proof_state="by\n  rfl", parent=root)
        c2 = MCTSNode(proof_state="by\n  simp", parent=root)
        root.children.extend([c1, c2])
        assert len(root.children) == 2
        assert root.children[0].parent is root
        assert root.children[1].parent is root

    def test_mutability(self):
        node = MCTSNode(proof_state="by")
        node.visits = 10
        node.value = 5.5
        node.is_terminal = True
        node.is_solved = True
        assert node.visits == 10
        assert node.value == 5.5
        assert node.is_terminal is True
        assert node.is_solved is True


# ── Blockchain ──────────────────────────────────────────────────────────────

class TestBlockchain:
    def setup_method(self):
        self.bc = Blockchain()

    # -- Genesis block --
    def test_genesis_block_created(self):
        assert len(self.bc.chain) == 1

    def test_genesis_block_fields(self):
        genesis = self.bc.chain[0]
        assert genesis["index"] == 1
        assert genesis["proof"] == "by rfl"
        assert genesis["previous_hash"] == "1"
        assert genesis["transactions"] == []
        assert "timestamp" in genesis

    # -- new_block --
    def test_new_block_appends(self):
        prev_hash = Blockchain.hash(self.bc.last_block)
        block = self.bc.new_block(proof="by simp", previous_hash=prev_hash)
        assert len(self.bc.chain) == 2
        assert block["index"] == 2
        assert block["proof"] == "by simp"
        assert block["previous_hash"] == prev_hash

    def test_new_block_clears_pending_transactions(self):
        self.bc.new_transaction("a", "b", 10)
        assert len(self.bc.current_transactions) == 1
        self.bc.new_block(proof="by rfl", previous_hash="abc")
        assert self.bc.current_transactions == []

    def test_new_block_includes_pending_transactions(self):
        self.bc.new_transaction("a", "b", 5)
        self.bc.new_transaction("c", "d", 3)
        block = self.bc.new_block(proof="by rfl", previous_hash="xyz")
        assert len(block["transactions"]) == 2

    def test_new_block_previous_hash_fallback(self):
        block = self.bc.new_block(proof="by rfl", previous_hash=None)
        expected = Blockchain.hash(self.bc.chain[-2])
        assert block["previous_hash"] == expected

    # -- new_transaction --
    def test_new_transaction_returns_next_index(self):
        idx = self.bc.new_transaction("alice", "bob", 1)
        assert idx == self.bc.last_block["index"] + 1

    def test_new_transaction_stored(self):
        self.bc.new_transaction("alice", "bob", 42, data="memo")
        tx = self.bc.current_transactions[0]
        assert tx["sender"] == "alice"
        assert tx["recipient"] == "bob"
        assert tx["amount"] == 42
        assert tx["data"] == "memo"

    def test_new_transaction_default_data(self):
        self.bc.new_transaction("a", "b", 1)
        assert self.bc.current_transactions[0]["data"] == ""

    def test_multiple_transactions(self):
        self.bc.new_transaction("a", "b", 1)
        self.bc.new_transaction("c", "d", 2)
        self.bc.new_transaction("e", "f", 3)
        assert len(self.bc.current_transactions) == 3

    # -- last_block --
    def test_last_block_is_genesis_initially(self):
        assert self.bc.last_block["index"] == 1

    def test_last_block_updates_after_new_block(self):
        self.bc.new_block(proof="p", previous_hash="h")
        assert self.bc.last_block["index"] == 2

    # -- hash --
    def test_hash_deterministic(self):
        block = self.bc.chain[0]
        h1 = Blockchain.hash(block)
        h2 = Blockchain.hash(block)
        assert h1 == h2

    def test_hash_is_sha256_hex(self):
        h = Blockchain.hash(self.bc.chain[0])
        assert len(h) == 64
        int(h, 16)  # should not raise

    def test_hash_matches_manual_computation(self):
        block = self.bc.chain[0]
        expected = hashlib.sha256(
            json.dumps(block, sort_keys=True).encode()
        ).hexdigest()
        assert Blockchain.hash(block) == expected

    def test_hash_changes_with_different_blocks(self):
        b1 = self.bc.chain[0]
        self.bc.new_block(proof="different", previous_hash="diff")
        b2 = self.bc.chain[1]
        assert Blockchain.hash(b1) != Blockchain.hash(b2)

    # -- get_problem_for_next_block --
    def test_get_problem_returns_valid_entry(self):
        h = Blockchain.hash(self.bc.chain[0])
        problem = self.bc.get_problem_for_next_block(h)
        assert "id" in problem
        assert "statement" in problem
        assert problem in PROBLEM_DB

    def test_get_problem_deterministic(self):
        h = Blockchain.hash(self.bc.chain[0])
        p1 = self.bc.get_problem_for_next_block(h)
        p2 = self.bc.get_problem_for_next_block(h)
        assert p1 == p2

    def test_get_problem_index_wraps(self):
        # Any hex hash should produce a valid PROBLEM_DB index
        for test_hash in ["0" * 64, "f" * 64, "abcdef1234567890" * 4]:
            problem = self.bc.get_problem_for_next_block(test_hash)
            assert problem in PROBLEM_DB

    # -- verify_lean_proof --
    @patch("blockchain.subprocess.run")
    def test_verify_lean_proof_valid_complete(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", stderr="")
        valid, complete = Blockchain.verify_lean_proof("theorem t : True :=", "by trivial")
        assert valid is True
        assert complete is True

    @patch("blockchain.subprocess.run")
    def test_verify_lean_proof_error(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", stderr="error: unknown tactic")
        valid, complete = Blockchain.verify_lean_proof("theorem t : True :=", "by bad")
        assert valid is False
        assert complete is False

    @patch("blockchain.subprocess.run")
    def test_verify_lean_proof_sorry(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="", stderr="warning: declaration uses 'sorry'"
        )
        valid, complete = Blockchain.verify_lean_proof("theorem t : True :=", "by sorry")
        assert valid is True
        assert complete is False

    @patch("blockchain.subprocess.run")
    def test_verify_lean_proof_cleans_up_temp_file(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", stderr="")
        Blockchain.verify_lean_proof("theorem t : True :=", "by rfl")
        # The method removes temp files in the finally block;
        # just verify no temp_proof_* files remain in cwd
        leftover = [f for f in os.listdir(".") if f.startswith("temp_proof_")]
        assert leftover == []

    @patch("blockchain.subprocess.run", side_effect=Exception("lean not found"))
    def test_verify_lean_proof_exception(self, mock_run):
        valid, complete = Blockchain.verify_lean_proof("theorem t : True :=", "by rfl")
        assert valid is False
        assert complete is False

    @patch("blockchain.subprocess.run")
    def test_verify_lean_proof_writes_correct_file(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", stderr="")
        Blockchain.verify_lean_proof("theorem add_zero (n : Nat) : n + 0 = n :=", "by rfl")
        call_args = mock_run.call_args
        filename = call_args[0][0][1]  # ["lean", filename]
        assert filename.startswith("temp_proof_")
        assert filename.endswith(".lean")

    @patch("blockchain.subprocess.run")
    def test_verify_lean_proof_passes_timeout(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", stderr="")
        Blockchain.verify_lean_proof("theorem t :=", "by rfl")
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 10


# ── AlphaProofMiner ─────────────────────────────────────────────────────────

class TestAlphaProofMiner:
    def _make_miner(self):
        return AlphaProofMiner("theorem t : True :=", api_key="fake-key")

    # -- _call_llm_for_tactics --
    @patch("blockchain.OpenAI")
    def test_call_llm_returns_tactics(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="rfl\nsimp\ntrivial"))]
        )
        miner = AlphaProofMiner("theorem t : True :=", api_key="k")
        tactics = miner._call_llm_for_tactics("by")
        assert tactics == ["rfl", "simp", "trivial"]

    @patch("blockchain.OpenAI")
    def test_call_llm_filters_blank_lines(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="\nrfl\n\nsimp\n\n"))]
        )
        miner = AlphaProofMiner("theorem t : True :=", api_key="k")
        tactics = miner._call_llm_for_tactics("by")
        assert tactics == ["rfl", "simp"]

    @patch("blockchain.OpenAI")
    def test_call_llm_fallback_on_exception(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API down")
        miner = AlphaProofMiner("theorem t : True :=", api_key="k")
        tactics = miner._call_llm_for_tactics("by")
        assert tactics == ["rfl", "simp", "sorry"]

    # -- _evaluate_heuristic --
    def test_evaluate_heuristic_returns_float(self):
        miner = self._make_miner()
        val = miner._evaluate_heuristic("by rfl")
        assert isinstance(val, float)
        assert 0.0 <= val <= 1.0

    # -- mine --
    @patch.object(Blockchain, "verify_lean_proof", return_value=(True, True))
    @patch("blockchain.OpenAI")
    def test_mine_returns_proof_on_success(self, mock_openai_cls, mock_verify):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="rfl"))]
        )
        miner = AlphaProofMiner("theorem t : True :=", api_key="k")
        result = miner.mine(max_iterations=2)
        assert "rfl" in result

    @patch.object(Blockchain, "verify_lean_proof", return_value=(False, False))
    @patch("blockchain.OpenAI")
    def test_mine_returns_sorry_on_failure(self, mock_openai_cls, mock_verify):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="bad_tactic"))]
        )
        miner = AlphaProofMiner("theorem t : True :=", api_key="k")
        result = miner.mine(max_iterations=2)
        assert result == "by sorry"

    @patch.object(Blockchain, "verify_lean_proof")
    @patch("blockchain.OpenAI")
    def test_mine_backpropagates_visits(self, mock_openai_cls, mock_verify):
        """After mining iterations, root node should have accumulated visits."""
        mock_verify.return_value = (True, False)
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="simp"))]
        )
        miner = AlphaProofMiner("theorem t : True :=", api_key="k")
        miner.mine(max_iterations=3)
        # No assertion on internal state — just verify it runs without error


# ── Flask Routes ────────────────────────────────────────────────────────────

class TestFlaskRoutes:
    def setup_method(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    # -- /chain --
    def test_chain_endpoint(self):
        resp = self.client.get("/chain")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "chain" in data
        assert "length" in data
        assert "pending_transactions" in data
        assert isinstance(data["chain"], list)
        assert data["length"] >= 1

    # -- /wallet/new --
    def test_wallet_new(self):
        resp = self.client.get("/wallet/new")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "address" in data
        assert len(data["address"]) == 32  # UUID without dashes

    def test_wallet_new_unique(self):
        r1 = self.client.get("/wallet/new").get_json()["address"]
        r2 = self.client.get("/wallet/new").get_json()["address"]
        assert r1 != r2

    # -- /transactions/new --
    def test_new_transaction_success(self):
        resp = self.client.post(
            "/transactions/new",
            json={"sender": "a", "recipient": "b", "amount": 10},
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert "message" in resp.get_json()

    def test_new_transaction_with_data(self):
        resp = self.client.post(
            "/transactions/new",
            json={"sender": "a", "recipient": "b", "amount": 5, "data": "hello"},
            content_type="application/json",
        )
        assert resp.status_code == 201

    def test_new_transaction_missing_fields(self):
        resp = self.client.post(
            "/transactions/new",
            json={"sender": "a"},
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    # -- /mine --
    def test_mine_missing_api_key(self):
        resp = self.client.post(
            "/mine",
            json={"address": "abc"},
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_mine_missing_address(self):
        resp = self.client.post(
            "/mine",
            json={"api_key": "key"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    @patch.object(Blockchain, "verify_lean_proof", return_value=(True, True))
    @patch("blockchain.OpenAI")
    def test_mine_success(self, mock_openai_cls, mock_verify):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="rfl"))]
        )
        resp = self.client.post(
            "/mine",
            json={"api_key": "test-key", "address": "miner123"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "message" in data
        assert "block_index" in data

    @patch.object(Blockchain, "verify_lean_proof", return_value=(False, False))
    @patch("blockchain.OpenAI")
    def test_mine_failure(self, mock_openai_cls, mock_verify):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="bad"))]
        )
        resp = self.client.post(
            "/mine",
            json={"api_key": "test-key", "address": "miner123"},
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        assert "best_attempt" in data


# ── PROBLEM_DB ──────────────────────────────────────────────────────────────

class TestProblemDB:
    def test_problem_db_not_empty(self):
        assert len(PROBLEM_DB) >= 1

    def test_problem_db_entries_have_required_keys(self):
        for p in PROBLEM_DB:
            assert "id" in p
            assert "statement" in p

    def test_problem_db_ids_unique(self):
        ids = [p["id"] for p in PROBLEM_DB]
        assert len(ids) == len(set(ids))
