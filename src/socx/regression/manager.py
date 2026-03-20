"""Regression manager orchestrating execution and persistence concerns."""

from __future__ import annotations

import time
import logging
import asyncio as aio
from typing import Any

from pydantic import ConfigDict

from socx.core.schema.types import FilePath, DirectoryPath
from socx.core import Runner, Manager, Serializer
from socx.regression.runners import (
    default_regression_runner,
    default_test_runner,
)
from socx.regression.serializers import (
    default_regression_serializer,
)
from socx.regression.test import (
    Test,
    TestStatus,
)
from socx.regression.regression import Regression


logger = logging.getLogger(__name__)


class RegressionManager(Manager[Regression]):
    """Coordinates running, restarting and persisting task objects."""

    runner: Runner[Regression]
    serializer: Serializer[Regression]
    test_runner: Runner[Test]

    model_config = ConfigDict(
        title="Manager",
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

    def __init__(
        self,
        runner: Runner[Regression] | None = None,
        serializer: Serializer[Regression] | None = None,
        test_runner: Runner[Test] | None = None,
    ):
        self.runner = runner or default_regression_runner
        self.serializer = serializer or default_regression_serializer
        self.test_runner = test_runner or default_test_runner

    async def start(
        self, task: Regression, runner: Runner[Regression] | None = None
    ) -> None:
        runner = runner or self.runner
        if task.status is TestStatus.Paused:
            await self.resume(task)
            return

        if task.started and task.status is not TestStatus.Pending:
            return

        task._stop_requested = False
        task._pause_event.set()
        task._running.clear()
        task._done = aio.Queue()
        task._pending = aio.Queue()
        task.finished_time = None
        if task.started_time is None:
            task.started_time = time.time()

        chosen_runner = runner or self.runner
        try:
            await chosen_runner.run(task)
        finally:
            task.finished_time = time.time()
            task._pause_event.set()
            task._running.clear()
            logger.info(f"task {task.status.name.lower()}.")

    async def pause(self, task: Regression) -> None:
        if not task.is_running():
            return

        task._pause_event.clear()
        await aio.gather(
            *(test.pause() for test in task._active_tests()),
            return_exceptions=True,
        )

    async def resume(self, task: Regression) -> None:
        if not task.is_suspended():
            return

        task._pause_event.set()
        await aio.gather(
            *(test.resume() for test in task.tests),
            return_exceptions=True,
        )

    async def stop(self, task: Regression) -> None:
        if task.is_idle() or task.terminated or task.finished:
            return

        task._stop_requested = True
        task._pause_event.set()
        await aio.gather(
            *(test.stop() for test in task.tests), return_exceptions=True
        )

    async def restart(self, task: Regression) -> None:
        await self.stop(task)
        self.reset(task)
        await self.start(task)

    def reset(self, task: Regression) -> None:
        super(type(task), task).reset()
        for test in task.tests:
            if hasattr(test, "reset"):
                test.reset()

        task._done = aio.Queue()
        task._pending = aio.Queue()
        task._pause_event = aio.Event()
        task._running.clear()
        task._stop_requested = False

    def soft_reset(self, task: Regression) -> None:
        if not task.started or task.passed:
            return

        super(type(task), task).soft_reset()
        for test in task.tests:
            if hasattr(test, "soft_reset"):
                test.soft_reset()

        task._done = aio.Queue()
        task._pending = aio.Queue()
        task._pause_event = aio.Event()
        task._running.clear()
        task._stop_requested = False

    def dump_state(
        self, task: Regression, output_dir: DirectoryPath | None = None
    ) -> FilePath:
        logger.info("saving task state and results to disk...")
        file = self.serializer.dump_state(task, output_dir=output_dir)
        logger.info(f"state and results saved to: '{file}'.")
        return file

    def from_file(
        self,
        cls: type[Regression],
        path: FilePath,
        name: str | None = None,
        test_cls: type[Test] | None = None,
        **kwargs: Any,
    ) -> Regression:
        return self.serializer.from_file(
            cls, path, **dict(name=name, test_cls=test_cls)
        )

    def load(
        self,
        cls: type[Regression],
        path: FilePath,
        name: str | None = None,
        test_cls: type[Test] | None = None,
        **kwargs: Any,
    ) -> Regression:
        return self.serializer.load(
            cls, path, **dict(name=name, test_cls=test_cls)
        )


default_regression_manager: Manager[Regression] = RegressionManager()
