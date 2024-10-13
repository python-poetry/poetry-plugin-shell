# Poetry Plugin: Shell

[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)

> [!NOTE]
> We are looking for maintainers, see the [issue](https://github.com/python-poetry/poetry-plugin-shell/issues/3).

This package is a plugin that runs a subshell with virtual environment activated.


This plugin replaces the same feature as the `shell` command previously available in Poetry.


## Installation

The easiest way to install the `shell` plugin is via the `self add` command of Poetry.

```bash
poetry self add poetry-plugin-shell
```

If you used `pipx` to install Poetry you can add the plugin via the `pipx inject` command.

```bash
pipx inject poetry poetry-plugin-shell
```

Otherwise, if you used `pip` to install Poetry you can add the plugin packages via the `pip install` command.

```bash
pip install poetry-plugin-shell
```


## Usage

The plugin provides a `shell` command to run a subshell with virtual environment activated.

```bash
poetry shell
```

By default, the current active shell is detected and used. Failing that,
the shell defined via the environment variable `SHELL` (on *nix) or
`COMSPEC` (on Windows) is used.

If a virtual environment does not exist, it will be created.

Note that this command starts a new shell and activates the virtual environment.

As such, `exit` should be used to properly exit the shell and the virtual environment instead of `deactivate`.

> [!NOTE]
> This plugin internally uses the [Shellingham](https://github.com/sarugaku/shellingham) project to detect current active shell.
