"""graph/contradiction/__init__.py"""
from .detector import detect_contradiction, scan_contradictions
from .resolver import resolve_by_weakening, resolve_by_flagging
__all__ = ["detect_contradiction", "scan_contradictions", "resolve_by_weakening", "resolve_by_flagging"]
