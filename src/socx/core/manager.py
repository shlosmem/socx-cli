from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from socx.core.runner import Runner
from socx.core.schema.types import FilePath, DirectoryPath


class Manager[T](ABC):
    """Coordinates running, restarting and persisting regression objects."""

    @abstractmethod
    async def start(
        self, task: T, runner: Runner[T] | None = None
    ) -> None: ...

    @abstractmethod
    async def pause(self, task: T) -> None: ...

    @abstractmethod
    async def resume(self, task: T) -> None: ...

    @abstractmethod
    async def stop(self, task: T) -> None: ...

    @abstractmethod
    async def restart(self, task: T) -> None: ...

    @abstractmethod
    def reset(self, task: T) -> None: ...

    @abstractmethod
    def soft_reset(self, task: T) -> None: ...

    @abstractmethod
    def dump_state(
        self, task: T, output_dir: DirectoryPath | None = None
    ) -> FilePath: ...

    @abstractmethod
    def from_file(
        self,
        cls: type[T],
        path: FilePath,
        **kwargs: Any,
    ) -> T: ...

    @abstractmethod
    def load(
        self,
        cls: type[T],
        path: FilePath,
        **kwargs: Any,
    ) -> T: ...
