"""Lean 4 proof verification utility.

Extracts the temp-file + subprocess pattern used to verify Lean proofs,
shared between the MCTS miner and the Blockchain validation layer.
"""

import os
import subprocess
from uuid import uuid4

from config import LEAN_IMPORT_HEADER, LEAN_TIMEOUT_SECONDS


def build_lean_source(theorem_statement, proof_code):
    """Construct a complete Lean 4 source file from a theorem and its proof."""
    return f"{LEAN_IMPORT_HEADER}\n\n{theorem_statement}\n{proof_code}\n"


def verify_lean_proof(theorem_statement, proof_code):
    """Verify a Lean 4 proof by compiling it with the Lean toolchain.

    Returns:
        (is_valid, is_complete): A tuple where is_valid indicates the proof
        has no errors, and is_complete indicates it is a full proof (no sorry).
    """
    lean_code = build_lean_source(theorem_statement, proof_code)
    filename = f"temp_proof_{uuid4().hex[:8]}.lean"
    try:
        with open(filename, "w") as f:
            f.write(lean_code)
        result = subprocess.run(
            ["lean", filename], capture_output=True, text=True, timeout=LEAN_TIMEOUT_SECONDS
        )
        output = result.stdout + result.stderr

        if "error:" in output:
            return False, False
        if "warning: declaration uses 'sorry'" in output:
            return True, False
        return True, True
    except Exception:
        return False, False
    finally:
        if os.path.exists(filename):
            os.remove(filename)
