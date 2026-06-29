import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass

import config

# Patterns that could allow arbitrary code execution in Lean
_UNSAFE_LEAN_PATTERNS = re.compile(
    r'#eval|#check|#reduce|IO\.|System\.|Environment\.|Lake\.|'
    r'native_decide|Lean\.Elab|import\s+(?!Mathlib)',
    re.IGNORECASE,
)


@dataclass
class VerificationResult:
    is_valid: bool
    is_complete: bool
    output: str = ""
    mock: bool = False


def is_lean_available() -> bool:
    return shutil.which(config.LEAN_BINARY) is not None


def should_use_mock() -> bool:
    mode = config.LEAN_MOCK_MODE.lower()
    if mode == "true":
        return True
    if mode == "false":
        return False
    return not is_lean_available()


def verify_lean_proof(theorem_statement: str, proof_code: str) -> VerificationResult:
    if should_use_mock():
        return _mock_verify(theorem_statement, proof_code)
    return _real_verify(theorem_statement, proof_code)


def _real_verify(theorem_statement: str, proof_code: str) -> VerificationResult:
    if _UNSAFE_LEAN_PATTERNS.search(proof_code):
        return VerificationResult(
            is_valid=False,
            is_complete=False,
            output="Proof rejected: contains unsafe Lean patterns",
        )

    lean_code = f"{theorem_statement} :=\n{proof_code}\n"
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".lean", delete=False, prefix="mathchain_"
        ) as f:
            f.write(lean_code)
            filepath = f.name

        result = subprocess.run(
            [config.LEAN_BINARY, filepath],
            capture_output=True,
            text=True,
            timeout=config.LEAN_TIMEOUT_SECONDS,
        )
        output = result.stdout + result.stderr

        if "error:" in output:
            return VerificationResult(
                is_valid=False, is_complete=False, output=output
            )
        if "warning: declaration uses 'sorry'" in output:
            return VerificationResult(
                is_valid=True, is_complete=False, output=output
            )
        return VerificationResult(is_valid=True, is_complete=True, output=output)

    except subprocess.TimeoutExpired:
        return VerificationResult(
            is_valid=False, is_complete=False, output="Lean verification timed out"
        )
    except FileNotFoundError:
        return VerificationResult(
            is_valid=False,
            is_complete=False,
            output=f"Lean binary not found: {config.LEAN_BINARY}",
        )
    except Exception as e:
        return VerificationResult(
            is_valid=False, is_complete=False, output=f"Verification error: {e}"
        )
    finally:
        if "filepath" in locals() and os.path.exists(filepath):
            os.remove(filepath)


def _mock_verify(theorem_statement: str, proof_code: str) -> VerificationResult:
    proof_lower = proof_code.strip().lower()

    if "sorry" in proof_lower:
        return VerificationResult(
            is_valid=True,
            is_complete=False,
            output="[Mock] Proof contains sorry",
            mock=True,
        )

    valid_tactics = {"rfl", "simp", "omega", "ring", "norm_num", "decide", "trivial"}
    lines = [
        line.strip()
        for line in proof_code.strip().splitlines()
        if line.strip() and line.strip() != "by"
    ]

    if not lines:
        return VerificationResult(
            is_valid=False,
            is_complete=False,
            output="[Mock] Empty proof",
            mock=True,
        )

    for line in lines:
        tokens = line.replace("by", "").strip().split()
        for token in tokens:
            base_tactic = token.split("[")[0].strip()
            if base_tactic in valid_tactics:
                return VerificationResult(
                    is_valid=True,
                    is_complete=True,
                    output=f"[Mock] Accepted tactic: {base_tactic}",
                    mock=True,
                )

    return VerificationResult(
        is_valid=True,
        is_complete=False,
        output=f"[Mock] Unknown tactics: {lines}",
        mock=True,
    )
