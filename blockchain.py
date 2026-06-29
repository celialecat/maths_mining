import hashlib
import json
import logging
import subprocess
import os
import math
import random
from time import time
from uuid import uuid4

from flask import Flask, jsonify, request, render_template
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- BASE DE DONNÉES DE PROBLÈMES ---
# Pour l'MVP, on utilise des théorèmes simples pour que le minage ne prenne pas des heures.
PROBLEM_DB = [
    {"id": 0, "statement": "theorem add_zero_custom (n : Nat) : n + 0 = n :="},
    {"id": 1, "statement": "theorem eq_self (a : Nat) : a = a :="},
]

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
        """Appel RÉEL à OpenAI pour générer des tactiques Lean 4."""
        prompt = f"""
        Tu es un expert en Lean 4. Voici le théorème à prouver :
        {self.theorem_statement}
        
        Voici l'état actuel de la preuve :
        {current_proof}
        
        Génère 3 tactiques Lean 4 possibles pour continuer la preuve. 
        Ne fournis que les tactiques, une par ligne, sans aucune explication.
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.7
            )
            content = response.choices[0].message.content
            if not content:
                logger.warning("LLM returned empty content, using fallback tactics")
                return ["rfl", "simp", "sorry"]
            tactics = [line.strip() for line in content.split('\n') if line.strip()]
            if not tactics:
                logger.warning("LLM response parsed to zero tactics, using fallback")
                return ["rfl", "simp", "sorry"]
            return tactics
        except Exception as e:
            logger.error("LLM API call failed: %s", e, exc_info=True)
            raise RuntimeError(f"LLM API error: {e}") from e
        
    def _evaluate_heuristic(self, proof_state):
        return random.random() # Pour l'MVP, valeur aléatoire. (À remplacer par un modèle de valeur).

    def mine(self, max_iterations=5):
        """Recherche MCTS. Restreint à 5 itérations pour l'interface web (éviter le timeout HTTP)."""
        root = MCTSNode(proof_state="by")
        llm_failures = 0

        for i in range(max_iterations):
            logger.info("--- Itération MCTS %d/%d ---", i + 1, max_iterations)
            node = root
            # 1. SÉLECTION
            while node.children and not node.is_terminal:
                node = max(node.children, key=lambda c: (c.value / (c.visits + 1e-6)) + 1.41 * math.sqrt(math.log(node.visits + 1) / (c.visits + 1e-6)))

            # 2. EXPANSION
            if not node.is_terminal:
                try:
                    tactics = self._call_llm_for_tactics(node.proof_state)
                except RuntimeError:
                    llm_failures += 1
                    if llm_failures >= max_iterations:
                        raise RuntimeError(
                            "LLM API failed on all iterations; cannot mine"
                        )
                    continue
                for tactic in tactics:
                    new_state = f"{node.proof_state}\n  {tactic}"
                    child = MCTSNode(proof_state=new_state, parent=node)
                    node.children.append(child)
                node = random.choice(node.children) if node.children else node

            # 3. SIMULATION / VÉRIFICATION LEAN
            is_valid, is_complete = Blockchain.verify_lean_proof(self.theorem_statement, node.proof_state)

            if not is_valid:
                node.is_terminal = True
                reward = -1.0
            elif is_complete:
                node.is_terminal = True
                node.is_solved = True
                return node.proof_state
            else:
                reward = self._evaluate_heuristic(node.proof_state)

            # 4. RÉTROPROPAGATION
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
        self.new_block(proof="by rfl", previous_hash='1')

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
            'data': data
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

    @staticmethod
    def verify_lean_proof(theorem_statement, proof_code):
        lean_code = f"import Mathlib\n\n{theorem_statement}\n{proof_code}\n"
        filename = f"temp_proof_{uuid4().hex[:8]}.lean"
        try:
            with open(filename, "w") as f:
                f.write(lean_code)
        except OSError as e:
            logger.error("Failed to write temp Lean file %s: %s", filename, e)
            raise RuntimeError(f"Cannot write proof file: {e}") from e

        try:
            result = subprocess.run(
                ["lean", filename], capture_output=True, text=True, timeout=30
            )
        except FileNotFoundError:
            logger.error("Lean compiler not found in PATH")
            raise RuntimeError(
                "Lean 4 is not installed or not in PATH"
            )
        except subprocess.TimeoutExpired:
            logger.warning("Lean verification timed out for proof: %s", proof_code[:80])
            return False, False
        finally:
            try:
                os.remove(filename)
            except OSError:
                pass

        output = result.stdout + result.stderr
        if "error:" in output:
            return False, False
        if "warning: declaration uses 'sorry'" in output:
            return True, False
        return True, True

