from flask import jsonify


def success(data=None, meta=None, status=200):
    payload = {"success": True, "data": data if data is not None else {}}
    if meta is not None:
        payload["meta"] = meta
    return jsonify(payload), status


def error(code, message, status=400, details=None):
    err = {"code": code, "message": message}
    if details is not None:
        err["details"] = details
    return jsonify({"success": False, "error": err}), status
