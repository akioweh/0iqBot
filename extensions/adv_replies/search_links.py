from urllib.parse import quote_plus as parse_url
from typing import TYPE_CHECKING

from discord.ext.commands import Cog, command

if TYPE_CHECKING:
    import botcord


class SearchLinks(Cog):
    def __init__(self, bot):
        self.bot: 'botcord.BotClient' = bot

    @command(aliases=['g', 'search', 'bruhwhycouldntyoujustgooglethis'])
    async def google(self, ctx, *, query):
        if not query:
            return
        await ctx.send(f'http://www.usethefuckinggoogle.com/?q={parse_url(query)}')

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


def setup(bot: 'botcord.BotClient'):
    bot.add_cog(SearchLinks(bot))
