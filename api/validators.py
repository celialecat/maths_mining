from flask import request


def get_json_body() -> tuple[dict | None, str]:
    body = request.get_json(silent=True)
    if body is None:
        return None, "Request body must be valid JSON"
    if not isinstance(body, dict):
        return None, "Request body must be a JSON object"
    return body, ""


def require_fields(body: dict, fields: list[str]) -> tuple[bool, str]:
    missing = [f for f in fields if f not in body or body[f] is None]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    return True, ""


def validate_amount(value) -> tuple[bool, str, float]:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return False, "Amount must be a number", 0.0
    if amount <= 0:
        return False, "Amount must be positive", 0.0
    return True, "", amount


def validate_address(value) -> tuple[bool, str]:
    if not value or not isinstance(value, str):
        return False, "Address must be a non-empty string"
    if len(value) < 8:
        return False, "Address too short"
    return True, ""
