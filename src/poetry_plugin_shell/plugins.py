from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.plugins.application_plugin import ApplicationPlugin

from poetry_plugin_shell.command import ShellCommand


if TYPE_CHECKING:
    from poetry.console.application import Application
    from poetry.console.commands.command import Command


class ShellApplicationPlugin(ApplicationPlugin):
    @property
    def commands(self) -> list[type[Command]]:
        return [ShellCommand]

    def activate(self, application: Application) -> None:
        # Removing the existing shell command to avoid an error

        # If you're checking this code out to get inspiration
        # for your own plugins: DON'T DO THIS!
        if application.command_loader.has("shell"):
            del application.command_loader._factories["shell"]

        super().activate(application=application)
