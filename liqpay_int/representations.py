from flask_restx import representations


def output_json(data, code, headers=None):
    if code >= 500:
        data["status"] = "failure"
    elif code >= 400:
        data["status"] = "error"
    return representations.output_json(data, code, headers=headers)
