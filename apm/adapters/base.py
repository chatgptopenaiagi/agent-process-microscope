"""Small polling contract; returned payloads require the central Normalizer."""
from abc import ABC, abstractmethod
from typing import Any


class ObserverAdapter(ABC):
    name = "observer"

    @abstractmethod
    def poll(self) -> list[dict[str, Any]]:
        """Return scoped evidence, never Event instances or private content."""

    def close(self) -> None:
        """Stop observation. Attached processes are never terminated."""
        self._closed = True


def payload(source: str, category: str, action: str, target: str,
            metadata: dict[str, Any], *, status: str = "observed") -> dict[str, Any]:
    return {"source": source, "category": category, "action": action,
            "target": target, "status": status,
            "confidence": 1.0 if status == "observed" else 0.0,
            "interpretation_level": "observation", "metadata": metadata}
