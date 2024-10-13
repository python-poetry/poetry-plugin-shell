from __future__ import annotations

import contextlib
import os

from typing import TYPE_CHECKING

from poetry.console.application import Application
from poetry.factory import Factory
from poetry.installation.executor import Executor
from poetry.packages import Locker


if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from typing import Any

    from poetry.core.packages.package import Package
    from poetry.installation.operations.operation import Operation
    from poetry.poetry import Poetry
    from tomlkit.toml_document import TOMLDocument


class TestExecutor(Executor):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self._installs: list[Package] = []
        self._updates: list[Package] = []
        self._uninstalls: list[Package] = []

    @property
    def installations(self) -> list[Package]:
        return self._installs

    @property
    def updates(self) -> list[Package]:
        return self._updates

    @property
    def removals(self) -> list[Package]:
        return self._uninstalls

    def _do_execute_operation(self, operation: Operation) -> int:
        rc = super()._do_execute_operation(operation)

        if not operation.skipped:
            getattr(self, f"_{operation.job_type}s").append(operation.package)

        return rc

    def _execute_install(self, operation: Operation) -> int:
        return 0

    def _execute_update(self, operation: Operation) -> int:
        return 0

    def _execute_remove(self, operation: Operation) -> int:
        return 0


class PoetryTestApplication(Application):
    def __init__(self, poetry: Poetry) -> None:
        super().__init__()
        self._poetry = poetry

    def reset_poetry(self) -> None:
        assert self._poetry is not None
        poetry = self._poetry
        self._poetry = Factory().create_poetry(self._poetry.file.path.parent)
        self._poetry.set_pool(poetry.pool)
        self._poetry.set_config(poetry.config)
        self._poetry.set_locker(
            TestLocker(poetry.locker.lock, self._poetry.pyproject.data)
        )


class TestLocker(Locker):
    # class name begins 'Test': tell pytest that it does not contain testcases.
    __test__ = False

    def __init__(self, lock: Path, pyproject_data: dict[str, Any]) -> None:
        super().__init__(lock, pyproject_data)
        self._locked = False
        self._write = False

    def write(self, write: bool = True) -> None:
        self._write = write

    def is_locked(self) -> bool:
        return self._locked

    def locked(self, is_locked: bool = True) -> TestLocker:
        self._locked = is_locked

        return self

    def mock_lock_data(self, data: dict[str, Any]) -> None:
        self.locked()

        self._lock_data = data

    def is_fresh(self) -> bool:
        return True

    def _write_lock_data(self, data: TOMLDocument) -> None:
        if self._write:
            super()._write_lock_data(data)
            self._locked = True
            return

        self._lock_data = data


@contextlib.contextmanager
def isolated_environment(
    environ: dict[str, Any] | None = None, clear: bool = False
) -> Iterator[None]:
    original_environ = dict(os.environ)

    if clear:
        os.environ.clear()

    if environ:
        os.environ.update(environ)

    yield

    os.environ.clear()
    os.environ.update(original_environ)
