from __future__ import annotations

import asyncio
from time import perf_counter

from socx.regression import Test, Regression, TestResult, TestStatus

from utils import wait_for

Test.__test__ = False
TestResult.__test__ = False
TestStatus.__test__ = False


async def _wait_for(predicate, max_wait: float = 2.0) -> None:
    deadline = perf_counter() + max_wait
    while perf_counter() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.02)
    msg = "Condition was not met before timeout."
    raise AssertionError(msg)


def test_test_can_pause_and_resume() -> None:
    async def run_test() -> None:
        test = Test(name="slow", exec="sleep 0.4")
        task = asyncio.create_task(test.start())

        await _wait_for(lambda: test.status is TestStatus.Running)
        await test.pause()
        assert test.status is TestStatus.Paused

        await asyncio.sleep(0.05)
        await test.resume()
        await task

        assert test.status is TestStatus.Finished
        assert test.result is TestResult.Passed

    asyncio.run(run_test())


def test_regression_state(tmp_path) -> None:
    command = "sleep 1.5"

    async def run_test() -> None:
        regression = Regression(
            name="smoke",
            tests=[Test(name="alpha", exec=command)],
        )
        assert regression.is_idle()

        task = asyncio.create_task(regression.start())
        await wait_for(regression.is_running)

        await regression.pause()
        await wait_for(regression.is_suspended)

        await regression.resume()
        await wait_for(regression.is_running)
        await task
        assert regression.finished

        task = asyncio.create_task(regression.restart())
        await wait_for(regression.is_running)

        await regression.stop()
        assert regression.terminated
        await task

    asyncio.run(run_test())


def test_regression_can_restart_children(tmp_path) -> None:
    marker = tmp_path / "runs.log"
    command = f"echo run >> {marker}"

    async def run_test() -> None:
        regression = Regression(
            name="smoke",
            tests=[Test(name="alpha", exec=command)],
        )

        await regression.start()
        assert regression.status is TestStatus.Finished
        assert marker.read_text().splitlines() == ["run"]
        assert regression.elapsed_time is not None
        assert regression.total_test_count == 1
        assert regression.completed_test_count == 1
        assert regression.progress_ratio == 1.0
        assert regression.estimated_remaining_time == 0.0

        await regression.restart()

        assert regression.status is TestStatus.Finished
        assert marker.read_text().splitlines() == ["run", "run"]

    asyncio.run(run_test())


def test_regression_state_round_trips_with_test_outputs(tmp_path) -> None:
    async def run_test() -> None:
        regression = Regression(
            name="smoke",
            tests=[
                Test(
                    name="alpha",
                    exec="printf 'alpha out'; printf 'alpha err' >&2",
                )
            ],
        )
        session_dir = tmp_path / "session"
        regression.assign_output_dir(session_dir / regression.name)
        test = regression.tests[0]

        task = asyncio.create_task(regression.start())
        await _wait_for(
            lambda: (
                test.output_dir is not None
                and test.output_dir.is_dir()
                and test.stdout_path is not None
                and test.stdout_path.exists()
                and test.stderr_path is not None
                and test.stderr_path.exists()
            )
        )
        await task

        state_file = regression.dump_state(session_dir)
        loaded = Regression.load(state_file)
        loaded_test = loaded.tests[0]

        assert regression.started_time is not None
        assert regression.started_time > 946684800
        assert state_file.exists()
        assert isinstance(loaded_test, Test)
        assert loaded_test.stdout == "alpha out"
        assert loaded_test.stderr == "alpha err"
        assert loaded_test.finished
        assert loaded_test.output_dir is not None
        assert loaded_test.stdout_path is not None
        assert loaded_test.stdout_path.read_text() == "alpha out"
        assert loaded_test.stderr_path is not None
        assert loaded_test.stderr_path.read_text() == "alpha err"

    asyncio.run(run_test())


def test_soft_reset_preserves_passed_tests() -> None:
    test = Test(name="alpha", exec="echo ok")
    test.status = TestStatus.Finished
    test.result = TestResult.Passed
    test.started_time = 1.0

    test.soft_reset()

    assert test.status is TestStatus.Finished
    assert test.result is TestResult.Passed
    assert test.started_time == 1.0
