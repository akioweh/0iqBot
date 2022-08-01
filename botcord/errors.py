"""Custom Error Classes"""

from discord.ext.commands import CommandInvokeError as _CommandInvokeError

__all__ = ['ExtensionDisabledGuild']


class ExtensionDisabledGuild(_CommandInvokeError):
    """Raised when a command/etc. is invoked
    in a guild that doesn't have it enabled

    designd to be raised to stop execution of the command
    and caught and ignored (similar to discord.ext.commands.CheckFailure)"""
    pass
