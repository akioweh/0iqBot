from typing import List, Optional, TYPE_CHECKING

from discord import Webhook, User, HTTPException, Forbidden, NotFound, AllowedMentions
from discord.ext.commands import Cog, Context, command

if TYPE_CHECKING:
    import botcord


class MessageHook(Cog):
    def __init__(self, bot: 'botcord.BotClient'):
        self.bot = bot
        self.mentions = AllowedMentions(everyone=False, users=True, roles=False)

    @command(aliases=['say'])
    async def send(self, ctx: Context, *, text=None):
        if (text is None) and (ctx.message.attachments is None):
            return
        if len(text) > 2000:
            await ctx.reply('Messages must be 2000 or fewer in length. (nitro abuse smh)', delete_after=10)
            return

        attachments = []
        if ctx.message.attachments:
            attachments = [await item.to_file() for item in ctx.message.attachments]

        await ctx.send(content=text, files=attachments, reference=ctx.message.reference, allowed_mentions=self.mentions)
        try:
            await ctx.message.delete()
        except (Forbidden, NotFound):
            pass

    @command(aliases=['repost'])
    async def resend(self, ctx: Context, *, text=None):
        await self.sendas(ctx, user=ctx.author, text=text)

    @command()
    async def sendas(self, ctx: Context, user: Optional[User] = None, *, text=None):
        if (user is None) or ((text is None) and (ctx.message.attachments is None)):
            return
        if len(text) > 2000:
            await ctx.reply('Messages must be 2000 or fewer in length. (nitro abuse smh)', delete_after=10)
            return

        attachments = []
        if ctx.message.attachments:
            attachments = [await item.to_file() for item in ctx.message.attachments]

        hooks: Optional[List[Webhook]] = await ctx.channel.webhooks()
        valid_hook: Optional[Webhook] = None
        for hook in hooks:
            if hook.token is not None:
                valid_hook = hook
                break
        try:
            if not valid_hook:
                valid_hook = await ctx.channel.create_webhook(name='MessageHook')

            await valid_hook.send(content=text,
                                  username=user.name,
                                  avatar_url=user.avatar_url,
                                  files=attachments,
                                  allowed_mentions=self.mentions)
            try:
                await ctx.message.delete()
            except (Forbidden, NotFound):
                pass

        except HTTPException as error:
            if error.code == 30007:
                await ctx.reply('All existing webhooks are unusable (please delete). Failed to create new one: Maximum number of webhooks in this channel reached (10).')
            else:
                await ctx.reply('Failed to send message.', delete_after=10)
                print(error)

    @command()
    async def cleanhooks(self, ctx, *args):
        if args:
            return
        if not ctx.guild:
            return
        hooks: Optional[List[Webhook]] = await ctx.guild.webhooks()
        if not hooks:
            await ctx.reply('No hooks cleaned.')
            return
        deleted = 0
        for hook in hooks:
            if (hook.name == 'MessageHook') or (hook.user == ctx.bot.user):
                await hook.delete()
                deleted += 1
        await ctx.reply(f'Deleted {deleted} hook{"s" if deleted > 1 else ""}.')


def setup(bot: 'botcord.BotClient'):
    bot.add_cog(MessageHook(bot))
