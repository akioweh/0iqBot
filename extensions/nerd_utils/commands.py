from typing import TYPE_CHECKING

from discord.ext.commands import Cog, command, Context

from botcord.functions import batch
from .socialscan.util import execute_queries

if TYPE_CHECKING:
    from botcord import BotClient


class NerdUtils(Cog):
    def __init__(self, bot: 'BotClient'):
        self.bot = bot

    @command()
    async def socialscan(self, ctx: Context, *, usernames=None):
        if not usernames:
            return
        usernames = usernames.split(",")
        usernames = [i.strip() for i in usernames]
        await ctx.reply(f'Scanning for {usernames}...')
        results = await execute_queries(usernames, aiohttp_session=self.bot.aiohttp_session)
        msg = ''
        for result in results:
            msg += f'`{result.query}` on **`{result.platform}`**: [Success: `{result.success}`, Valid: `{result.valid}`, **Available: `{result.available}`**] (`{result.message if result.message else "No response"}`)\n'
        for i in batch(msg):
            await ctx.reply(i)
        await ctx.reply('Finished Scan.')


def setup(bot):
    bot.add_cog(NerdUtils(bot))