# --- FLASK APP ---
app = Flask(__name__, template_folder='templates')
blockchain = Blockchain()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/wallet/new', methods=['GET'])
def new_wallet():
    # Pour l'MVP, on génère un simple UUID en guise de clé publique
    address = str(uuid4()).replace('-', '')
    return jsonify({'address': address}), 200

@app.route('/mine', methods=['POST'])
def mine():
    values = request.get_json(silent=True)
    if values is None:
        return jsonify({'error': 'Corps de requête JSON invalide'}), 400

    api_key = values.get('api_key')
    miner_address = values.get('address')

    if not api_key or not miner_address:
        return jsonify({'error': 'API key et Adresse du mineur requises'}), 400

    last_block = blockchain.last_block
    last_hash = blockchain.hash(last_block)
    problem = blockchain.get_problem_for_next_block(last_hash)

    try:
        miner = AlphaProofMiner(problem['statement'], api_key)
        proof_code = miner.mine(max_iterations=4)
    except RuntimeError as e:
        logger.error("Mining failed due to infrastructure error: %s", e)
        return jsonify({'error': f'Erreur d\'infrastructure: {e}'}), 503
    except Exception:
        logger.exception("Unexpected error during mining")
        return jsonify({'error': 'Erreur interne du serveur pendant le minage'}), 500

    try:
        is_valid, is_complete = Blockchain.verify_lean_proof(problem['statement'], proof_code)
    except RuntimeError as e:
        logger.error("Lean verification infrastructure error: %s", e)
        return jsonify({'error': f'Erreur de vérification: {e}'}), 503

    if is_complete:
        blockchain.new_transaction(sender="0", recipient=miner_address, amount=1, data="Block Reward")
        block = blockchain.new_block(proof_code, last_hash)
        return jsonify({
            'message': "Bloc forgé avec succès !",
            'theorem': problem['statement'],
            'proof': block['proof'],
            'block_index': block['index']
        }), 200
    else:
        return jsonify({
            'error': "Le LLM n'a pas réussi à trouver la preuve à temps.",
            'best_attempt': proof_code
        }), 400

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json(silent=True)
    if values is None:
        return jsonify({'error': 'Corps de requête JSON invalide'}), 400

    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return jsonify({'error': 'Valeurs manquantes'}), 400

    try:
        amount = float(values['amount'])
    except (TypeError, ValueError):
        return jsonify({'error': 'Le montant doit être un nombre valide'}), 400
    if amount <= 0:
        return jsonify({'error': 'Le montant doit être positif'}), 400

    index = blockchain.new_transaction(
        values['sender'],
        values['recipient'],
        amount,
        values.get('data', '')
    )
    return jsonify({'message': f'Transaction en attente pour le bloc {index}'}), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    return jsonify({
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
        'pending_transactions': blockchain.current_transactions
    }), 200

@app.errorhandler(500)
def internal_error(error):
    logger.exception("Unhandled server error: %s", error)
    return jsonify({'error': 'Erreur interne du serveur'}), 500


if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    logger.info("Démarrage du nœud MathChain sur http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)