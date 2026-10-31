from __future__ import annotations

import os

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.utils.env import MockEnv

from poetry_plugin_shell.command import ShellCommand


if TYPE_CHECKING:
    from cleo.testers.command_tester import CommandTester
    from pytest_mock import MockerFixture

    from tests.types import CommandTesterFactory


@pytest.fixture
def tester(command_tester_factory: CommandTesterFactory) -> CommandTester:
    return command_tester_factory("shell")


def test_shell(tester: CommandTester, mocker: MockerFixture) -> None:
    shell_activate = mocker.patch("poetry_plugin_shell.shell.Shell.activate")

    tester.execute()
    assert isinstance(tester.command, ShellCommand)
    expected_output = f"Spawning shell within {tester.command.env.path}\n"

    shell_activate.assert_called_once_with(tester.command.env)
    assert tester.io.fetch_output() == expected_output
    assert tester.status_code == 0


def test_shell_already_active(tester: CommandTester, mocker: MockerFixture) -> None:
    os.environ["POETRY_ACTIVE"] = "1"
    shell_activate = mocker.patch("poetry_plugin_shell.shell.Shell.activate")

    tester.execute()

    assert isinstance(tester.command, ShellCommand)
    expected_output = (
        f"Virtual environment already activated: {tester.command.env.path}\n"
    )

    shell_activate.assert_not_called()
    assert tester.io.fetch_output() == expected_output
    assert tester.status_code == 0


def test_shell_without_virtualenv_shows_error(
    command_tester_factory: CommandTesterFactory,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    env = MockEnv(path=tmp_path / "system", is_venv=False)
    tester = command_tester_factory("shell", environment=env)
    shell_activate = mocker.patch("poetry_plugin_shell.shell.Shell.activate")

    tester.execute()

    error = tester.io.fetch_error()
    shell_activate.assert_not_called()
    assert "Spawning shell" not in tester.io.fetch_output()
    assert "could not find a virtual environment" in error
    assert "virtualenvs.create" in error
    assert tester.status_code == 1


@pytest.mark.parametrize(
    ("poetry_active", "real_prefix", "prefix", "expected"),
    [
        (None, None, "", False),
        ("", None, "", False),
        (" ", None, "", True),
        ("0", None, "", True),
        ("1", None, "", True),
        ("foobar", None, "", True),
        ("1", "foobar", "foobar", True),
        (None, "foobar", "foobar", True),
        (None, "foobar", "foo", True),
        (None, None, "foobar", True),
        (None, "foo", "foobar", False),
        (None, "foo", "foo", False),
    ],
)
def test__is_venv_activated(
    tester: CommandTester,
    mocker: MockerFixture,
    poetry_active: str | None,
    real_prefix: str | None,
    prefix: str,
    expected: bool,
) -> None:
    assert isinstance(tester.command, ShellCommand)
    mocker.patch.object(tester.command.env, "_path", Path("foobar"))
    mocker.patch("sys.prefix", prefix)

    if real_prefix is not None:
        mocker.patch("sys.real_prefix", real_prefix, create=True)

    if poetry_active is not None:
        os.environ["POETRY_ACTIVE"] = poetry_active

    assert tester.command._is_venv_activated() is expected
