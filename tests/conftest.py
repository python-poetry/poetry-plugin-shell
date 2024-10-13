from __future__ import annotations

import os
import sys

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest

from cleo.io.null_io import NullIO
from cleo.testers.command_tester import CommandTester
from poetry.config.config import Config as BaseConfig
from poetry.config.dict_config_source import DictConfigSource
from poetry.core.packages.package import Package
from poetry.factory import Factory
from poetry.installation import Installer
from poetry.layouts import layout
from poetry.repositories import Repository
from poetry.repositories.repository_pool import RepositoryPool
from poetry.utils.env import MockEnv
from poetry.utils.env import SystemEnv

from tests.helpers import PoetryTestApplication
from tests.helpers import TestExecutor
from tests.helpers import TestLocker
from tests.helpers import isolated_environment


if TYPE_CHECKING:
    from collections.abc import Iterator

    from poetry.installation.executor import Executor
    from poetry.poetry import Poetry
    from poetry.utils.env import Env
    from pytest_mock import MockerFixture

    from tests.types import CommandTesterFactory
    from tests.types import ProjectFactory


class Config(BaseConfig):
    def get(self, setting_name: str, default: Any = None) -> Any:
        self.merge(self._config_source.config)  # type: ignore[attr-defined]
        self.merge(self._auth_config_source.config)  # type: ignore[attr-defined]

        return super().get(setting_name, default=default)

    def raw(self) -> dict[str, Any]:
        self.merge(self._config_source.config)  # type: ignore[attr-defined]
        self.merge(self._auth_config_source.config)  # type: ignore[attr-defined]

        return super().raw()

    def all(self) -> dict[str, Any]:
        self.merge(self._config_source.config)  # type: ignore[attr-defined]
        self.merge(self._auth_config_source.config)  # type: ignore[attr-defined]

        return super().all()


@pytest.fixture
def config_cache_dir(tmp_path: Path) -> Path:
    path = tmp_path / ".cache" / "pypoetry"
    path.mkdir(parents=True)

    return path


@pytest.fixture
def config_source(config_cache_dir: Path) -> DictConfigSource:
    source = DictConfigSource()
    source.add_property("cache-dir", str(config_cache_dir))

    return source


@pytest.fixture
def auth_config_source() -> DictConfigSource:
    source = DictConfigSource()

    return source


@pytest.fixture
def config(
    config_source: DictConfigSource,
    auth_config_source: DictConfigSource,
    mocker: MockerFixture,
) -> Config:
    import keyring

    from keyring.backends.fail import Keyring

    keyring.set_keyring(Keyring())  # type: ignore[no-untyped-call]

    c = Config()
    c.merge(config_source.config)
    c.set_config_source(config_source)
    c.set_auth_config_source(auth_config_source)

    mocker.patch("poetry.config.config.Config.create", return_value=c)
    mocker.patch("poetry.config.config.Config.set_config_source")

    return c


@pytest.fixture(autouse=True)
def isolate_environ() -> Iterator[None]:
    """Ensure the environment is isolated from user configuration."""
    with isolated_environment():
        for var in os.environ:
            if var.startswith("POETRY_") or var in {"PYTHONPATH", "VIRTUAL_ENV"}:
                del os.environ[var]

        yield


@pytest.fixture
def fixture_root() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_root_uri(fixture_root: Path) -> str:
    return fixture_root.as_uri()


@pytest.fixture()
def repo() -> Repository:
    return Repository("repo")


@pytest.fixture
def installed() -> Repository:
    return Repository("installed")


@pytest.fixture(scope="session")
def current_env() -> SystemEnv:
    return SystemEnv(Path(sys.executable))


@pytest.fixture(scope="session")
def current_python(current_env: SystemEnv) -> tuple[Any, ...]:
    return current_env.version_info[:3]


@pytest.fixture(scope="session")
def default_python(current_python: tuple[int, int, int]) -> str:
    return "^" + ".".join(str(v) for v in current_python[:2])


