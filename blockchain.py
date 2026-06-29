import hashlib
import json
import re
import subprocess
import os
import math
import random
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request, render_template
from openai import OpenAI

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
                model="gpt-3.5-turbo", # Rapide et économique pour les tests
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.7
            )
            content = response.choices[0].message.content
            return [line.strip() for line in content.split('\n') if line.strip()]
        except Exception as e:
            print(f"Erreur LLM : {e}")
            return ["rfl", "simp", "sorry"] # Fallback en cas d'erreur API
        
    def _evaluate_heuristic(self, proof_state):
        return random.random() # Pour l'MVP, valeur aléatoire. (À remplacer par un modèle de valeur).

    def mine(self, max_iterations=5):
        """Recherche MCTS. Restreint à 5 itérations pour l'interface web (éviter le timeout HTTP)."""
        root = MCTSNode(proof_state="by")
        
        for i in range(max_iterations):
            print(f"--- Itération MCTS {i+1}/{max_iterations} ---")
            node = root
            # 1. SÉLECTION
            while node.children and not node.is_terminal:
                node = max(node.children, key=lambda c: (c.value / (c.visits + 1e-6)) + 1.41 * math.sqrt(math.log(node.visits + 1) / (c.visits + 1e-6)))
            
            # 2. EXPANSION
            if not node.is_terminal:
                tactics = self._call_llm_for_tactics(node.proof_state)
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
                return node.proof_state # PREUVE TROUVÉE !
            else:
                reward = self._evaluate_heuristic(node.proof_state)

            # 4. RÉTROPROPAGATION
            curr = node
            while curr is not None:
                curr.visits += 1
                curr.value += reward
                curr = curr.parent

        return "by sorry" # Échec après X itérations

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

    # Patterns that could allow arbitrary code execution in Lean
    UNSAFE_LEAN_PATTERNS = re.compile(
        r'#eval|#check|#reduce|IO\.|System\.|Environment\.|Lake\.|'
        r'native_decide|Lean\.Elab|import\s+(?!Mathlib)',
        re.IGNORECASE,
    )

    @staticmethod
    def verify_lean_proof(theorem_statement, proof_code):
        if Blockchain.UNSAFE_LEAN_PATTERNS.search(proof_code):
            return False, False

        lean_code = f"import Mathlib\n\n{theorem_statement}\n{proof_code}\n"
        filename = f"temp_proof_{uuid4().hex[:8]}.lean"
        try:
            with open(filename, "w") as f:
                f.write(lean_code)
            result = subprocess.run(
                ["lean", filename],
                capture_output=True, text=True, timeout=10,
            )
            output = result.stdout + result.stderr
            
            if "error:" in output: return False, False
            if "warning: declaration uses 'sorry'" in output: return True, False
            return True, True
        except Exception:
            return False, False
        finally:
            if os.path.exists(filename):
                os.remove(filename)

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
    values = request.get_json()
    api_key = values.get('api_key')
    miner_address = values.get('address')

    if not api_key or not miner_address:
        return jsonify({'error': 'API key et Adresse du mineur requises'}), 400

    last_block = blockchain.last_block
    last_hash = blockchain.hash(last_block)
    problem = blockchain.get_problem_for_next_block(last_hash)
    
    miner = AlphaProofMiner(problem['statement'], api_key)
    proof_code = miner.mine(max_iterations=4) # Limité pour éviter le timeout web
    
    # Vérifie si le minage a réussi (sans "sorry")
    is_valid, is_complete = Blockchain.verify_lean_proof(problem['statement'], proof_code)
    
    if is_complete:
        # Récompense
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
    values = request.get_json()
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return jsonify({'error': 'Valeurs manquantes'}), 400

    try:
        amount = float(values['amount'])
    except (TypeError, ValueError):
        return jsonify({'error': 'Le montant doit être un nombre'}), 400

    if amount <= 0:
        return jsonify({'error': 'Le montant doit être positif'}), 400

    sender = str(values['sender']).strip()
    recipient = str(values['recipient']).strip()
    if not sender or not recipient:
        return jsonify({'error': 'Expéditeur et destinataire requis'}), 400

    index = blockchain.new_transaction(
        sender,
        recipient,
        amount,
        str(values.get('data', '')),
    )
    return jsonify({'message': f'Transaction en attente pour le bloc {index}'}), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    return jsonify({
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
        'pending_transactions': blockchain.current_transactions
    }), 200

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', '5000'))
    print(f"Démarrage du nœud MathChain sur http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)