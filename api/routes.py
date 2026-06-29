from uuid import uuid4

from flask import Blueprint, jsonify, render_template, request

from api.auth import (
    assign_wallet,
    get_current_user,
    get_user_wallet,
    login_required,
    login_user,
    register_user,
)
from api.validators import (
    get_json_body,
    require_fields,
    validate_address,
    validate_amount,
)
from blockchain.chain import Blockchain
from blockchain.transaction import Transaction
from mining.lean_verifier import (
    is_lean_available,
    should_use_mock,
    verify_lean_proof,
)
from mining.llm_prover import LLMProver
from mining.miner import AlphaProofMiner
from problems.problem_db import ProblemDB

bp = Blueprint("api", __name__)

blockchain = Blockchain()
problem_db = ProblemDB()
miner = AlphaProofMiner()
llm = LLMProver()


@bp.route("/")
def index():
    return render_template("index.html")


# --- Auth ---

@bp.route("/auth/register", methods=["POST"])
def auth_register():
    body, err = get_json_body()
    if body is None:
        return jsonify({"error": err}), 400

    ok, err = require_fields(body, ["username", "password"])
    if not ok:
        return jsonify({"error": err}), 400

    result, err = register_user(body["username"].strip(), body["password"])
    if result is None:
        return jsonify({"error": err}), 400
    return jsonify(result), 201


@bp.route("/auth/login", methods=["POST"])
def auth_login():
    body, err = get_json_body()
    if body is None:
        return jsonify({"error": err}), 400

    ok, err = require_fields(body, ["username", "password"])
    if not ok:
        return jsonify({"error": err}), 400

    result, err = login_user(body["username"].strip(), body["password"])
    if result is None:
        return jsonify({"error": err}), 401
    return jsonify(result), 200


@bp.route("/auth/me", methods=["GET"])
def auth_me():
    user = get_current_user()
    if user is None:
        return jsonify({"logged_in": False}), 200
    return jsonify({"logged_in": True, **user}), 200


# --- Wallet ---

@bp.route("/wallet/new", methods=["GET"])
@login_required
def new_wallet():
    user = request.current_user
    existing = get_user_wallet(user["username"])
    if existing:
        return jsonify({"address": existing, "message": "Wallet already exists"}), 200
    address = uuid4().hex
    assign_wallet(user["username"], address)
    return jsonify({"address": address}), 200


# --- Mining ---

@bp.route("/mine", methods=["POST"])
@login_required
def mine_block():
    user = request.current_user
    address = get_user_wallet(user["username"])
    if not address:
        return jsonify({"error": "Create a wallet first"}), 400

    ok, err = validate_address(address)
    if not ok:
        return jsonify({"error": err}), 400

    last_block = blockchain.last_block
    last_hash = last_block.compute_hash()
    problem = problem_db.get_problem_for_block(last_hash)

    result = miner.mine(
        theorem_statement=problem["statement"],
        problem_id=problem["id"],
    )

    if result.success:
        blockchain.add_reward_transaction(address)
        block = blockchain.create_block(
            proof=result.proof,
            problem_id=problem["id"],
        )
        return jsonify({
            "message": "Block mined successfully!",
            "theorem": problem["statement"],
            "theorem_title": problem.get("title", ""),
            "proof": result.proof,
            "block_index": block.index,
            "iterations": result.iterations_used,
            "logs": result.logs,
            "mock_mode": result.mock_mode,
        }), 200
    else:
        return jsonify({
            "error": "Mining failed: no complete proof found in time.",
            "best_attempt": result.proof,
            "theorem": problem["statement"],
            "theorem_title": problem.get("title", ""),
            "iterations": result.iterations_used,
            "logs": result.logs,
            "mock_mode": result.mock_mode,
        }), 400


@bp.route("/transactions/new", methods=["POST"])
@login_required
def new_transaction():
    user = request.current_user
    body, err = get_json_body()
    if body is None:
        return jsonify({"error": err}), 400

    ok, err = require_fields(body, ["recipient", "amount"])
    if not ok:
        return jsonify({"error": err}), 400

    sender = get_user_wallet(user["username"])
    if not sender:
        return jsonify({"error": "Create a wallet first"}), 400

    ok, err = validate_address(sender)
    if not ok:
        return jsonify({"error": f"Sender: {err}"}), 400

    ok, err = validate_address(body["recipient"])
    if not ok:
        return jsonify({"error": f"Recipient: {err}"}), 400

    ok, err, amount = validate_amount(body["amount"])
    if not ok:
        return jsonify({"error": err}), 400

    tx = Transaction(
        sender=sender,
        recipient=body["recipient"],
        amount=amount,
        data=body.get("data", ""),
    )

    try:
        block_index = blockchain.add_transaction(tx)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "message": f"Transaction pending for block {block_index}",
    }), 201


