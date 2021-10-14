from typing import Optional, Union

from discord import PartialEmoji, User, Role, TextChannel
from discord.ext.commands import Cog, Context, group
from discord.ext.commands.errors import UserNotFound
from discord.ext.commands.converter import UserConverter, Greedy

from botcord.utils import find


class AdvInfo(Cog):
    def __init__(self, bot):
        self.bot = bot

    @group(aliases=['esc', 'str'], invoke_without_command=True)
    async def escape(self, ctx: Context, args: Greedy[Union[PartialEmoji, User, Role, TextChannel]] = None):
        """
        'Escapes' special discord items; outputs plain copy-able text.
        Works for:
         - Roles
         - Channels
         - Pings/Mentions
         - Emojis

        The main command tries to determing the type and convert appropriately. If that doesn't work, there is a subcommand for each type.
        For example, `escape @a-ping` will output a plain text/string that will generate the ping when pasted.
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


def setup(bot):
    bot.add_cog(AdvInfo(bot))
