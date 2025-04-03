from asyncio import gather
from contextlib import suppress
from typing import TYPE_CHECKING

from discord import Message, User
from discord.ext.commands import Context, check_any, command

from botcord.ext.commands import Cog
from botcord.ext.commands.checks import guild_owner_or_perms, has_global_perms

if TYPE_CHECKING:
    from botcord import BotClient


class Purger(Cog):
    def __init__(self, bot: 'BotClient'):
        self.bot: 'BotClient' = bot

    @command(aliases=['clear', 'cancel'], hidden=True)
    @check_any(guild_owner_or_perms(administrator=True), has_global_perms(owner=True))
    async def obliterate(self, ctx: Context, user: User):
        """Obliterate someone by deleting ALL their messages, ever."""
        await ctx.send(f'Are you sure you want to obliterate {user.mention}? (yes/no)', delete_after=5)
        with suppress(TimeoutError):
            reply = await self.bot.wait_for(
                'message',
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=10
            )
            if reply.content.lower() == 'yes':
                await ctx.send(f'Obliterating {user.mention}...', delete_after=5)
                await self._obliterate(ctx, user)
                return
        await ctx.send('Obliteration cancelled.', delete_after=5)

    @staticmethod
    async def _obliterate(ctx: Context, user: User):
        if ctx.guild is None:
            await ctx.send('Who on Mars are you trying to obliterate here? Yourself? '
                           'This command only works in guilds.')
            return
        channels = ctx.guild.text_channels
        tasks = []
        for channel in channels:
            tasks.append(channel.purge(check=lambda m: m.author == user))

        res: list[list[Message] | BaseException] = await gather(*tasks, return_exceptions=True)

        deleted = 0
        errors = []
        for r in res:
            if isinstance(r, BaseException):
                if isinstance(r, Exception):
                    errors.append(r)
                else:
                    raise r
            else:
                deleted += len(r)

        if errors:
            await ctx.send('Error(s) have occurred while obliterating messages... '
                           'Not all messages may have been deleted.')
        await ctx.send(f'Obliteration complete. ({deleted} messages vaporized)', delete_after=5)
        if errors:
            raise errors[0]


async def setup(bot: 'BotClient'):
    await bot.add_cog(Purger(bot))
