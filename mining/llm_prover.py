import logging

import config

logger = logging.getLogger(__name__)

FALLBACK_TACTICS = [
    "rfl",
    "simp",
    "omega",
    "ring",
    "norm_num",
    "decide",
    "trivial",
    "simp [Nat.add_comm]",
    "simp [Nat.mul_comm]",
    "simp [Nat.add_assoc]",
]


class LLMProver:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None and config.OPENAI_API_KEY:
            from openai import OpenAI
            self._client = OpenAI(api_key=config.OPENAI_API_KEY)
        return self._client

    @property
    def is_available(self) -> bool:
        return bool(config.OPENAI_API_KEY)

    def suggest_tactics(
        self, theorem_statement: str, current_proof: str, n: int = 3
    ) -> list[str]:
        if not self.is_available:
            return self._fallback_tactics(n)
        return self._llm_tactics(theorem_statement, current_proof, n)

    def _llm_tactics(
        self, theorem_statement: str, current_proof: str, n: int
    ) -> list[str]:
        prompt = (
            f"You are a Lean 4 expert. Prove this theorem:\n"
            f"{theorem_statement}\n\n"
            f"Current proof state:\n{current_proof}\n\n"
            f"Suggest {n} Lean 4 tactics to continue the proof. "
            f"Output ONLY the tactics, one per line, no explanation."
        )
        try:
            client = self._get_client()
            if client is None:
                logger.warning("OpenAI client unavailable, using fallback tactics")
                return self._fallback_tactics(n)
            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.7,
            )
            content = response.choices[0].message.content or ""
            tactics = [
                line.strip()
                for line in content.splitlines()
                if line.strip() and not line.strip().startswith("--")
            ]
            if not tactics:
                logger.warning("LLM returned no usable tactics, using fallback")
                return self._fallback_tactics(n)
            return tactics[:n]
        except Exception as e:
            logger.error("LLM API call failed: %s", e, exc_info=True)
            raise RuntimeError(f"LLM API error: {e}") from e

    def _fallback_tactics(self, n: int) -> list[str]:
        import random
        return random.sample(FALLBACK_TACTICS, min(n, len(FALLBACK_TACTICS)))
