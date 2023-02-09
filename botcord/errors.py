"""Custom Error Classes"""

from discord.ext.commands import ExtensionError as _ExtensionError

__all__ = ['ExtensionDisabledGuild']


class ExtensionDisabledGuild(_ExtensionError):
    """Designed to be raised when a command/listener/etc.
    is invoked in a guild that doesn't have it enabled.

    Designed to be raised to stop execution of the disabled code
    and caught and ignored (similar to discord.ext.commands.CheckFailure).

    Subclasses discord.ext.commands.ExtensionError, so the name of the
    extension must be passed to the constructor as a keyword argument."""
