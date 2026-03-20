"""Runner strategies used by test and regression models."""

from __future__ import annotations

import asyncio as aio
import time
import logging

import anyio

from socx.core import Runner
from socx.config import settings
from socx.regression.test import Test, TestResult, TestStatus
from socx.regression.regression import Regression


logger = logging.getLogger(__name__)

semaphore = anyio.Semaphore(max(1, settings.regression.max_runs_in_parallel))


class TestRunner(Runner[Test]):
    """Interface for executing a single test node."""

    async def run(self, task: Test) -> None:
        raise NotImplementedError


class RegressionRunner(Runner[Regression]):
    """Interface for executing a regression node."""

    async def run(self, task: Regression) -> None:
        raise NotImplementedError


class DefaultTestRunner(TestRunner):
    """Subprocess-backed implementation for executing ``Test`` models."""

    async def run(self, task: Test) -> None:
        if not isinstance(task, Test):
            msg = f"Unsupported task type: {type(task).__name__}"
            raise TypeError(msg)

        if task.is_running():
            return

        if task.is_suspended():
            await task.resume()
            return

        task._termination_requested = False
        task.result = TestResult.NA
        task.stdout = ""
        task.stderr = ""
        task.started_time = time.time()
        task.finished_time = None
        task.status = TestStatus.Pending
        task._prepare_output_files()

        if not task.exec:
            task.status = TestStatus.Terminated
            task.result = TestResult.Failed
            task.finished_time = time.time()
            task._write_output_files()
            return

        process = await aio.create_subprocess_shell(
            str(task.exec),
            stdout=aio.subprocess.PIPE,
            stderr=aio.subprocess.PIPE,
            start_new_session=True,
        )
        task._process = process
        task.status = TestStatus.Running

        stdout, stderr = None, None

        try:
            stdout, stderr = await process.communicate()
        finally:
            task.finished_time = time.time()
            task.stderr = stderr.decode() if stderr else ""
            task.stdout = stdout.decode() if stdout else ""
            task._write_output_files()
            returncode = process.returncode or 0

            if task._termination_requested or returncode < 0:
                task.status = TestStatus.Terminated
                task.result = TestResult.Failed
            elif returncode == 0:
                task.status = TestStatus.Finished
                task.result = TestResult.Passed
            else:
                task.status = TestStatus.Finished
                task.result = TestResult.Failed

            task._process = None


class DefaultRegressionRunner(RegressionRunner):
    """Default concurrent runner implementation for regressions."""

    async def run(self, task: Regression) -> None:
        logger.info("task starting...")
        async with anyio.create_task_group() as tg:
            tg.start_soon(task._queue_tests)
            for _ in range(task.run_limit):
                tg.start_soon(self._worker, task)

    async def _worker(self, task: Regression) -> None:
        async with semaphore:
            while True:
                test = await task.pending.get()
                try:
                    if test is None:
                        return

                    if not task._pause_event.is_set():
                        await anyio.sleep(0.05)

                    if task._stop_requested:
                        return

                    task._running.add(test.id)
                    runner = getattr(self, "test_runner", default_test_runner)
                    await test.start(runner=runner)
                    await task.done.put(test)
                finally:
                    if test is not None:
                        task._running.discard(test.id)
                    task.pending.task_done()


default_test_runner = DefaultTestRunner()
default_regression_runner = DefaultRegressionRunner()
