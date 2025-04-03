from discord import Guild, Role
from discord.abc import GuildChannel
from discord.utils import get as _get

from botcord.functions import to_int as _int

__all__ = ['role', 'channel']


# noinspection DuplicatedCode
async def role(string: str, guild: Guild) -> Role | None:
    """Tries to find a role in the guild.

    Tries to match by ID, then by mention, then by name."""
    string = string.strip()
    if (role_id := _int(string)) is not None and (_role := guild.get_role(role_id)):
        return _role

    if _role := _get(guild.roles, mention=string):
        return _role

    if _role := _get(guild.roles, name=string):
        return _role

    return None


# noinspection DuplicatedCode
async def channel(string: str, guild: Guild) -> GuildChannel | None:
    """Tries to find a channel in the guild.

    Tries to match by ID, then by mention, then by name."""
    string = string.strip()
    if (channel_id := _int(string)) is not None and (_channel := guild.get_channel(channel_id)):
        return _channel

    if _channel := _get(guild.channels, mention=string):
        return _channel

    if _channel := _get(guild.channels, name=string):
        return _channel

    return None
