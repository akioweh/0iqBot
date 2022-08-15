import asyncio
from datetime import datetime
from typing import Optional, Union

from discord import Member, Message, PartialEmoji, Role, TextChannel, User
from discord.ext.commands import Cog, Context, group
from discord.ext.commands.converter import Greedy, UserConverter
from discord.ext.commands.errors import UserNotFound

from botcord.utils import find, str_info


class AdvInfo(Cog):
    def __init__(self, bot):
        self.bot = bot

    # ========== Escape Discord Utility ========== #

    @group(aliases=['esc', 'str'], invoke_without_command=True)
    async def escape(self, ctx: Context, args: Greedy[Union[PartialEmoji, User, Role, TextChannel]] = None):
        """
        'Escapes' special discord items; outputs plain copy-able text.
        Works for:
         - Roles
         - Channels
         - Pings/Mentions
         - Emojis

        The main command tries to determine the type and convert appropriately. If that doesn't work, there is a
        subcommand for each type. For example, `escape @a-ping` will output a plain text/string that will generate
        the ping when pasted.
        """
        if args:
            msg = '[ '
            for item in args:
                if isinstance(item, PartialEmoji):
                    msg += f'`{str(item)}` | '
                else:
                    msg += f'`{item.mention}` | '
            msg = msg.rstrip(' | ')
            msg += ' ]'
            await ctx.reply(msg)

    @escape.command()
    async def emoji(self, ctx: Context, emoji: Optional[PartialEmoji] = None):
        if emoji:
            await ctx.reply(f'`{str(emoji)}`')
        else:
            await ctx.reply('Emoji not found (Builtin/unicode emojis cannot be escaped).', delete_after=10)

    @escape.command(aliases=['ping'])
    async def mention(self, ctx: Context, user):
        try:
            user = await UserConverter().convert(ctx, user)
            await ctx.reply(f'`{user.mention}`')
        except UserNotFound:
            await ctx.reply('User not found.', delete_after=10)

    @escape.command()
    async def channel(self, ctx: Context, channel):
        if channel := await find.channel(channel, ctx.guild):
            await ctx.reply(f'`{channel.mention}`')
        else:
            await ctx.reply('Channel not found (Only works with channels in THIS server).', delete_after=10)

    @escape.command()
    async def role(self, ctx: Context, role):
        if role := await find.role(role, ctx.guild):
            await ctx.reply(f'`{role.mention}`')
        else:
            await ctx.reply('Role not found (Only works with roles in THIS server).', delete_after=10)

    # ========== Bot Status Info ========== #

    @group(invoke_without_command=True)
    async def status(self, ctx: Context):
        await ctx.reply('TODO: show bot\'s status and various metrics')

    @status.command()
    async def ping(self, ctx: Context):
        """Calculates Websocket and True Ping"""
        p_t = asyncio.create_task(ctx.reply('Pinging...'))
        await asyncio.sleep(0)
        start1 = datetime.utcnow()
        start2 = ctx.message.created_at

        def ping_msg_check(msg: Message):
            return msg.author.id == self.bot.user.id and msg.content == 'Pinging...'

        ping_msg = await self.bot.wait_for('message', check=ping_msg_check, timeout=5)
        stop1 = datetime.utcnow()
        stop2 = ping_msg.created_at
        delta1 = (stop1 - start1).total_seconds() * 1000
        delta2 = (stop2 - start2).total_seconds() * 1000
        websocket_ping = self.bot.latency

        await ctx.send(f'Websocket Ping: `{websocket_ping * 1000}`ms \n'
                       f'True Ping (bot-based): `{delta1}`ms \n'
                       f'True Ping (message-based): `{delta2}`ms')
        await p_t

    # ========== Discord Object Info ========== #

    @group(invoke_without_command=True)
    async def info(self, ctx: Context, obj: Optional[Member] = None):
        if not obj:
            await ctx.reply('This object type isn\'t supported yet... or try using a specific subcommand.')
        else:
            await ctx.reply(str_info.member_details(obj))

    @info.command()
    async def member(self, ctx: Context, member: Member):
        await ctx.reply(str_info.member_details(member))


def setup(bot):
    bot.add_cog(AdvInfo(bot))
