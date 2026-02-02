# proofsync_app.py – ProofSync: Blockchain of Verifiable Work & Achievements

from flask import Flask, jsonify, request, render_template_string
import hashlib
import json
import time
import os
from uuid import uuid4

CHAIN_FILE = 'proofsync_chain.json'
app = Flask(__name__)

class Block:
    def __init__(self, index, timestamp, proof_id, user_id, task_type, description, evidence_link, validator_note, score, previous_hash, nonce=0):
        self.index = index
        self.timestamp = timestamp
        self.proof_id = proof_id
        self.user_id = user_id
        self.task_type = task_type
        self.description = description
        self.evidence_link = evidence_link
        self.validator_note = validator_note
        self.score = score
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.compute_hash()

    def compute_hash(self):
        return hashlib.sha256(json.dumps(self.__dict__, sort_keys=True).encode()).hexdigest()

class ProofSync:
    difficulty = 3

    def __init__(self):
        self.queue = []
        self.chain = self.load_chain()

    def create_genesis_block(self):
        return [Block(0, time.time(), "GENESIS", "SYSTEM", "init", "Genesis Block", "N/A", "System Init", 10, "0")]

    def last_block(self):
        return self.chain[-1]

    def submit_proof(self, user_id, task_type, description, evidence_link, validator_note, score):
        proof_id = str(uuid4())
        self.queue.append({
            'proof_id': proof_id,
            'user_id': user_id,
            'task_type': task_type,
            'description': description,
            'evidence_link': evidence_link,
            'validator_note': validator_note,
            'score': score
        })
        return proof_id

    def proof_of_work(self, block):
        block.nonce = 0
        hashed = block.compute_hash()
        while not hashed.startswith('0' * ProofSync.difficulty):
            block.nonce += 1
            hashed = block.compute_hash()
        return hashed

    def add_block(self, block, proof):
        if self.last_block().hash != block.previous_hash:
            return False
        if not proof.startswith('0' * ProofSync.difficulty):
            return False
        if proof != block.compute_hash():
            return False
        self.chain.append(block)
        self.save_chain()
        return True

    def mine_proof(self):
        if not self.queue:
            return False
        data = self.queue.pop(0)
        block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            proof_id=data['proof_id'],
            user_id=data['user_id'],
            task_type=data['task_type'],
            description=data['description'],
            evidence_link=data['evidence_link'],
            validator_note=data['validator_note'],
            score=data['score'],
            previous_hash=self.last_block().hash
        )
        proof = self.proof_of_work(block)
        if self.add_block(block, proof):
            return block.index
        return False

    def save_chain(self):
        with open(CHAIN_FILE, 'w') as f:
            json.dump([b.__dict__ for b in self.chain], f, indent=4)

    def load_chain(self):
        if not os.path.exists(CHAIN_FILE):
            return self.create_genesis_block()
        with open(CHAIN_FILE, 'r') as f:
            return [Block(**b) for b in json.load(f)]

sync = ProofSync()

@app.route('/')
def home():
    html = """
    <html><head><title>ProofSync Explorer</title><style>
    body { font-family: sans-serif; background: #f8f9fa; padding: 20px; }
    .block { background: #fff; border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 6px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    </style></head><body>
    <h1>📜 ProofSync Blockchain</h1>
    {% for block in chain %}
    <div class="block">
        <h3>Block #{{ block.index }} – {{ block.task_type }}</h3>
        <p><b>User:</b> {{ block.user_id }}</p>
        <p><b>Description:</b> {{ block.description }}</p>
        <p><b>Evidence:</b> <a href="{{ block.evidence_link }}" target="_blank">View</a></p>
        <p><b>Note:</b> {{ block.validator_note }}</p>
        <p><b>Score:</b> {{ block.score }}</p>
        <p><b>Hash:</b> {{ block.hash }}</p>
        <p><b>Previous:</b> {{ block.previous_hash }}</p>
    </div>
    {% endfor %}
    </body></html>
    """
    return render_template_string(html, chain=sync.chain)

@app.route('/submit', methods=['POST'])
def submit():
    data = request.json
    required = ('user_id', 'task_type', 'description', 'evidence_link', 'validator_note', 'score')
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing fields'}), 400
    pid = sync.submit_proof(
        data['user_id'], data['task_type'], data['description'],
        data['evidence_link'], data['validator_note'], data['score']
    )
    return jsonify({'message': 'Proof submitted', 'proof_id': pid})

@app.route('/mine')
def mine():
    index = sync.mine_proof()
    return jsonify({'message': f'Block #{index} mined' if index is not False else 'No proofs to mine'})

@app.route('/chain')
def chain_data():
    return jsonify([b.__dict__ for b in sync.chain])

app = app  # For Vercel
