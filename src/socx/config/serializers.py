"""Serialization helpers used when bootstrapping configuration objects."""

from __future__ import annotations

from types import ModuleType
from typing import Any

from pydantic_core import to_jsonable_python
from dynaconf import LazySettings
from dynaconf.utils.boxing import DynaBox


class ModuleSerializer:
    """Serialize module globals into a Dynaconf-ready mapping."""

    @classmethod
    def serialize(
        cls, obj: ModuleType, *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        name = obj.__name__.rpartition(".")[-1]
        attr_names = getattr(obj, "__all__", ())
        attrs = {k: v for k, v in vars(obj).items() if k in attr_names}
        attrs = to_jsonable_python(attrs)
        return {name: attrs}


class SettingsSerializer:
    @classmethod
    def serialize(
        cls,
        obj: LazySettings,
        key: str | None = None,
        merge: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> DynaBox:
        """Serialize a ``LazySettings`` obj into a python ``dict``."""
        if key is None:
            return DynaBox(obj.to_dict())
        return obj.get(key, cast=False, fresh=True)
