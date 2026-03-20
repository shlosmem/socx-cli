"""Serialization strategies for regression definitions and runtime state."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import box
from pydantic import UUID4

from socx.config import settings
from socx.core.schema import FilePath
from socx.regression.test import Test, TestBase, TestResult, TestStatus


def _safe_dir_name(name: str, node_id: UUID4) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-").lower()
    return f"{slug or 'item'}-{node_id}"


def _coerce_status(value: TestStatus | int | str) -> TestStatus:
    if isinstance(value, TestStatus):
        return value
    if isinstance(value, int):
        return TestStatus(value)
    return TestStatus[value.strip().lower().title()]


def _coerce_result(value: TestResult | str) -> TestResult:
    if isinstance(value, TestResult):
        return value
    return TestResult(value)


class RegressionSerializer:
    def read_data(self, path: str | Path) -> Mapping[str, Any]:
        raise NotImplementedError

    def from_file(
        self,
        cls,
        path: str | Path,
        name: str | None = None,
        test_cls: type[TestBase] | None = None,
    ):
        raise NotImplementedError

    def load(
        self,
        cls,
        path: str | Path,
        name: str | None = None,
        test_cls: type[TestBase] | None = None,
    ):
        raise NotImplementedError

    def dump_state(self, regression, output_dir: Path | None = None) -> Path:
        raise NotImplementedError


class YamlRegressionSerializer(RegressionSerializer):
    def from_file(
        self,
        cls,
        path: str | Path,
        name: str | None = None,
        test_cls: type[TestBase] | None = None,
    ):
        from box import Box

        path = Path(FilePath(path))
        name = name or path.stem
        node_cls = test_cls or Test
        data = self.read_data(path)

        settings.update(Box({name: data}), merge=False)
        return self._from_data(cls, name, settings[name], node_cls)

    def load(
        self,
        cls,
        path: str | Path,
        name: str | None = None,
        test_cls: type[TestBase] | None = None,
    ):
        path = Path(FilePath(path))
        data = self.read_data(path)

        if self._looks_like_state(data):
            return self._from_state_data(
                cls,
                data,
                output_dir=path.parent,
                test_cls=test_cls or Test,
            )

        return self.from_file(cls, path, name=name, test_cls=test_cls)

    def dump_state(self, regression, output_dir: Path | None = None) -> Path:
        root_output_dir = regression.output_dir
        if output_dir is not None:
            root_output_dir = regression.assign_output_dir(
                output_dir / regression.name
            )

        if root_output_dir is None:
            msg = "Regression output directory is not configured."
            raise ValueError(msg)

        regression._persist_test_outputs()
        file = root_output_dir / "state.yaml"
        state = self._serialize_node(regression, root_output_dir)
        file.parent.mkdir(parents=True, exist_ok=True)
        box.DDBox(state).to_yaml(str(file))
        return file

    def read_data(self, path: str | Path) -> Mapping[str, Any]:
        from box import Box

        path = Path(path)
        suffix = path.suffix.lower()
        if suffix in {".yml", ".yaml"}:
            return Box.from_yaml(filename=str(path))
        if suffix == ".toml":
            return Box.from_toml(filename=str(path))
        if suffix == ".json":
            return Box.from_json(filename=str(path))

        msg = f"Unsupported file format: '{path.suffix}'"
        raise ValueError(msg)

    def _looks_like_state(self, data: Mapping[str, Any]) -> bool:
        return data.get("kind") == "regression" and "tests" in data

    def _from_data(
        self,
        cls,
        name: str,
        data: dict[str, Any],
        test_cls: type[TestBase],
    ):
        regressions = []
        for child_name, entries in data.items():
            if isinstance(entries, list):
                tests = [test_cls.model_validate(test) for test in entries]
                regression = cls(name=child_name, tests=tests)
            else:
                regression = cls(
                    name=child_name,
                    tests=[
                        self._from_data(cls, key, entries[key], test_cls)
                        for key in entries
                    ],
                )
            regressions.append(regression)
        return cls(name=name, tests=regressions)

    def _from_state_data(
        self,
        cls,
        data: Mapping[str, Any],
        output_dir: Path,
        test_cls: type[TestBase],
    ):
        node = self._deserialize_node(
            cls,
            data,
            root_output_dir=output_dir,
            test_cls=test_cls,
            parent_output_dir=None,
        )
        if node.kind != "regression":
            msg = "State file must contain a root regression."
            raise ValueError(msg)
        return node

    def _serialize_node(
        self, node: TestBase, root_output_dir: Path
    ) -> dict[str, Any]:
        from socx.regression.regression import Regression

        state = json.loads(
            node.model_dump_json(serialize_as_any=True)
        )

        if node.output_dir is not None and node.output_dir != root_output_dir:
            state["output_dir"] = str(
                node.output_dir.relative_to(root_output_dir)
            )

        if isinstance(node, Regression):
            state["tests"] = [
                self._serialize_node(child, root_output_dir)
                for child in node.tests
            ]
            return state

        state.pop("stdout", None)
        state.pop("stderr", None)
        if node.stdout_path is not None and node.stdout_path.exists():
            state["stdout_path"] = str(
                node.stdout_path.relative_to(root_output_dir)
            )
        if node.stderr_path is not None and node.stderr_path.exists():
            state["stderr_path"] = str(
                node.stderr_path.relative_to(root_output_dir)
            )
        return state

    def _deserialize_node(
        self,
        cls,
        data: Mapping[str, Any],
        root_output_dir: Path,
        test_cls: type[TestBase],
        parent_output_dir: Path | None,
    ):
        kind = str(data.get("kind", "")).strip().lower()
        output_dir = self._resolve_output_dir(
            data,
            root_output_dir=root_output_dir,
            parent_output_dir=parent_output_dir,
        )

        node_data = dict(data)
        node_data.pop("output_dir", None)

        if kind == "regression":
            tests_data = node_data.pop("tests", [])
            regression = cls.model_validate(node_data)
            regression.output_dir = output_dir
            regression.tests = [
                self._deserialize_node(
                    cls,
                    child,
                    root_output_dir=root_output_dir,
                    test_cls=test_cls,
                    parent_output_dir=regression.output_dir,
                )
                for child in tests_data
            ]
            return regression

        if kind != "test":
            msg = f"Unknown state node kind: '{kind}'"
            raise ValueError(msg)

        stdout_relpath = node_data.pop("stdout_path", None)
        stderr_relpath = node_data.pop("stderr_path", None)
        test = test_cls.model_validate(node_data)
        test.output_dir = output_dir
        test.status = _coerce_status(data.get("status", TestStatus.Idle))
        test.result = _coerce_result(data.get("result", TestResult.NA))

        if isinstance(test, Test):
            root_output_dir_resolved = root_output_dir.resolve()
            for attr, relpath in (
                ("stdout", stdout_relpath),
                ("stderr", stderr_relpath),
            ):
                if relpath:
                    candidate = (root_output_dir / str(relpath)).resolve()
                    try:
                        candidate.relative_to(root_output_dir_resolved)
                    except ValueError:
                        continue
                    if candidate.exists():
                        setattr(
                            test,
                            attr,
                            candidate.read_text(encoding="utf-8"),
                        )

        return test

    def _resolve_output_dir(
        self,
        data: Mapping[str, Any],
        *,
        root_output_dir: Path,
        parent_output_dir: Path | None,
    ) -> Path:
        relative_output_dir = data.get("output_dir")
        if relative_output_dir:
            return root_output_dir / str(relative_output_dir)
        if parent_output_dir is None:
            return root_output_dir
        return parent_output_dir / _safe_dir_name(data["name"], data["id"])


default_regression_serializer = YamlRegressionSerializer()
