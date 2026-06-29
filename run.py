import logging
import os

from flask import Flask, jsonify

import config
from api.routes import bp
from mining.lean_verifier import is_lean_available, should_use_mock
from mining.llm_prover import LLMProver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    )
    app.register_blueprint(bp)

    @app.errorhandler(500)
    def internal_error(error):
        logger.exception("Unhandled server error: %s", error)
        return jsonify({"error": "Internal server error"}), 500

    return app


def print_startup_info():
    logger.info("=" * 50)
    logger.info("  MathChain - Proof of Useful Work Blockchain")
    logger.info("=" * 50)

    if is_lean_available():
        logger.info("  Lean 4:  CONNECTED")
    else:
        logger.info("  Lean 4:  NOT FOUND (using mock verifier)")

    if should_use_mock():
        logger.info("  Mode:    MOCK (proofs accepted heuristically)")
    else:
        logger.info("  Mode:    REAL (proofs verified by Lean compiler)")

    llm = LLMProver()
    if llm.is_available:
        logger.info("  LLM:     CONNECTED (%s)", config.OPENAI_MODEL)
    else:
        logger.info("  LLM:     FALLBACK (using hardcoded tactics)")

    logger.info("  Server:  http://%s:%s", config.FLASK_HOST, config.FLASK_PORT)
    logger.info("=" * 50)


if __name__ == "__main__":
    print_startup_info()
    app = create_app()
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )
