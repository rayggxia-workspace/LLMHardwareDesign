"""Exact lookup for executable TLM service models after hardware admission."""

from dataclasses import dataclass
from collections.abc import Callable


@dataclass(frozen=True)
class ModelBinding:
    """An installed provider and its implementation identity, including version."""

    provider: Callable
    identity: str

    def __post_init__(self):
        if not callable(self.provider):
            raise TypeError("TLM model provider must be callable")
        if not isinstance(self.identity, str) or not self.identity.strip():
            raise ValueError("TLM model identity must be a nonempty versioned name")


def model_for(models, key):
    """Find the model for (target, schema, ABI, opcode, completion), if installed."""
    if (not isinstance(key, tuple) or len(key) != 5
            or any(type(value) is not int or value < 0 for value in key[:4])
            or not isinstance(key[4], str) or not key[4].strip()):
        raise ValueError("expected a complete TLM service key")
    if key not in models:
        return None
    model = models[key]
    if not isinstance(model, ModelBinding):
        raise TypeError("TLM registry entry must be a ModelBinding")
    return model
