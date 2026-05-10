"""core/exceptions.py — Exception hierarchy for the Paragi cognitive runtime."""
from __future__ import annotations


class ParagiError(Exception):
    """Base exception for all Paragi cognitive runtime errors."""
    def __init__(self, message: str, *, code: str = "paragi_error") -> None:
        super().__init__(message)
        self.code = code


class EncoderError(ParagiError):
    """Raised when the semantic compiler / encoder fails."""
    def __init__(self, message: str, *, code: str = "encoder_error") -> None:
        super().__init__(message, code=code)


class GraphError(ParagiError):
    """Raised for graph structural or storage errors."""
    def __init__(self, message: str, *, code: str = "graph_error") -> None:
        super().__init__(message, code=code)


class ReasoningError(ParagiError):
    """Raised when a reasoning pass fails or times out."""
    def __init__(self, message: str, *, code: str = "reasoning_error") -> None:
        super().__init__(message, code=code)


class DecoderError(ParagiError):
    """Raised when the decoder cannot reconstruct language from graph state."""
    def __init__(self, message: str, *, code: str = "decoder_error") -> None:
        super().__init__(message, code=code)


class CognitionError(ParagiError):
    """Raised by the cognition orchestration layer."""
    def __init__(self, message: str, *, code: str = "cognition_error") -> None:
        super().__init__(message, code=code)


class StorageError(ParagiError):
    """Raised for persistence / serialization failures."""
    def __init__(self, message: str, *, code: str = "storage_error") -> None:
        super().__init__(message, code=code)


class ConfigError(ParagiError):
    """Raised for configuration / environment variable errors."""
    def __init__(self, message: str, *, code: str = "config_error") -> None:
        super().__init__(message, code=code)


class LearningGateError(ParagiError):
    """Raised when the learning gate rejects or cannot validate an edge."""
    def __init__(self, message: str, *, code: str = "learning_gate_error") -> None:
        super().__init__(message, code=code)
