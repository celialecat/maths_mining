import hashlib
import json
import os
import random
from time import time
from uuid import uuid4

import requests
from flask import Flask, jsonify, request, render_template
from openai import OpenAI

from config import (
    GENESIS_PREVIOUS_HASH,
    GENESIS_PROOF,
    LLM_FALLBACK_TACTICS,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_TEMPERATURE,
    MCTS_DEFAULT_MAX_ITERATIONS,
    MCTS_WEB_MAX_ITERATIONS,
    MINING_REWARD_AMOUNT,
    PROBLEM_DB,
)
from utils.lean_verifier import verify_lean_proof
from utils.mcts_utils import ucb1_score
from utils.validation import validate_json_fields


# --- ALGORITHME MCTS + LLM (Le Mineur) ---
class MCTSNode:
    def __init__(self, proof_state, parent=None):
        self.proof_state = proof_state
        self.parent = parent
        self.children = []
        self.visits = 0
        self.value = 0.0
        self.is_terminal = False
        self.is_solved = False


class AlphaProofMiner:
    def __init__(self, theorem_statement, api_key):
        self.theorem_statement = theorem_statement
        self.client = OpenAI(api_key=api_key)

    def _call_llm_for_tactics(self, current_proof):
        """Appel a OpenAI pour generer des tactiques Lean 4."""
        prompt = f"""
        Tu es un expert en Lean 4. Voici le theoreme a prouver :
        {self.theorem_statement}
        
        Voici l'etat actuel de la preuve :
        {current_proof}
        
        Genere 3 tactiques Lean 4 possibles pour continuer la preuve. 
        Ne fournis que les tactiques, une par ligne, sans aucune explication.
        """
        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=LLM_MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
            )
            content = response.choices[0].message.content
            return [line.strip() for line in content.split('\n') if line.strip()]
        except Exception as e:
            print(f"Erreur LLM : {e}")
            return LLM_FALLBACK_TACTICS

    def _evaluate_heuristic(self, proof_state):
        return random.random()

    def mine(self, max_iterations=MCTS_DEFAULT_MAX_ITERATIONS):
        """Recherche MCTS. Restreint pour l'interface web (eviter le timeout HTTP)."""
        root = MCTSNode(proof_state="by")

        for i in range(max_iterations):
            print(f"--- Iteration MCTS {i+1}/{max_iterations} ---")
            node = root
            # 1. SELECTION (UCB1)
            while node.children and not node.is_terminal:
                node = max(
                    node.children,
                    key=lambda c: ucb1_score(c.value, c.visits, node.visits),
                )

            # 2. EXPANSION
            if not node.is_terminal:
                tactics = self._call_llm_for_tactics(node.proof_state)
                for tactic in tactics:
                    new_state = f"{node.proof_state}\n  {tactic}"
                    child = MCTSNode(proof_state=new_state, parent=node)
                    node.children.append(child)
                node = random.choice(node.children) if node.children else node

            # 3. SIMULATION / VERIFICATION LEAN
            is_valid, is_complete = verify_lean_proof(self.theorem_statement, node.proof_state)

            if not is_valid:
                node.is_terminal = True
                reward = -1.0
            elif is_complete:
                node.is_terminal = True
                node.is_solved = True
                return node.proof_state
            else:
                reward = self._evaluate_heuristic(node.proof_state)

            # 4. RETROPROPAGATION
            curr = node
            while curr is not None:
                curr.visits += 1
                curr.value += reward
                curr = curr.parent

        return "by sorry"


# --- BLOCKCHAIN ---
class Blockchain:
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()
        self.new_block(proof=GENESIS_PROOF, previous_hash=GENESIS_PREVIOUS_HASH)

    def new_block(self, proof, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }
        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount, data=""):
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'data': data,
        })
        return self.last_block['index'] + 1

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def get_problem_for_next_block(self, last_hash):
        seed = int(last_hash, 16)
        return PROBLEM_DB[seed % len(PROBLEM_DB)]


# --- FLASK APP ---
app = Flask(__name__, template_folder='templates')
blockchain = Blockchain()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/wallet/new', methods=['GET'])
def new_wallet():
    address = str(uuid4()).replace('-', '')
    return jsonify({'address': address}), 200


@app.route('/mine', methods=['POST'])
def mine():
    values, error = validate_json_fields(['api_key', 'address'])
    if error:
        return error

    last_block = blockchain.last_block
    last_hash = blockchain.hash(last_block)
    problem = blockchain.get_problem_for_next_block(last_hash)

    miner = AlphaProofMiner(problem['statement'], values['api_key'])
    proof_code = miner.mine(max_iterations=MCTS_WEB_MAX_ITERATIONS)

    is_valid, is_complete = verify_lean_proof(problem['statement'], proof_code)

    if is_complete:
        blockchain.new_transaction(
            sender="0",
            recipient=values['address'],
            amount=MINING_REWARD_AMOUNT,
            data="Block Reward",
        )
        block = blockchain.new_block(proof_code, last_hash)
        return jsonify({
            'message': "Bloc forge avec succes !",
            'theorem': problem['statement'],
            'proof': block['proof'],
            'block_index': block['index'],
        }), 200
    else:
        return jsonify({
            'error': "Le LLM n'a pas reussi a trouver la preuve a temps.",
            'best_attempt': proof_code,
        }), 400


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values, error = validate_json_fields(['sender', 'recipient', 'amount'])
    if error:
        return error

    index = blockchain.new_transaction(
        values['sender'],
        values['recipient'],
        values['amount'],
        values.get('data', ''),
    )
    return jsonify({'message': f'Transaction en attente pour le bloc {index}'}), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    return jsonify({
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
        'pending_transactions': blockchain.current_transactions,
    }), 200


if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    print("Demarrage du noeud MathChain sur http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
