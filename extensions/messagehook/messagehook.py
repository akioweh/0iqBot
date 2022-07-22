import asyncio
from contextlib import suppress
from typing import List, Optional, TYPE_CHECKING

from discord import AllowedMentions, Forbidden, HTTPException, NotFound, User, Webhook
from discord.ext.commands import Cog, Context, command

if TYPE_CHECKING:
    import botcord


# noinspection SpellCheckingInspection
class MessageHook(Cog):
    def __init__(self, bot: 'botcord.BotClient'):
        self.bot = bot
        self.mentions = AllowedMentions(everyone=False, users=True, roles=False)

    @command(aliases=['say'])
    async def send(self, ctx: Context, *, text: str = None, delete: bool = True):
        if (text is None) and (ctx.message.attachments is None):
            return
        if len(text) > 2000:
            await ctx.reply('Messages must be 2000 or fewer in length. (nitro abuse smh)', delete_after=10)
            return

        attachments = await asyncio.gather(*(item.to_file() for item in ctx.message.attachments))

        if delete:
            t1 = asyncio.create_task(ctx.message.delete())
        t2 = asyncio.create_task(ctx.send(content=text,
                                          files=attachments,
                                          reference=ctx.message.reference,
                                          allowed_mentions=self.mentions))

        with suppress(Forbidden, NotFound):
            if delete:
                await asyncio.gather(t1, t2)
            else:
                await t2

    @command(aliases=['repost'])
    async def resend(self, ctx: Context, *, text: str = None):
        await self.sendas(ctx, user=ctx.author, text=text)

    @command()
    async def sendas(self, ctx: Context, user: Optional[User] = None, *, text: str = None, delete: bool = True):
        if (user is None) or ((text is None) and (ctx.message.attachments is None)):
            return
        if len(text) > 2000:
            await ctx.reply('Messages must be 2000 or fewer in length. (nitro abuse smh)', delete_after=10)
            return

        attachments = await asyncio.gather(*(item.to_file() for item in ctx.message.attachments))

        try:
            hooks: Optional[List[Webhook]] = await ctx.channel.webhooks()
            valid_hook: Optional[Webhook] = None
            for hook in hooks:
                if hook.token:
                    valid_hook = hook
                    break

            if not valid_hook:
                valid_hook = await ctx.channel.create_webhook(name='MessageHook')

            if delete:
                t1 = asyncio.create_task(ctx.message.delete())
            t2 = asyncio.create_task(valid_hook.send(content=text,
                                                     username=user.name,
                                                     avatar_url=user.avatar_url,
                                                     files=attachments,
                                                     allowed_mentions=self.mentions))
            with suppress(Forbidden, NotFound):
                if delete:
                    await asyncio.gather(t1, t2)
                else:
                    await t2

        except Forbidden:
            with suppress(Forbidden):
                await ctx.reply('Missing Permissions', delete_after=5)

        except HTTPException as error:
            if error.code == 30007:
                await ctx.reply('All existing webhooks are unusable (please delete). '
                                'Failed to create new one: Maximum number of webhooks in this channel reached (10).')

    @command()
    async def cleanhooks(self, ctx: Context):
        if not ctx.guild:
            return

        try:
            hooks: Optional[List[Webhook]] = await ctx.guild.webhooks()
            delete_ables = [hook for hook in hooks if hook.name == 'MessageHook' or hook.user == ctx.bot.user]
            if not delete_ables:
                await ctx.reply('No hooks cleaned.')
                return

            await asyncio.gather(*(hook.delete() for hook in delete_ables))
            await ctx.reply(f'Deleted {len(delete_ables)} hooks.')
        except Forbidden:
            with suppress(Forbidden):
                await ctx.reply('Missing Permissions', delete_after=5)


def setup(bot: 'botcord.BotClient'):
    bot.add_cog(MessageHook(bot))
