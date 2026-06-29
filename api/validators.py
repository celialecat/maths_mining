from flask import jsonify, request


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


def error_response(error_msg: str, status_code: int = 400):
    """Build a JSON error response tuple ready to return from a Flask route."""
    return jsonify({"error": error_msg}), status_code


def validate_request(body: dict, validators: list) -> tuple[bool, None] | tuple[bool, tuple]:
    """Run a chain of validators on the request body.

    Each validator is a callable returning (ok, err, *extra). On the first
    failure, returns (False, error_response_tuple). On success returns
    (True, None).

    Args:
        body: The parsed JSON body.
        validators: List of callables, each returning (ok: bool, err: str, ...).
    """
    for validator in validators:
        result = validator(body)
        ok, err = result[0], result[1]
        if not ok:
            return False, error_response(err)
    return True, None
