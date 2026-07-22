from flask import jsonify


def error_response(code, message, status):
    return jsonify({"error_code": code, "error": message}), status


def message_response(code, message, status=200, **extra):
    payload = {"message_code": code, "message": message, **extra}
    return jsonify(payload), status


def validation_errors(items, status=400):
    # items: list[tuple[str, str]]
    return jsonify({"errors": [{"code": code, "message": message} for code, message in items]}), status
