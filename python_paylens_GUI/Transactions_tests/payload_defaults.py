"""Resolve templates, earlier event values, and lazy generated defaults."""

import json
from collections.abc import Mapping
from copy import deepcopy


def read_payload(payload):
    if payload is None:
        return {}
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, Mapping):
        raise TypeError("Payloads must be dictionaries, JSON objects, or None")
    return deepcopy(dict(payload))


def fill_defaults(template, defaults):
    """Fill null/missing fields recursively, preserving zero, False and empty strings."""
    result = {}
    for key, default in defaults.items():
        value = template.get(key)
        if isinstance(default, dict) and (value is None or isinstance(value, Mapping)):
            result[key] = fill_defaults(value or {}, default)
        elif value is not None:
            result[key] = deepcopy(value)
        else:
            result[key] = default() if callable(default) else deepcopy(default)
    for key, value in template.items():
        if key not in result:
            result[key] = deepcopy(value)
    return result


class PayloadDefaults:
    def __init__(self, payload, previous_payloads):
        self.template = read_payload(payload)
        # Earlier events are passed in dispatch order: the latest wins.
        self.previous = [read_payload(item) for item in previous_payloads if item is not None]
        self.result = {}

    def previous_value(self, *keys):
        inherited = None
        for payload in reversed(self.previous):
            for key in keys:
                value = payload.get(key)
                if value is None:
                    continue
                if inherited is None:
                    if not isinstance(value, Mapping):
                        return deepcopy(value)
                    inherited = deepcopy(dict(value))
                elif isinstance(value, Mapping):
                    inherited = fill_defaults(inherited, value)
        return inherited

    def add(self, key, default=None, *, inherit=False, aliases=(), force_default=False):
        if force_default:
            value = default() if callable(default) else deepcopy(default)
        else:
            value = self.template.get(key)
            if value is None and inherit:
                value = self.previous_value(key, *aliases)
            if isinstance(default, dict) and (value is None or isinstance(value, Mapping)):
                value = fill_defaults(value or {}, default)
            elif value is None:
                value = default() if callable(default) else deepcopy(default)
        self.result[key] = deepcopy(value)
        return value

    def to_json(self):
        for key, value in self.template.items():
            if key not in self.result:
                self.result[key] = deepcopy(value)
        return json.dumps(self.result, indent=4)


def cached_payload(factory):
    """Generate a missing predecessor once, and only when needed."""
    cached = None

    def get(key):
        nonlocal cached
        if cached is None:
            cached = read_payload(factory())
        return cached.get(key)

    return get