@pytest.fixture
def project_factory(
    tmp_path: Path,
    config: Config,
    repo: Repository,
    installed: Repository,
    default_python: str,
) -> ProjectFactory:
    def _factory(
        name: str,
        dependencies: dict[str, str] | None = None,
        dev_dependencies: dict[str, str] | None = None,
        pyproject_content: str | None = None,
        poetry_lock_content: str | None = None,
        install_deps: bool = True,
    ) -> Poetry:
        project_dir = tmp_path / f"poetry-fixture-{name}"
        dependencies = dependencies or {}
        dev_dependencies = dev_dependencies or {}

        if pyproject_content:
            project_dir.mkdir(parents=True, exist_ok=True)
            with project_dir.joinpath("pyproject.toml").open(
                "w", encoding="utf-8"
            ) as f:
                f.write(pyproject_content)
        else:
            layout("src")(
                name,
                "0.1.0",
                author="PyTest Tester <mc.testy@testface.com>",
                readme_format="md",
                python=default_python,
                dependencies=dict(dependencies),
                dev_dependencies=dict(dev_dependencies),
            ).create(project_dir, with_tests=False)

        if poetry_lock_content:
            lock_file = project_dir / "poetry.lock"
            lock_file.write_text(data=poetry_lock_content, encoding="utf-8")

        poetry = Factory().create_poetry(project_dir)

        locker = TestLocker(
            poetry.locker.lock,
            poetry.locker._pyproject_data,
        )
        locker.write()

        poetry.set_locker(locker)
        poetry.set_config(config)

        pool = RepositoryPool()
        pool.add_repository(repo)

        poetry.set_pool(pool)

        if install_deps:
            for deps in [dependencies, dev_dependencies]:
                for name, version in deps.items():
                    pkg = Package(name, version)
                    repo.add_package(pkg)
                    installed.add_package(pkg)

        return poetry

    return _factory


@pytest.fixture
def command_tester_factory(
    app: PoetryTestApplication, env: MockEnv
) -> CommandTesterFactory:
    def _tester(
        command: str,
        poetry: Poetry | None = None,
        installer: Installer | None = None,
        executor: Executor | None = None,
        environment: Env | None = None,
    ) -> CommandTester:
        app._load_plugins(NullIO())

        command_obj = app.find(command)
        tester = CommandTester(command_obj)

        # Setting the formatter from the application
        # TODO: Find a better way to do this in Cleo
        app_io = app.create_io()
        formatter = app_io.output.formatter
        tester.io.output.set_formatter(formatter)
        tester.io.error_output.set_formatter(formatter)

        if poetry:
            app._poetry = poetry

        poetry = app.poetry

        if hasattr(command_obj, "set_env"):
            command_obj.set_env(environment or env)

        if hasattr(command_obj, "set_installer"):
            installer = installer or Installer(
                tester.io,
                env,
                poetry.package,
                poetry.locker,
                poetry.pool,
                poetry.config,
                executor=executor
                or TestExecutor(env, poetry.pool, poetry.config, tester.io),
            )
            command_obj.set_installer(installer)

        return tester

    return _tester


@pytest.fixture
def app(poetry: Poetry) -> PoetryTestApplication:
    app_ = PoetryTestApplication(poetry)

    return app_


PYPROJECT_CONTENT = """\
[tool.poetry]
name = "simple-project"
version = "1.2.3"
description = "Some description."
authors = [
    "Sébastien Eustace <sebastien@eustace.io>"
]
license = "MIT"

readme = "README.rst"

homepage = "https://python-poetry.org"
repository = "https://github.com/python-poetry/poetry"
documentation = "https://python-poetry.org/docs"

keywords = ["packaging", "dependency", "poetry"]

classifiers = [
    "Topic :: Software Development :: Build Tools",
    "Topic :: Software Development :: Libraries :: Python Modules"
]

# Requirements
[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
foo = "^1.0"
bar = { version = "^1.1", optional = true }
qux = { version = "^1.2", optional = true }

[tool.poetry.group.dev.dependencies]
baz = "^2.0"

[tool.poetry.group.opt]
optional = true

[tool.poetry.group.opt.dependencies]
opt = "^2.2"


[tool.poetry.extras]
feature_bar = ["bar"]
feature_qux = ["qux"]
"""


@pytest.fixture
def poetry(project_factory: ProjectFactory) -> Poetry:
    return project_factory(name="simple", pyproject_content=PYPROJECT_CONTENT)


@pytest.fixture
def env(tmp_path: Path) -> MockEnv:
    path = tmp_path / ".venv"
    path.mkdir(parents=True)
    return MockEnv(path=path, is_venv=True)
