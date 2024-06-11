from asyncio import gather, TimeoutError
from typing import TYPE_CHECKING

from discord import User, TextChannel, Message
from discord.ext.commands import command, Context

from botcord.ext.commands import Cog
from botcord.ext.commands.checks import guild_admin_or_perms

if TYPE_CHECKING:
    from botcord import BotClient


class Purger(Cog):
    def __init__(self, bot: 'BotClient'):
        self.bot: 'BotClient' = bot

    @command(aliases=['clear', 'cancel'], hidden=True)
    @guild_admin_or_perms()
    async def obliterate(self, ctx: Context, user: User):
        """Obliterate someone by deleting ALL their messages, ever."""
        await ctx.send(f'Are you sure you want to obliterate {user.mention}? (yes/no)', delete_after=5)
        try:
            reply = await self.bot.wait_for(
                'message',
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=10
            )
            if reply.content.lower() == 'yes':
                await ctx.send(f'Obliterating {user.mention}...', delete_after=5)
                await self._obliterate(ctx, user)
            else:
                await ctx.send('Obliteration cancelled.', delete_after=5)
        except TimeoutError:
            await ctx.send('Obliteration cancelled.', delete_after=5)

    @staticmethod
    async def _obliterate(ctx: Context, user: User):
        channels: list[TextChannel] = ctx.guild.text_channels
        tasks = []
        for channel in channels:
            tasks.append(channel.purge(check=lambda m: m.author == user))

        res = await gather(*tasks, return_exceptions=True)

        deleted = 0
        r: Exception | list[Message]
        for r in res:
            if isinstance(r, Exception):
                await ctx.send('An error occurred while purging messages.')
                raise r
            else:
                deleted += len(r)

        await ctx.send(f'Obliration complete. ({deleted} messages vaporized)', delete_after=5)


async def setup(bot: 'BotClient'):
    await bot.add_cog(Purger(bot))
