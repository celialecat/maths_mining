# maths_mining
A small blockchain, but replacing the standard proof of work by solving a real world maths problem (MCTS + LLM + Lean 4)

Le minage se fait en résolvant des problèmes de maths, plus précisément en faisant des démonstrations assistées par Lean. Les mineurs utilisent des LLMs (via un algorithme prof de AlphaProof/MCTS) pour prouver des théorèmes mathématiques non résolus. La validité est vérifiée formellement par le compilateur Lean 4. Note : ce dépôt est 100% vibe codé pour l'instant

## Prérequis
1. **Python 3.8+**
2. **Lean 4** installé sur votre machine (la commande `lean` doit être accessible dans votre PATH). Voir [Lean Installation](https://leanprover.github.io/lean4/doc/setup.html).
3. **Une clé API OpenAI** (pour le minage LLM).

## Installation

1. Clonez ce dépôt :
   
```bash
   git clone [https://github.com/votre-nom/mathchain.git](https://github.com/votre-nom/mathchain.git)
   cd mathchain

