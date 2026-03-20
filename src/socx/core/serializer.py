from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from pathlib import Path
from collections.abc import Mapping


class Serializer[T](ABC):
    @abstractmethod
    def load(
        self,
        cls: type[T],
        path: str | Path,
    ) -> T: ...

    @abstractmethod
    def from_file(
        self,
        cls: type[T],
        path: str | Path,
    ) -> T: ...

    @abstractmethod
    def serialize(
        self, obj: T, *args: Any, **kwargs: Any
    ) -> Mapping[str, Any]: ...

    @abstractmethod
    def read_data(self, path: str | Path) -> Mapping[str, Any]: ...

    @abstractmethod
    def dump_state(self, obj: T, output_dir: Path | None = None) -> Path: ...
