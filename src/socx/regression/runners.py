"""Runner strategies used by test and regression models."""

from __future__ import annotations

import asyncio as aio
import time
import logging

import anyio

from socx.config import settings
from socx.regression.test import TestBase, Test, TestResult, TestStatus


logger = logging.getLogger(__name__)

semaphore = anyio.Semaphore(max(1, settings.regression.max_runs_in_parallel))


class TestRunner:
    """Interface for executing a single test node."""

    async def run(self, test: TestBase) -> None:
        raise NotImplementedError


class RegressionRunner:
    """Interface for executing a regression node."""

    async def run(self, regression) -> None:
        raise NotImplementedError


class DefaultTestRunner(TestRunner):
    """Subprocess-backed implementation for executing ``Test`` models."""

    async def run(self, test: TestBase) -> None:
        if not isinstance(test, Test):
            msg = f"Unsupported test type: {type(test).__name__}"
            raise TypeError(msg)

        if test.is_running():
            return

        if test.is_suspended():
            await test.resume()
            return

        test._termination_requested = False
        test.result = TestResult.NA
        test.stdout = ""
        test.stderr = ""
        test.started_time = time.time()
        test.finished_time = None
        test.status = TestStatus.Pending
        test._prepare_output_files()

        if not test.exec:
            test.status = TestStatus.Terminated
            test.result = TestResult.Failed
            test.finished_time = time.time()
            test._write_output_files()
            return

        process = await aio.create_subprocess_exec(
            "/bin/sh",
            "-c",
            str(test.exec),
            stdout=aio.subprocess.PIPE,
            stderr=aio.subprocess.PIPE,
            start_new_session=True,
        )
        test._process = process
        test.status = TestStatus.Running

        stdout, stderr = None, None

        try:
            stdout, stderr = await process.communicate()
        finally:
            test.finished_time = time.time()
            test.stderr = stderr.decode() if stderr else ""
            test.stdout = stdout.decode() if stdout else ""
            test._write_output_files()
            returncode = process.returncode or 0

            if test._termination_requested or returncode < 0:
                test.status = TestStatus.Terminated
                test.result = TestResult.Failed
            elif returncode == 0:
                test.status = TestStatus.Finished
                test.result = TestResult.Passed
            else:
                test.status = TestStatus.Finished
                test.result = TestResult.Failed

            test._process = None


class DefaultRegressionRunner(RegressionRunner):
    """Default concurrent runner implementation for regressions."""

    async def run(self, regression) -> None:
        logger.info("regression starting...")
        await regression._queue_tests()
        async with anyio.create_task_group() as tg:
            for _ in range(regression.run_limit):
                tg.start_soon(self._worker, regression)

    async def _worker(self, regression) -> None:
        while True:
            await semaphore.acquire()
            test = await regression.pending.get()
            try:
                if test is None:
                    return

                while not regression._pause_event.is_set():
                    await aio.sleep(0.05)

                if regression._stop_requested:
                    return

                regression._running.add(test.id)
                await test.start()
                await regression.done.put(test)
            finally:
                if test is not None:
                    regression._running.discard(test.id)
                regression.pending.task_done()
                semaphore.release()


default_test_runner = DefaultTestRunner()
default_regression_runner = DefaultRegressionRunner()