@bp.route("/chain", methods=["GET"])
def full_chain():
    return jsonify(blockchain.get_chain_data()), 200


@bp.route("/problems", methods=["GET"])
def list_problems():
    return jsonify({
        "problems": problem_db.list_problems(),
        "count": problem_db.count,
    }), 200


@bp.route("/status", methods=["GET"])
def status():
    return jsonify({
        "chain_length": blockchain.length,
        "pending_transactions": len(blockchain.pending_transactions),
        "lean_available": is_lean_available(),
        "mock_mode": should_use_mock(),
        "llm_available": llm.is_available,
        "problems_count": problem_db.count,
        "solved_problems": list(blockchain.get_solved_problem_ids()),
    }), 200


@bp.route("/problems/current", methods=["GET"])
def current_problem():
    last_hash = blockchain.last_block.compute_hash()
    problem = problem_db.get_problem_for_block(last_hash)
    solved = blockchain.get_solved_problem_ids()
    return jsonify({
        "problem": problem,
        "block_index": blockchain.length,
        "already_solved_globally": problem["id"] in solved,
    }), 200


@bp.route("/solutions/submit", methods=["POST"])
@login_required
def submit_solution():
    user = request.current_user
    body, err = get_json_body()
    if body is None:
        return jsonify({"error": err}), 400

    ok, err = require_fields(body, ["proof"])
    if not ok:
        return jsonify({"error": err}), 400

    address = get_user_wallet(user["username"])
    if not address:
        return jsonify({"error": "Create a wallet first"}), 400

    proof_code = body["proof"].strip()
    if not proof_code:
        return jsonify({"error": "Proof cannot be empty"}), 400

    last_hash = blockchain.last_block.compute_hash()
    problem = problem_db.get_problem_for_block(last_hash)

    result = verify_lean_proof(problem["statement"], proof_code)

    if not result.is_complete:
        reason = result.output if result.output else "Proof did not verify"
        return jsonify({
            "error": "Proof rejected",
            "reason": reason,
            "is_valid": result.is_valid,
            "is_complete": result.is_complete,
            "theorem": problem["statement"],
            "mock_mode": result.mock,
        }), 400

    blockchain.add_reward_transaction(address)
    block = blockchain.create_block(
        proof=proof_code,
        problem_id=problem["id"],
    )
    return jsonify({
        "message": "Solution accepted! Block mined.",
        "theorem": problem["statement"],
        "theorem_title": problem.get("title", ""),
        "proof": proof_code,
        "block_index": block.index,
        "problem_id": problem["id"],
        "mock_mode": result.mock,
    }), 200


@bp.route("/config/api-key", methods=["POST"])
def set_api_key():
    body, err = get_json_body()
    if body is None:
        return jsonify({"error": err}), 400

    ok, err = require_fields(body, ["api_key"])
    if not ok:
        return jsonify({"error": err}), 400

    api_key = body["api_key"].strip()
    if not api_key:
        return jsonify({"error": "API key cannot be empty"}), 400

    llm.set_api_key(api_key)
    miner.llm.set_api_key(api_key)

    return jsonify({
        "message": "API key configured successfully",
        "llm_available": llm.is_available,
    }), 200


@bp.route("/config/api-key", methods=["DELETE"])
def clear_api_key():
    llm.set_api_key("")
    miner.llm.set_api_key("")

    return jsonify({
        "message": "API key cleared",
        "llm_available": llm.is_available,
    }), 200


@bp.route("/validate", methods=["GET"])
def validate_chain():
    is_valid, error = blockchain.validate_chain(problem_db)
    return jsonify({
        "valid": is_valid,
        "error": error if error else None,
        "chain_length": blockchain.length,
        "blocks_checked": blockchain.length - 1,
    }), 200 if is_valid else 400
