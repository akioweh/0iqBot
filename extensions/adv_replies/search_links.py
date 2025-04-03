from typing import TYPE_CHECKING
from urllib.parse import quote_plus as parse_url

from discord.ext.commands import command

from botcord.ext.commands import Cog

if TYPE_CHECKING:
    from botcord import BotClient


class SearchLinks(Cog):
    def __init__(self, bot: 'BotClient'):
        self.bot = bot

    @command(aliases=['g', 'search', 'bruhwhycouldntyoujustgooglethis'])
    async def google(self, ctx, *, query):
        if not query:
            return
        await ctx.send(f'[google.com: {query}](https://letmegooglethat.com/?q={parse_url(query)})')

    @command(aliases=['minecraftwiki'])
    async def mcwiki(self, ctx, *, query):
        if not query:
            return
        await ctx.send(f'https://minecraft.fandom.com/wiki/Special:Search?query={parse_url(query)}')

    @command(aliases=['dict', 'dictionary', 'urbandict'])
    async def urban(self, ctx, *, query):
        if not query:
            return
        await ctx.send(f'https://www.urbandictionary.com/define.php?term={parse_url(query)}')

    @command(aliases=['yt', 'ytube'])
    async def youtube(self, ctx, *, query):
        if not query:
            return
        await ctx.send(f'https://www.youtube.com/results?search_query={parse_url(query)}')


async def setup(bot: 'BotClient'):
    await bot.add_cog(SearchLinks(bot))
