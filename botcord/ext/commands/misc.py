"""
Yeah.
"""

from typing import TYPE_CHECKING

from discord.ext.commands import Context as _Context

if TYPE_CHECKING:
    from botcord import BotClient

__all__ = ['Context']

type Context = _Context[BotClient]
