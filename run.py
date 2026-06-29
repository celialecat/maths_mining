import os
import sys

from flask import Flask

import config
from api.routes import bp
from mining.lean_verifier import is_lean_available, should_use_mock
from mining.llm_prover import LLMProver


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    )
    app.register_blueprint(bp)
    return app


def print_startup_info():
    print("=" * 50)
    print("  MathChain - Proof of Useful Work Blockchain")
    print("=" * 50)

    if is_lean_available():
        print("  Lean 4:  CONNECTED")
    else:
        print("  Lean 4:  NOT FOUND (using mock verifier)")

    if should_use_mock():
        print("  Mode:    MOCK (proofs accepted heuristically)")
    else:
        print("  Mode:    REAL (proofs verified by Lean compiler)")

    llm = LLMProver()
    if llm.is_available:
        print(f"  LLM:     CONNECTED ({config.OPENAI_MODEL})")
    else:
        print("  LLM:     FALLBACK (using hardcoded tactics)")

    print(f"  Server:  http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    print("=" * 50)


if __name__ == "__main__":
    print_startup_info()
    app = create_app()
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )
