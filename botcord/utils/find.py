from typing import Optional

from discord import Guild, Role
from discord.abc import GuildChannel
from discord.utils import get as _get

from botcord.functions import to_int as _int

__all__ = ['role', 'channel']


# noinspection DuplicatedCode
async def role(string: str, guild: Guild) -> Optional[Role]:
    """Tries to find a role in the guild.

    Tries to match by ID, then by mention, then by name."""
    string = string.strip()
    if _role := guild.get_role(_int(string)):
        return _role

    if _role := _get(guild.roles, mention=string):
        return _role

    if _role := _get(guild.roles, name=string):
        return _role

    return None


# noinspection DuplicatedCode
async def channel(string: str, guild: Guild) -> Optional[GuildChannel]:
    """Tries to find a channel in the guild.

    Tries to match by ID, then by mention, then by name."""
    string = string.strip()
    if _channel := guild.get_channel(_int(string)):
        return _channel

    if _channel := _get(guild.channels, mention=string):
        return _channel

    if _channel := _get(guild.channels, name=string):
        return _channel

    return None
