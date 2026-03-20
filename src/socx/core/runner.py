from __future__ import annotations

from abc import ABC, abstractmethod


class Runner[T](ABC):
    @abstractmethod
    async def run(self, task: T) -> None:
        """Run an executable task."""
        ...
