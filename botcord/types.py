from typing import Protocol


class SupportsWrite(Protocol):
    def write(self, s: str, *args, **kwargs):
        ...
