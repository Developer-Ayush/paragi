from collections import deque
from typing import List, Any

class ContextWindow:
    """
    Maintains a sliding window of recent cognitive states.
    """
    def __init__(self, max_size: int = 10):
        self.window = deque(maxlen=max_size)

    def push(self, state: Any):
        self.window.append(state)

    def get_recent(self, count: int = 5) -> List[Any]:
        return list(self.window)[-count:]

    def clear(self):
        self.window.clear()
