from discord.utils import get as _get

from botcord.functions import to_int as _int


async def role(string, guild):
    string = string.strip()
    if _role := guild.get_role(_int(string)):
        return _role

    if _role := _get(guild.roles, mention=string):
        return _role

    if _role := _get(guild.roles, name=string):
        return _role

    return None


async def channel(string, guild):
    string = string.strip()
    if _channel := guild.get_channel(_int(string)):
        return _channel

    if _channel := _get(guild.channels, mention=string):
        return _channel

    if _channel := _get(guild.channels, name=string):
        return _channel

    return None

# End
