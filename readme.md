# MathChain : Blockchain avec Preuve de Travail Utile (MCTS + LLM + Lean 4)

Une blockchain expérimentale où le minage ne gaspille pas d'énergie dans des hachages inutiles. À la place, les mineurs utilisent des LLMs (via l'algorithme AlphaProof/MCTS) pour prouver des théorèmes mathématiques non résolus. La validité est vérifiée formellement par le compilateur Lean 4.

## Prérequis
1. **Python 3.8+**
2. **Lean 4** installé sur votre machine (la commande `lean` doit être accessible dans votre PATH). Voir [Lean Installation](https://leanprover.github.io/lean4/doc/setup.html).
3. **Une clé API OpenAI** (pour le minage LLM).

## Installation

1. Clonez ce dépôt :
   
```bash
   git clone [https://github.com/votre-nom/mathchain.git](https://github.com/votre-nom/mathchain.git)
   cd mathchain