from mining.tactics import STRONG_TACTICS


def rule_based_heuristic(proof_state: str) -> float:
    score = 0.5
    lines = [l.strip() for l in proof_state.strip().splitlines() if l.strip()]
    depth = len(lines)

    if depth > 10:
        score -= 0.2
    elif depth <= 3:
        score += 0.1

    for line in lines:
        tokens = line.split()
        for token in tokens:
            if token in STRONG_TACTICS:
                score += 0.15

    if "sorry" in proof_state.lower():
        score -= 0.3

    weak_patterns = {"admit", "sorry", "undefined"}
    for pattern in weak_patterns:
        if pattern in proof_state.lower():
            score -= 0.1

    return max(0.0, min(1.0, score))
