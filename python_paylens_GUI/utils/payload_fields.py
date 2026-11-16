"""Read and update nested JSON fields using dotted paths."""


def get_path(payload, path):
    value = payload
    for key in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def set_path(payload, path, value):
    keys = path.split(".")
    for key in keys[:-1]:
        if not isinstance(payload.get(key), dict):
            payload[key] = {}
        payload = payload[key]
    payload[keys[-1]] = value
