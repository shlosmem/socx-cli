"""Asynchronous regression runner that orchestrates test execution."""

from __future__ import annotations

import asyncio as aio
import anyio
import anyio.from_thread
from pathlib import Path
from typing import Self, Any, Literal, cast
from threading import RLock
from functools import partial
from collections import OrderedDict, ChainMap
from collections.abc import AsyncGenerator, Iterable

from pydantic import (
    UUID4,
    ConfigDict,
    SerializeAsAny,
    Field,
    PrivateAttr,
    computed_field,
)

from socx.core import Manager, Runner, FilePath
from socx.config import settings
from socx.regression.test import Test, TestBase, TestResult, TestStatus
from socx.regression._utils import _safe_dir_name


class Regression(TestBase):
    """Manage and execute a collection of tests with concurrency control."""

    kind: Literal["regression"] = Field(default="regression")
    test_map: OrderedDict[UUID4, SerializeAsAny[TestBase]] = Field(
        default_factory=OrderedDict, repr=True, title="Test Map"
    )
    model_config = ConfigDict(
        title="Regression",
        from_attributes=True,
        arbitrary_types_allowed=True,
    )
    _lock: RLock = PrivateAttr(default_factory=RLock)
    _done: aio.Queue[TestBase] = PrivateAttr(default_factory=aio.Queue)
    _mutex: anyio.Semaphore = PrivateAttr(
        default_factory=partial(anyio.Semaphore, 1)
    )
    _pending: aio.Queue[TestBase | None] = PrivateAttr(
        default_factory=aio.Queue
    )
    _running: set[UUID4] = PrivateAttr(default_factory=set)
    _pause_event: aio.Event = PrivateAttr(default_factory=aio.Event)
    _stop_requested: bool = PrivateAttr(default=False)

    def __init__(
        self,
        name: str,
        tests: list[TestBase] | None = None,
        test_map: dict[UUID4, TestBase] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, name=name, **kwargs)
        test_map = test_map or {}
        tests = [*list(test_map.values()), *(tests or [])]
        self.test_map = OrderedDict({test.id: test for test in tests})

    @classmethod
    def from_file(
        cls,
        path: FilePath,
        name: str | None = None,
        test_cls: type[TestBase] | None = None,
        manager: Manager[Self] | None = None,
        **kwargs: Any,
    ) -> Self:
        kwargs = dict(ChainMap(kwargs, dict(name=name, test_cls=test_cls)))
        if manager is None:
            from socx.regression.manager import default_regression_manager

            manager = cast(Manager[Self], default_regression_manager)
        return manager.from_file(cls, path, **kwargs)

    @classmethod
    def load(
        cls,
        path: FilePath,
        name: str | None = None,
        test_cls: type[Test] | None = None,
        manager: Manager[Self] | None = None,
        **kwargs: Any,
    ) -> Self:
        kwargs = dict(ChainMap(kwargs, dict(name=name, test_cls=test_cls)))
        if manager is None:
            from socx.regression.manager import default_regression_manager

            manager = cast(Manager[Self], default_regression_manager)
        return manager.load(cls, path, **kwargs)

    @computed_field
    @property
    def result(self) -> TestResult:
        with self.lock:
            if not len(self):
                return TestResult.NA
            results = [test.result for test in self.tests]
            if all(result is TestResult.Passed for result in results):
                return TestResult.Passed
            if any(result is TestResult.Failed for result in results):
                return TestResult.Failed
            return TestResult.NA

    @computed_field
    @property
    def status(self) -> TestStatus:
        with self.lock:
            if not len(self):
                return TestStatus.Idle
            terminated_statuses = {TestStatus.Finished, TestStatus.Terminated}
            statuses = [test.status for test in self.tests]
            if all(status is TestStatus.Finished for status in statuses):
                return TestStatus.Finished
            if all(status in terminated_statuses for status in statuses):
                return TestStatus.Terminated
            if any(status is TestStatus.Running for status in statuses):
                return TestStatus.Running
            if any(status is TestStatus.Paused for status in statuses):
                return TestStatus.Paused
            if any(status is TestStatus.Idle for status in statuses):
                return TestStatus.Idle
            return TestStatus.Pending

    @computed_field
    @property
    def tests(self) -> list[TestBase]:
        with self.lock:
            return list(self.test_map.values())

    @tests.setter
    def tests(self, other: list[TestBase]) -> None:
        with self.lock:
            self.test_map = OrderedDict({test.id: test for test in other})

    @computed_field
    @property
    def run_limit(self) -> int:
        """Return the maximum number of tests that may run concurrently."""
        return int(max(1, int(settings.regression.max_runs_in_parallel)))

    @property
    def lock(self) -> RLock:
        return self._lock

    @property
    def mutex(self) -> anyio.Semaphore:
        return self._mutex

    @property
    def pending(self) -> aio.Queue:
        return self._pending

    @property
    def running(self) -> set[UUID4]:
        with self.lock:
            return self._running.copy()

    @property
    def done(self) -> aio.Queue:
        return self._done

    def __len__(self) -> int:
        """Return the number of tests scheduled within the regression."""
        return len(self.test_map)

    def __getitem__(self, key: int | UUID4):
        if isinstance(key, int):
            return self.tests[key]
        elif isinstance(key, TestBase):
            return self.test_map[key.id]
        else:
            return self.test_map[key]

    def __contains__(self, test: TestBase) -> bool:
        """Return ``True`` if ``test`` is tracked by this regression."""
        return test is not None and test.id in self.test_map

    async def start(
        self,
        runner: Runner[Regression] | None = None,
        manager: Manager[Regression] | None = None,
    ) -> None:
        """Start or resume a regression."""
        if manager is None:
            from socx.regression.manager import default_regression_manager

            manager = default_regression_manager
        if runner is None:
            from socx.regression.runners import default_regression_runner

            runner = default_regression_runner
        await manager.start(self, runner=runner)

    async def pause(self, manager: Manager[Self] | None = None) -> None:
        """Pause a running regression and any active descendants."""
        if manager is None:
            from socx.regression.manager import default_regression_manager

            manager = cast(Manager[Self], default_regression_manager)
        await manager.pause(self)

    async def resume(self, manager: Manager[Self] | None = None) -> None:
        """Resume a paused regression and any active descendants."""
        if manager is None:
            from socx.regression.manager import default_regression_manager

            manager = cast(Manager[Self], default_regression_manager)
        await manager.resume(self)

    async def stop(self, manager: Manager[Self] | None = None) -> None:
        """Terminate active work within the regression."""
        if manager is None:
            from socx.regression.manager import default_regression_manager

            manager = cast(Manager[Self], default_regression_manager)
        await manager.stop(self)

    async def restart(self, manager: Manager[Self] | None = None) -> None:
        """Terminate, reset, and execute the regression again."""
        if manager is None:
            from socx.regression.manager import default_regression_manager

            manager = cast(Manager[Self], default_regression_manager)
        await manager.restart(self)

    def reset(self, manager: Manager[Self] | None = None) -> None:
        """Reset the regression and all child tests."""
        if manager is None:
            from socx.regression.manager import default_regression_manager

            manager = cast(Manager[Self], default_regression_manager)
        manager.reset(self)

    def soft_reset(self, manager: Manager[Self] | None = None) -> None:
        """Reset this regression unless it has already passed."""
        if manager is None:
            from socx.regression.manager import default_regression_manager

            manager = cast(Manager[Self], default_regression_manager)
        manager.soft_reset(self)

    @classmethod
    async def desync[T](cls, it: Iterable[T]) -> AsyncGenerator[T]:
        for item in it:
            yield item

    async def _queue_tests(self) -> None:
        async with self.mutex:
            items = [test for test in self.tests if not test.passed]
            async with anyio.create_task_group() as tg:
                for test in items:
                    test._status = TestStatus.Pending
                    tg.start_soon(self.pending.put, test)

            async with anyio.create_task_group() as tg:
                for _ in range(self.run_limit):
                    tg.start_soon(self.pending.put, None)

    def assign_output_dir(self, output_dir: Path) -> Path:
        self.output_dir = output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        for child in self.tests:
            child_output_dir = output_dir / _safe_dir_name(
                child.name, child.id
            )
            if isinstance(child, Regression):
                child.assign_output_dir(child_output_dir)
            else:
                child.output_dir = child_output_dir

        return output_dir

    def dump_state(
        self,
        output_dir: Path | None = None,
        manager: Manager[Self] | None = None,
    ) -> Path:
        """Write the regression state and test artifacts to disk."""
        if manager is None:
            from socx.regression.manager import default_regression_manager

            manager = cast(Manager[Self], default_regression_manager)
        return manager.dump_state(self, output_dir=output_dir)

    def _active_tests(self) -> list[TestBase]:
        return [test for test in self.tests if test.id in self._running]

    def iter_leaf_tests(self) -> Iterable[TestBase]:
        for test in self.tests:
            if isinstance(test, Regression):
                yield from test.iter_leaf_tests()
            else:
                yield test

    @property
    def leaf_tests(self) -> list[TestBase]:
        return list(self.iter_leaf_tests())

    @property
    def total_test_count(self) -> int:
        return len(self.leaf_tests)

    @property
    def completed_test_count(self) -> int:
        return sum(
            1
            for test in self.iter_leaf_tests()
            if test.status in (TestStatus.Finished, TestStatus.Terminated)
        )

    @property
    def progress_ratio(self) -> float:
        total = self.total_test_count
        if total == 0:
            return 0.0
        return min(1.0, self.completed_test_count / total)

    @property
    def estimated_remaining_time(self) -> float | None:
        total = self.total_test_count
        completed = self.completed_test_count
        elapsed = self.elapsed_time

        if total == 0 or elapsed is None:
            return None
        if completed >= total:
            return 0.0
        if completed == 0 or elapsed <= 0:
            return None

        rate = completed / elapsed
        if rate <= 0:
            return None

        return max(0.0, (total - completed) / rate)

    def _persist_test_outputs(self) -> None:
        for child in self.tests:
            if isinstance(child, Regression):
                child._persist_test_outputs()
                continue

            if (
                isinstance(child, Test)
                and child.started_time is not None
                and child.output_dir is not None
            ):
                child._prepare_output_files()
                child._write_output_files()
