"""Request validation utilities.

Extracts the repeated pattern of extracting JSON fields from Flask
requests and returning 400 errors for missing required fields.
"""

from flask import jsonify, request


def validate_json_fields(required_fields):
    """Extract and validate required fields from a JSON request body.

    Args:
        required_fields: List of field names that must be present and truthy.

    Returns:
        (values, error_response): If validation passes, error_response is None.
        If it fails, error_response is a (response, status_code) tuple ready
        to be returned from a Flask route.
    """
    values = request.get_json()
    if values is None:
        return None, (jsonify({"error": "Corps JSON requis"}), 400)

    missing = [f for f in required_fields if not values.get(f)]
    if missing:
        return values, (
            jsonify({"error": f"Champs requis manquants : {', '.join(missing)}"}),
            400,
        )

    return values, None
