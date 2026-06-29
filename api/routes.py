from uuid import uuid4

from flask import Blueprint, jsonify, render_template

from api.validators import (
    get_json_body,
    require_fields,
    validate_address,
    validate_amount,
)
from blockchain.chain import Blockchain
from blockchain.transaction import Transaction
from mining.lean_verifier import is_lean_available, should_use_mock
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


@bp.route("/wallet/new", methods=["GET"])
def new_wallet():
    address = uuid4().hex
    return jsonify({"address": address}), 200


@bp.route("/mine", methods=["POST"])
def mine_block():
    body, err = get_json_body()
    if body is None:
        return jsonify({"error": err}), 400

    ok, err = require_fields(body, ["address"])
    if not ok:
        return jsonify({"error": err}), 400

    address = body["address"]
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
def new_transaction():
    body, err = get_json_body()
    if body is None:
        return jsonify({"error": err}), 400

    ok, err = require_fields(body, ["sender", "recipient", "amount"])
    if not ok:
        return jsonify({"error": err}), 400

    ok, err = validate_address(body["sender"])
    if not ok:
        return jsonify({"error": f"Sender: {err}"}), 400

    ok, err = validate_address(body["recipient"])
    if not ok:
        return jsonify({"error": f"Recipient: {err}"}), 400

    ok, err, amount = validate_amount(body["amount"])
    if not ok:
        return jsonify({"error": err}), 400

    tx = Transaction(
        sender=body["sender"],
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
    }), 200
