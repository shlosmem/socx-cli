"""Regression manager orchestrating execution and persistence concerns."""

from __future__ import annotations

import asyncio as aio
import logging
import time

from socx.regression.runners import (
    default_regression_runner,
    default_test_runner,
)
from socx.regression.serializers import default_regression_serializer
from socx.regression.test import TestStatus


logger = logging.getLogger(__name__)


class RegressionManager:
    """Coordinates running, restarting and persisting regression objects."""

    def __init__(self, runner=None, serializer=None, test_runner=None):
        self.runner = runner or default_regression_runner
        self.serializer = serializer or default_regression_serializer
        self.test_runner = test_runner or default_test_runner

    async def start(self, regression, runner=None) -> None:
        if regression.status is TestStatus.Paused:
            await self.resume(regression)
            return

        if regression.started and regression.status is not TestStatus.Pending:
            return

        regression._stop_requested = False
        regression._pause_event.set()
        regression._running.clear()
        regression._done = aio.Queue()
        regression._pending = aio.Queue()
        regression.finished_time = None
        if regression.started_time is None:
            regression.started_time = time.time()

        chosen_runner = runner or self.runner
        try:
            await chosen_runner.run(regression)
        finally:
            regression.finished_time = time.time()
            regression._pause_event.set()
            regression._running.clear()
            logger.info(f"regression {regression.status.name.lower()}.")

    async def pause(self, regression) -> None:
        if regression.status is not TestStatus.Running:
            return

        regression._pause_event.clear()
        await aio.gather(
            *(test.pause() for test in regression._active_tests()),
            return_exceptions=True,
        )

    async def resume(self, regression) -> None:
        if regression.status is not TestStatus.Paused:
            return

        regression._pause_event.set()
        await aio.gather(
            *(test.resume() for test in regression.tests),
            return_exceptions=True,
        )

    async def stop(self, regression) -> None:
        if regression.status is TestStatus.Terminated:
            return

        regression._stop_requested = True
        regression._pause_event.set()
        await aio.gather(*(test.stop() for test in regression.tests), return_exceptions=True)

    async def restart(self, regression) -> None:
        await self.stop(regression)
        self.reset(regression)
        await self.start(regression)

    def reset(self, regression) -> None:
        super(type(regression), regression).reset()
        for test in regression.tests:
            if hasattr(test, "reset"):
                test.reset()

        regression._done = aio.Queue()
        regression._pending = aio.Queue()
        regression._pause_event = aio.Event()
        regression._running.clear()
        regression._stop_requested = False

    def soft_reset(self, regression) -> None:
        if regression.passed:
            return

        super(type(regression), regression).reset()
        for test in regression.tests:
            if hasattr(test, "soft_reset"):
                test.soft_reset()

        regression._done = aio.Queue()
        regression._pending = aio.Queue()
        regression._pause_event = aio.Event()
        regression._running.clear()
        regression._stop_requested = False

    def dump_state(self, regression, output_dir=None):
        logger.info("saving regression state and results to disk...")
        file = self.serializer.dump_state(regression, output_dir=output_dir)
        logger.info(f"state and results saved to: '{file}'.")
        return file

    def from_file(self, cls, path, name=None, test_cls=None, **kwargs):
        return self.serializer.from_file(cls, path, name=name, test_cls=test_cls)

    def load(self, cls, path, name=None, test_cls=None, **kwargs):
        return self.serializer.load(cls, path, name=name, test_cls=test_cls)


default_regression_manager = RegressionManager()
